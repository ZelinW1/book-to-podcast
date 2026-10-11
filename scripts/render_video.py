#!/usr/bin/env python3
"""Draw podcast video frames in Python and encode them with FFmpeg."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import wave
from array import array
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"


def make_subtitles(path: Path, segments: list[dict], end: float) -> None:
    lines = []
    for index, segment in enumerate(segments, 1):
        if segment["start"] >= end:
            break
        lines.extend([str(index), f"{timestamp(segment['start'])} --> {timestamp(min(segment['end'], end))}", segment["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def load_rms(path: Path, seconds: float, fps: int) -> list[float]:
    if path.suffix.lower() != ".wav":
        return []
    with wave.open(str(path), "rb") as source:
        channels, sample_width, rate, count = source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes()
        if sample_width != 2:
            return []
        samples_per_frame = max(1, round(rate / fps))
        values = []
        frames_to_read = min(count, math.ceil(seconds * rate))
        while frames_to_read > 0:
            raw = source.readframes(min(samples_per_frame, frames_to_read))
            if not raw:
                break
            samples = array("h")
            samples.frombytes(raw)
            if channels > 1:
                samples = samples[::channels]
            if samples:
                values.append(math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768)
            frames_to_read -= len(raw) // (sample_width * channels)
    peak = max(values, default=1) or 1
    return [min(1.0, value / peak) for value in values]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，。；,. ") + "…"
    return lines


def current_segment(segments: list[dict], time: float) -> dict | None:
    low, high = 0, len(segments)
    while low < high:
        middle = (low + high) // 2
        if segments[middle]["end"] <= time:
            low = middle + 1
        else:
            high = middle
    return segments[low] if low < len(segments) and segments[low]["start"] <= time else None


def draw_frame(width: int, height: int, time: float, duration: float, title: str, segments: list[dict], rms: list[float], fps: int, font_path: Path) -> Image.Image:
    scale = min(width / 1920, height / 1080)
    image = Image.new("RGB", (width, height), (13, 22, 36))
    draw = ImageDraw.Draw(image)
    margin = round(112 * scale)
    accent = (91, 218, 190)
    muted = (152, 171, 188)
    white = (243, 247, 247)
    draw.rounded_rectangle((margin, round(94 * scale), margin + round(72 * scale), round(105 * scale)), radius=5, fill=accent)
    label_font = font(font_path, max(18, round(27 * scale)))
    title_font = font(font_path, max(38, round(74 * scale)))
    caption_font = font(font_path, max(27, round(51 * scale)))
    draw.text((margin, round(133 * scale)), "BOOK  /  PODCAST", font=label_font, fill=muted)
    title_lines = wrap_text(draw, title, title_font, width - 2 * margin, 2)
    y = round(228 * scale)
    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=white)
        y += round(101 * scale)
    current = current_segment(segments, time)
    panel_top = round(535 * scale)
    panel_bottom = round(910 * scale)
    draw.rounded_rectangle((margin, panel_top, width - margin, panel_bottom), radius=round(27 * scale), fill=(24, 38, 53))
    role = current["role"] if current else ""
    speech = current["text"] if current else ""
    if role:
        draw.text((margin + round(45 * scale), panel_top + round(40 * scale)), role, font=label_font, fill=accent)
    caption_lines = wrap_text(draw, speech, caption_font, width - 2 * margin - round(90 * scale), 3)
    for line_number, line in enumerate(caption_lines):
        draw.text((margin + round(45 * scale), panel_top + round((105 + 75 * line_number) * scale)), line, font=caption_font, fill=white)
    bar_y = round(972 * scale)
    draw.rounded_rectangle((margin, bar_y, width - margin, bar_y + round(8 * scale)), radius=4, fill=(62, 82, 95))
    progress = min(1, max(0, time / duration)) if duration else 0
    draw.rounded_rectangle((margin, bar_y, margin + round((width - 2 * margin) * progress), bar_y + round(8 * scale)), radius=4, fill=accent)
    draw.text((margin, round(1003 * scale)), f"{int(time // 60):02d}:{int(time % 60):02d}  /  {int(duration // 60):02d}:{int(duration % 60):02d}", font=label_font, fill=muted)
    if rms:
        center = width - margin - round(100 * scale)
        activity = rms[min(len(rms) - 1, int(time * fps))]
        for index in range(9):
            h = round((10 + 44 * activity * (0.45 + 0.55 * math.sin((index + 1) * 1.7) ** 2)) * scale)
            x = center + round((index - 4) * 18 * scale)
            draw.rounded_rectangle((x, bar_y - round(10 * scale) - h, x + round(8 * scale), bar_y - round(10 * scale)), radius=3, fill=accent)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/msyh.ttc"))
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=2, help="distinct drawn frames per second; encoder outputs 30 fps")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--max-seconds", type=float, help="render a short sample")
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    if args.width < 640 or args.height < 360 or args.width % 2 or args.height % 2 or args.fps < 1:
        parser.error("width and height must be even and at least 640x360; fps must be positive")
    if not args.audio.is_file() or not args.timing.is_file() or not args.font.is_file():
        parser.error("audio, timing, and font must exist")
    timeline = json.loads(args.timing.read_text(encoding="utf-8"))
    duration = float(timeline["duration"])
    if args.max_seconds is not None:
        duration = min(duration, args.max_seconds)
    if duration <= 0:
        parser.error("episode duration must be positive")
    segments = timeline["segments"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    renderer_copy = output / "render_video.py"
    if Path(__file__).resolve() != renderer_copy.resolve():
        shutil.copy2(Path(__file__).resolve(), renderer_copy)
    project = {"schema": 1, "audio": str(args.audio.resolve()), "timing": str(args.timing.resolve()), "renderer": str(renderer_copy), "font": str(args.font.resolve()), "width": args.width, "height": args.height, "draw_fps": args.fps, "duration": duration, "title": timeline["title"]}
    (output / "video-project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    make_subtitles(output / "subtitles.srt", segments, duration)
    rms = load_rms(args.audio, duration, args.fps)
    image = draw_frame(args.width, args.height, 0, duration, timeline["title"], segments, rms, args.fps, args.font)
    image.save(output / "preview.png")
    if args.preview_only:
        print(str(output / "preview.png"))
        return
    if not args.ffmpeg:
        parser.error("FFmpeg not found; pass --ffmpeg PATH")
    frame_count = math.ceil(duration * args.fps)
    command = [args.ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-", "-i", str(args.audio.resolve()), "-t", str(duration), "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output / "video.mp4")]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for frame_number in range(frame_count):
            t = frame_number / args.fps
            frame = draw_frame(args.width, args.height, t, duration, timeline["title"], segments, rms, args.fps, args.font)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"FFmpeg exited with code {process.returncode}")
    except (BrokenPipeError, KeyboardInterrupt):
        process.kill()
        process.wait()
        raise
    print(json.dumps({"video": str(output / "video.mp4"), "duration": duration, "frames_drawn": frame_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
