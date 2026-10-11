# Video workflow

Use the episode's combined WAV or MP3 and `timing.json`. `scripts/render_video.py` generates subtitles and draws the title card, current spoken line, progress, and audio activity directly with Pillow. FFmpeg receives the generated frames and encodes the MP4 with the episode audio. No graphical editing application is involved.

Default to 1920×1080, 16:9, with readable high-contrast type and no background music. A user can choose another size or aspect ratio. Keep `video-project.json` (render settings and source paths), `subtitles.srt`, any added assets, the renderer script, and `video.mp4`. Fonts or art should have stable paths or be copied into the project when permitted.

At minimum, review a preview frame and a short encoded sample for Chinese glyphs, text clipping, subtitle timing, and audio/video synchronization. A full video must match the full episode duration. Re-run from the saved project settings to reproduce it.
