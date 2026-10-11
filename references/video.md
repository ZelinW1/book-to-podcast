# Video workflow

Use the episode audio and `timing.json` to build a video with code-drawn frames and a reproducible render command. Choose the visual concept from the audience, subject, platform, user preferences, and available assets. Possible elements include typography, chapter cards, diagrams, illustrations, source quotations, a waveform, or speaker indicators. Use only elements that clarify the episode; do not let the included sample renderer define the video's structure or look.

`scripts/render_video.py` is an optional minimal starter: it draws a title, current speech text, progress, and audio activity with Pillow and encodes an MP4 with FFmpeg. Pass `--font` with a font that covers the episode language. Adapt the starter or create a different renderer when the brief calls for another layout, aspect ratio, motion style, subtitle treatment, or visual material. Keep narration and visual timing aligned. Do not use a graphical editing application as the implementation path.

Preserve the rendering code, settings, source script, audio and timing references, subtitles, fonts and other assets needed for reproduction, and final video. Store assets with the project or document stable paths; the starter's `video-project.json` records absolute paths and does not package them automatically.

Review representative frames and a short encoded sample for text legibility, glyphs, clipping, timing, and audio/video synchronization. Check that the final video covers the complete episode unless the user requested an excerpt.
