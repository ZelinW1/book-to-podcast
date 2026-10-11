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

Use the TTS engine selected by the user. When unspecified and no local model is configured, present a short choice: an available local model, a lightweight local model such as Piper where the language has a suitable voice, or `edge-tts` as an online alternative. Never represent `edge-tts` as offline. Confirm engine, voice, and delivery style once, then reuse them across an episode or series unless the script intentionally changes speaker or style. The entrypoint links optional engine-specific instructions.

Make a short voice sample before a costly full-length run. For speech assembled from segments, keep the same role-to-voice mapping, pronunciation choices, pace, and style guidance at every boundary. Listen across joins in the assembled audio: an unintended change in timbre, accent, energy, or pacing is a defect even when each segment sounds acceptable alone. Re-synthesize or smooth affected segments before delivery; loudness matching alone does not make different deliveries sound consistent. Also check duration, intelligibility, missing speech, and long silences. Preserve segment audio and timing so corrections do not require rebuilding an entire episode.
