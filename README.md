# Book to Podcast

An Agent Skill for turning an ebook into a chapter-aware podcast series, then making code-rendered episode videos. The repository root is the skill directory; `SKILL.md` is its agent entrypoint.

## Layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Planning gate, shared decisions, and routing for the two stages |
| `references/` | Audio, script-format, and video guidance loaded when relevant; Qwen3-TTS instructions are optional |
| `scripts/ingest_book.py` | Extract a compact index and traceable text chunks |
| `scripts/tts_qwen.py` | Optional local Qwen3-TTS CustomVoice adapter |
| `scripts/render_video.py` | Optional simple code-drawn video starter |
| `tests/` | Small behavior checks for extraction and script parsing |

Install by placing this directory in the skills location supported by your agent. For Codex, that can be `~/.codex/skills/book-to-podcast/`. Open `SKILL.md` for the workflow; the skill chooses references only for the current stage and engine.

The skill supports EPUB, PDF, DOCX, HTML, Markdown, and plain text input. PDF extraction needs PyMuPDF; DOCX needs python-docx. TTS and video dependencies depend on the chosen implementation. The included Qwen adapter and video renderer are examples you can replace while retaining the script, audio, timing, and project artifacts described by the skill.

The default workflow uses reviewable checkpoints for the plan, a script pilot, complete scripts, a voice pilot, completed audio, and a video pilot before each larger production run. Explicit one-pass requests keep the internal checks without waiting between stages. Scripts are written for first-time listeners and checked against the source; the voice pilot tests listening pace as well as voice quality. Videos include gentle music and a separate 4:3 series cover by default. The included scripts automate extraction, one preset-voice TTS backend, and a simple video style. Synthesis segment timing is not a final subtitle alignment; captioned video needs verified cues aligned to the completed narration. Sample books and generated media belong in a separate output directory and are not tracked here.
