---
name: book-to-podcast
description: Turn an ebook into a chapter-aware podcast series with scripts and audio, or make code-rendered videos from its episodes. Use for EPUB, PDF, DOCX, HTML, Markdown, or text book sources and for continuing a book-to-podcast project.
---

# Book to podcast

Work in two stages. Stage 1 ingests a book, plans episodes, writes spoken scripts, and synthesizes audio. Stage 2 turns completed episodes into videos. Run either stage alone when that is what the user asks for. Keep generated work in a user-chosen output directory, not in this skill folder.

## Plan and production checkpoints

For a new book or major series change, inspect the source index and representative passages, then present a reviewable plan before production. Use Plan mode when the host provides it; otherwise present the plan in the current mode. A written plan alone is not approval. Wait for the user's explicit response before moving past the plan checkpoint. Do not claim to have entered a mode the host does not provide.

Cover adaptation density and intended listening experience; a source-to-episode coverage map with boundaries, target durations, and any hard limit; language and attribution; TTS engine, narrator or voice reference, delivery, and chunking; sample checkpoints; subtitle alignment and final quality checks; and output formats. When video is in scope, include layout, assets, music, opening buffer, and cover. Group decisions that require user input. See the [audio workflow](references/audio.md) and [video workflow](references/video.md) for details.

Default to these scoped checkpoints, each with a concrete artifact the user can review:

1. **Plan:** source coverage, episode structure, runtime estimates, and production choices; approval precedes production scripts.
2. **Script pilot:** an opening and a difficult representative passage, with source notes; approval precedes writing the full series.
3. **Complete scripts:** all episode scripts, coverage notes, and duration estimates checked for listening quality and fidelity; approval precedes full-series synthesis.
4. **Voice pilot:** actual script audio including the difficult passage and joins, assessed for comprehension, pace, pronunciation, and consistency; approval precedes full-series synthesis.
5. **Completed audio:** deliver it for listening review before video production when video is requested.
6. **Video pilot:** an encoded sample of the opening, a dense passage, a join, and the ending, with music and subtitles; approval precedes batch rendering.
7. **Final delivery:** complete media, reproducible project files, quality checks, and a standalone 4:3 series cover when video is in scope.

Pause at each relevant checkpoint and wait for an explicit go-ahead; completing a sample does not authorize the full run. Apply only checkpoints relevant to the requested work. Reuse approvals already given for the same scope and do not ask again. If the user explicitly requests one-pass production, perform the same internal reviews without waiting between checkpoints. Do not spend a user's time or compute on full synthesis or rendering before its applicable checkpoint is cleared.

## Decisions

- Use the source language by default. If the user's request language differs from the book language, ask which language to use for the podcast before writing scripts.
- Set episode count and target duration from the work's structure, adaptation density, and listening load. Agree on any hard maximum in the plan rather than imposing a universal runtime. Estimate from a representative voice sample, check actual audio duration before final synthesis, and revise episode boundaries or wording if needed; do not speed up narration to meet a time target.
- Default to one narrator and a natural voice suitable for the language. Two speakers, gender, exact voices, pacing, audience, and video format can be specified by the user. Ask for a TTS engine if none is specified or configured, explaining local options and that `edge-tts` uses an online service. Do not infer a local model, voice, or installation path from this skill's examples.
- Write for a first-time listener: natural, vivid, and easy to follow while preserving the author's sequence of questions, distinctions, evidence, objections, and conclusions, or the story's chronology, at the agreed density. After each coherent section, ask whether it sounds like speech, whether the listener can follow why each step follows, whether examples are clearly attributed, and whether any simplification changes the author's claim. Rewrite passages that merely recite or closely paraphrase the source, or that require rereading to understand. Avoid slang, sensationalism, invented quotations, and unsupported claims. Dialogue hosts may clarify but must not impersonate the author.
- Never load the whole book into model context. Parse locally, inspect the compact index first, then read only chunks needed for the current episode plus concise continuity notes. Keep source chunk IDs in adaptation notes so claims can be checked.

## Stage 1: book to audio

Read [audio workflow](references/audio.md) when ingesting, planning, writing, or synthesizing. Run `scripts/ingest_book.py` to create `book.json`, `index.md`, and source chunks. Create `series-plan.md` with a complete source-to-episode map, adaptation density, episode boundaries, and estimated duration. Write and review the script pilot, then each episode in the [script format](references/script-format.md), with `adaptation-notes.md` for source coverage, omissions, and uncertainty. Check complete scripts and actual voice-pilot pace before full synthesis. Use the TTS engine chosen for the project; read the [Qwen3-TTS adapter](references/tts-qwen.md) only if its CustomVoice model is selected. Deliver the script, notes, final audio, and segment timing. Preserve intermediate audio so one failed segment can be retried. Treat synthesis segment timing as assembly metadata, not word-accurate subtitle timing.

## Stage 2: audio to video

Read [video workflow](references/video.md). Design and draw frames in code from the completed audio and verified subtitle cues. Make encoded samples covering the opening, a dense middle passage, a speech join, and the ending, and get the applicable approval before batch rendering. Include gentle, audible music under the narration by default, and render a separate 4:3 series cover after the videos unless the user specifies otherwise. `scripts/render_video.py` is an optional simple starter, not the required visual design. Keep the code, project settings, source script, assets, subtitles, and output video so the result can be reproduced. Do not use a graphical video editor as the implementation path.

## Runtime

The ingestion script uses Python's standard library for EPUB, HTML, Markdown, and text. PDF needs PyMuPDF; DOCX needs python-docx. TTS and video dependencies depend on the selected implementation. Check availability before starting a costly run. A missing optional dependency affects only its format or stage.
