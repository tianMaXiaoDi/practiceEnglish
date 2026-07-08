# Practice English

Practice English is a local-first English learning project built around real videos.

The goal is not just to watch English videos. The goal is to turn a video into a practice lab where a learner can:

- watch with bilingual subtitles
- listen sentence by sentence
- shadow-read out loud
- record their own voice
- compare their speech with the original sentence
- review difficult sentences later

## Product Direction

The first version is a personal local tool, not a public platform or mini program.

This keeps cost low and lets the core learning loop be tested before considering Douyin, WeChat, or other short-video platform integrations.

## MVP Scope

The first usable version should generate a local study package from a YouTube URL or local MP4:

```text
projects/
  video-name/
    source.mp4
    bilingual.mp4
    segments.json
    study.tsv
    anki.csv
    practice.html
    attempts.json
    recordings/
```

The core loop:

1. Import a video.
2. Generate English subtitles, Chinese translation, and sentence timestamps.
3. Open a local practice page.
4. Play one sentence at a time.
5. Record shadowing.
6. Transcribe the recording.
7. Compare the learner transcript with the original sentence.
8. Save scores and weak sentences.

## Current Starting Point

`tools/make_bilingual_youtube.py` contains the proven first pipeline:

- YouTube/local video input
- `yt-dlp` download with cookie/proxy support
- `ffmpeg` audio/video processing
- `whisper.cpp` transcription
- English + Chinese `.ass` subtitles
- burned-in bilingual MP4 output

The next step is to extend this pipeline so it also outputs `segments.json`, `study.tsv`, and the first `practice.html`.

## Repository Policy

Generated videos, audio files, cookies, model binaries, and personal recordings are not committed.

Only source code, documentation, templates, and small deterministic fixtures belong in Git.
