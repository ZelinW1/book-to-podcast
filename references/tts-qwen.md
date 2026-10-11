# Optional Qwen3-TTS adapter

Use this reference only when the project selects a local Qwen3-TTS CustomVoice model. `scripts/tts_qwen.py` is a reusable adapter, not a requirement or a pointer to any particular user's installation. Supply the model directory with `--model` or `QWEN3_TTS_MODEL`; use the user's working Python environment with Qwen3-TTS, NumPy, and SoundFile installed. FFmpeg is optional for MP3 output.

The adapter loads the model once with `sdpa`, synthesizes turns sequentially, caches per-segment WAVs, and resumes matching cached segments. It applies one narration instruction, a fixed seed, deterministic decoding, and bounded loudness matching by default. These settings reduce unintended delivery changes but do not guarantee identical style; listen to the joined output and regenerate mismatched turns. Set `--default-voice` for a single narrator or use `--voice ROLE=VOICE` for every role. Choose voices for the project's language and desired delivery, then keep each role's voice stable.

Pass `--book-manifest source/book.json` to catch mistyped source IDs. The output includes combined WAV, `timing.json`, and subtitles; FFmpeg adds MP3 when available. For a different TTS engine, use or build an adapter that emits equivalent audio and segment timing, without copying Qwen-specific prompts or model settings.
