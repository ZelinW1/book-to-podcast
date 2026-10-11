---
name: book-to-podcast
description: Turn an ebook into a chapter-aware podcast series with scripts and audio, or make code-rendered videos from its episodes. Use for EPUB, PDF, DOCX, HTML, Markdown, or text book sources and for continuing a book-to-podcast project.
---

# Book to podcast

Work in two stages. Stage 1 ingests a book, plans episodes, writes spoken scripts, and synthesizes audio. Stage 2 turns completed episodes into videos. Run either stage alone when that is what the user asks for. Keep generated work in a user-chosen output directory, not in this skill folder.

## Decisions

- Use the source language by default. If the user's request language differs from the book language, ask which language to use for the podcast before writing scripts.
- Aim for roughly 30 minutes per episode, with a 45-minute ceiling. Prefer chapter and subsection boundaries; combine short sections and split long ones. Estimate from a voice sample when available, then check actual audio duration. Split an overlong episode rather than accelerating it substantially.
- Default to one narrator and a natural voice suitable for the language. Two speakers, gender, exact voices, pacing, audience, and video format can be specified by the user. Ask for a TTS engine if none is specified or configured, explaining local options and that `edge-tts` uses an online service. Do not infer a local model, voice, or installation path from this skill's examples.
- Favor faithful, vivid, conversational writing. Explain difficult ideas with clear transitions and attributed examples; avoid slang, sensationalism, invented quotations, and changes to the author's argument. For dialogue, hosts may ask clarifying questions but must not impersonate the author or invent claims.
- Never load the whole book into model context. Parse locally, inspect the compact index first, then read only chunks needed for the current episode plus concise continuity notes. Keep source chunk IDs in adaptation notes so claims can be checked.

## Stage 1: book to audio

Read [audio workflow](references/audio.md) when ingesting, planning, writing, or synthesizing. Run `scripts/ingest_book.py` to create `book.json`, `index.md`, and source chunks. Create `series-plan.md` with episode boundaries and estimated duration. Write each episode in the [script format](references/script-format.md), and create `adaptation-notes.md` for its source coverage, omissions, and uncertainty. Use the TTS engine chosen for the project; read the [Qwen3-TTS adapter](references/tts-qwen.md) only if that engine is selected. Deliver the script, notes, final audio, and segment timing. Preserve intermediate audio so one failed segment can be retried.

## Stage 2: audio to video

Read [video workflow](references/video.md). Design and draw frames in code from the completed audio and timing data. `scripts/render_video.py` is an optional simple starter, not the required visual design. Keep the code, project settings, source script, assets, subtitles, and output video so the result can be reproduced. Do not use a graphical video editor as the implementation path.

## Runtime

The ingestion script uses Python's standard library for EPUB, HTML, Markdown, and text. PDF needs PyMuPDF; DOCX needs python-docx. TTS and video dependencies depend on the selected implementation. Check availability before starting a costly run. A missing optional dependency affects only its format or stage.
