# Roadmap

## Milestone 0: Repository Setup

- Create the local project on `D:\practiceEnglish`.
- Connect it to `tianMaXiaoDi/practiceEnglish`.
- Add product docs and the existing bilingual video tool.

## Milestone 1: Study Pack Generator

Extend the current video pipeline to output:

- `bilingual.mp4`
- `segments.json`
- `study.tsv`
- `anki.csv`

Acceptance:

- A YouTube URL or local MP4 produces a complete project folder.
- `segments.json` has start time, end time, English, and Chinese for every sentence.

## Milestone 2: Local Practice Page

Generate `practice.html` for each video project.

Acceptance:

- Open `practice.html` locally.
- Play the video.
- Click a sentence and jump to that timestamp.
- Play a single sentence.
- Loop a sentence.

## Milestone 3: Recording And Replay

Add browser recording to `practice.html`.

Acceptance:

- Record one sentence.
- Save the recording under the project folder.
- Replay the learner recording.
- Preserve attempts in `attempts.json`.

## Milestone 4: Text-Level Speech Check

Add local transcription and text comparison for learner recordings.

Acceptance:

- Transcribe learner recording.
- Compare with target sentence.
- Show missing, extra, and changed words.
- Save score per attempt.

## Milestone 5: Review Mode

Add a review workflow.

Acceptance:

- Show low-score sentences.
- Show starred sentences.
- Repeat only weak sentences.
- Export Anki CSV.

## Later Options

- Better pronunciation scoring.
- Mobile-friendly UI.
- Douyin or WeChat mini program.
- Cloud sync.
- Community challenges.
