# Audio workflow

## Ingest and plan

`python scripts/ingest_book.py BOOK --output PROJECT/source` extracts EPUB in `spine` order and reads its navigation table when present. PDF uses the document table of contents and page locations; OCR only pages with no useful text, and report pages whose layout or OCR is uncertain. DOCX uses heading styles. Other text formats use headings where possible. Do not treat page breaks or EPUB file boundaries as definitive episode boundaries.

Read `source/index.md` first. It lists order, titles, sizes, and chunk IDs without including the full book. Inspect only selected `source/chunks/*.txt` files. For long works, produce a compact chapter summary and a series outline; retain only those and relevant chunks while writing an episode. Cache completed sections and source hashes so reruns do not repeat extraction or synthesis.

Plan episodes by ideas and chapter boundaries. Target approximately 30 minutes and keep actual episodes at or below 45 minutes. A short front matter section may be omitted from speech with a note; a long chapter can span episodes. For fiction, preserve reading order and avoid later spoilers. For nonfiction, preserve qualifications and distinguish the author's claims from the host's explanation.

## Script and source checks

Use `references/script-format.md` exactly for machine-readable speech turns. Each `##` turn should be short enough for reliable synthesis, roughly one or two spoken paragraphs. Keep source IDs in HTML comments, which are not spoken. The Markdown itself is the editable source of truth.

Write `adaptation-notes.md` for each episode: covered chunk IDs, concepts retained, compression and omissions, uncertain passages, pronunciation choices, and any original examples added for explanation. Check names, dates, quotations, distinctions, and conclusions against the cited chunks. An example invented for clarity must be introduced as an example, not attributed to the book.

If the request language and detected book language differ, ask before translating. If the source language is uncertain, inspect representative chunks before deciding.

## Synthesis

Use the TTS model selected by the user. When unspecified and no local model is configured, present a short choice: a locally installed model, a lightweight local model such as Piper where the language has a suitable voice, or `edge-tts` as an online alternative. Never represent `edge-tts` as offline. Confirm model and voice once, then reuse them across the series.

For local Qwen3-TTS CustomVoice, `scripts/tts_qwen.py` loads the model once with `sdpa`, synthesizes sequentially, saves per-segment WAVs, and resumes matching cached segments. It uses a shared narration instruction, fixed seed, deterministic decoding, and segment loudness matching by default so adjacent turns keep a consistent delivery. These settings can be overridden when the user wants a different style. Set the environment so its native audio dependencies are on PATH. Pass `--book-manifest source/book.json` to catch mistyped source IDs. Do a short voice sample before committing a full-length run. Its output includes a combined WAV and `timing.json`; MP3 is made when FFmpeg is available. Listen across segment joins as well as checking duration, intelligibility, missing segments, and long silences. Regenerate a turn whose delivery noticeably changes before declaring an episode complete.
