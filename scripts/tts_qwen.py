#!/usr/bin/env python3
"""Synthesize an episode Markdown script with a local Qwen3-TTS CustomVoice model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


TITLE = re.compile(r"^#\s+(.+)$")
TURN = re.compile(r"^##\s+(.+)$")
LANGUAGE = re.compile(r"^<!--\s*language:\s*(.*?)\s*-->$", re.I)
SOURCE = re.compile(r"^<!--\s*source:\s*(.*?)\s*-->$", re.I)


def read_script(path: Path) -> tuple[str, str | None, list[dict]]:
    title = ""
    language = None
    turns: list[dict] = []
    current: dict | None = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if match := TITLE.match(line):
            title = match.group(1).strip()
        elif match := TURN.match(line):
            current = {"role": match.group(1).strip(), "source": [], "lines": []}
            turns.append(current)
        elif match := LANGUAGE.match(line):
            language = match.group(1).strip()
        elif match := SOURCE.match(line):
            if current is not None:
                current["source"] = [item.strip() for item in match.group(1).split(",") if item.strip()]
        elif line and current is not None:
            if line.startswith("<!--") or line.startswith("#"):
                raise ValueError(f"unsupported markup in spoken turn: {line[:60]}")
            current["lines"].append(line)
        elif line and not line.startswith("<!--"):
            raise ValueError(f"text before first speaker turn would be ignored: {line[:60]}")
    if not title or not turns:
        raise ValueError("script needs a # title and at least one ## speaker turn")
    for turn in turns:
        turn["text"] = " ".join(turn.pop("lines"))
        if not turn["text"]:
            raise ValueError(f"empty turn for {turn['role']}")
    return title, language, turns


def split_speech(text: str, limit: int) -> list[str]:
    sentences = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z])", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > limit and current:
            chunks.append(current)
            current = ""
        while len(sentence) > limit:
            cut = max(sentence.rfind("，", 0, limit), sentence.rfind(", ", 0, limit), sentence.rfind(" ", 0, limit))
            cut = cut + 1 if cut > limit // 2 else limit
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        current = f"{current} {sentence}" if current else sentence
    if current:
        chunks.append(current)
    return chunks


def srt_timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, remainder = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{remainder:03d}"


def write_srt(path: Path, segments: list[dict]) -> None:
    lines: list[str] = []
    for number, segment in enumerate(segments, 1):
        lines.extend([str(number), f"{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}", segment["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=os.environ.get("QWEN3_TTS_MODEL"))
    parser.add_argument("--language")
    parser.add_argument("--book-manifest", type=Path, help="validate source chunk IDs against book.json")
    parser.add_argument("--default-voice", default="Serena")
    parser.add_argument("--voice", action="append", default=[], metavar="ROLE=VOICE")
    parser.add_argument("--max-chars", type=int, default=120)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_chars < 20 or args.pause < 0:
        parser.error("--max-chars must be at least 20 and --pause cannot be negative")
    title, script_language, turns = read_script(args.script)
    language = args.language or script_language or "Auto"
    voices: dict[str, str] = {}
    for mapping in args.voice:
        if "=" not in mapping:
            parser.error("--voice must be ROLE=VOICE")
        role, voice = mapping.split("=", 1)
        voices[role.strip()] = voice.strip()
    roles = {turn["role"] for turn in turns}
    if len(roles) > 1 and (any(role not in voices for role in roles) or len({voices[role] for role in roles}) < len(roles)):
        parser.error("multiple speaker roles need distinct --voice ROLE=VOICE mappings")
    pieces: list[dict] = []
    for turn_index, turn in enumerate(turns, 1):
        for spoken in split_speech(turn["text"], args.max_chars):
            pieces.append({"id": f"s{len(pieces) + 1:04d}", "turn": turn_index, "role": turn["role"], "voice": voices.get(turn["role"], args.default_voice), "source": turn["source"], "text": spoken})
    if args.book_manifest:
        manifest = json.loads(args.book_manifest.read_text(encoding="utf-8"))
        known = {chunk["id"] for chunk in manifest["chunks"]}
        unknown = sorted({source for piece in pieces for source in piece["source"] if source not in known})
        if unknown:
            parser.error(f"unknown source chunk IDs: {', '.join(unknown)}")
    summary = {"title": title, "language": language, "turns": len(turns), "segments": len(pieces), "characters": sum(len(piece["text"]) for piece in pieces)}
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False))
        return
    if not args.model or not args.model.is_dir():
        parser.error("provide a local CustomVoice model directory with --model or QWEN3_TTS_MODEL")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    numba_cache = output / ".numba-cache"
    numba_cache.mkdir(exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_cache))
    segment_dir = output / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output / "cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    pending = []
    for piece in pieces:
        key = hashlib.sha256(json.dumps([str(args.model.resolve()), language, piece["voice"], piece["text"], args.seed, args.max_new_tokens], ensure_ascii=False).encode()).hexdigest()
        piece["cache_key"] = key
        if cache.get(piece["id"], {}).get("key") != key or not (segment_dir / f"{piece['id']}.wav").exists():
            pending.append(piece)
    import numpy as np
    import soundfile as sf
    model = None
    if pending:
        print(f"loading Qwen runtime; {len(pending)} uncached segments", flush=True)
        import torch
        from qwen_tts import Qwen3TTSModel
        print(f"loading model {args.model.resolve()}", flush=True)
        model = Qwen3TTSModel.from_pretrained(str(args.model.resolve()), device_map="cuda:0" if torch.cuda.is_available() else "cpu", dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32, attn_implementation="sdpa")
        if model.model.tts_model_type != "custom_voice":
            raise ValueError("this adapter requires a Qwen3-TTS CustomVoice model")
    else:
        print(f"reusing {len(pieces)} cached segments", flush=True)
    for index, piece in enumerate(pieces):
        if piece not in pending:
            continue
        if args.seed is not None:
            torch.manual_seed(args.seed + index)
        print(f"synthesizing {piece['id']} ({len(piece['text'])} chars)", flush=True)
        wavs, sr = model.generate_custom_voice(text=piece["text"], speaker=piece["voice"], language=language, max_new_tokens=args.max_new_tokens)
        if sr != 24000:
            raise ValueError(f"unexpected Qwen sample rate: {sr}")
        sf.write(segment_dir / f"{piece['id']}.wav", wavs[0], sr, subtype="PCM_16")
        cache[piece["id"]] = {"key": piece["cache_key"]}
        cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
        print(f"synthesized {piece['id']} ({len(piece['text'])} chars)", flush=True)
    audio_parts = []
    timing = []
    cursor = 0.0
    sample_rate = 24000
    for index, piece in enumerate(pieces):
        waveform, sr = sf.read(segment_dir / f"{piece['id']}.wav", dtype="float32", always_2d=False)
        if sr != sample_rate:
            raise ValueError(f"sample-rate mismatch in {piece['id']}")
        if waveform.ndim == 2:
            waveform = waveform.mean(axis=1)
        duration = len(waveform) / sample_rate
        timing.append({key: piece[key] for key in ("id", "turn", "role", "voice", "source", "text") } | {"start": round(cursor, 3), "end": round(cursor + duration, 3)})
        audio_parts.append(waveform)
        cursor += duration
        if index + 1 < len(pieces):
            silence = np.zeros(round(args.pause * sample_rate), dtype="float32")
            audio_parts.append(silence)
            cursor += len(silence) / sample_rate
    sf.write(output / "episode.wav", np.concatenate(audio_parts), sample_rate, subtype="PCM_16")
    (output / "timing.json").write_text(json.dumps({"schema": 1, "title": title, "language": language, "sample_rate": sample_rate, "duration": round(cursor, 3), "segments": timing}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_srt(output / "subtitles.srt", timing)
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if ffmpeg:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(output / "episode.wav"), "-codec:a", "libmp3lame", "-qscale:a", "2", str(output / "episode.mp3")], check=True)
    print(json.dumps(summary | {"duration": round(cursor, 3), "output": str(output), "mp3": bool(ffmpeg)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
