# Product Spec: Local English Shadowing Lab

## Problem

Normal bilingual videos help with listening comprehension, but they do not force active speaking.

The missing loop is:

```text
hear original sentence -> speak it aloud -> get feedback -> repeat weak sentences
```

## Target User

The first target user is one learner using a local Windows machine to practice English from real YouTube videos or MP4 files.

## Core Learning Modes

### 1. Watch

- Play the original or generated bilingual video.
- Switch between bilingual, English-only, and no-subtitle modes when available.
- Click a subtitle sentence to jump to that sentence.

### 2. Listen

- Play a single sentence.
- Loop a sentence.
- Slow playback to 0.75x or 0.85x.
- Repeat difficult sentences.

### 3. Shadow

- Play the original sentence.
- Record the learner speaking the same sentence.
- Play back the learner recording.
- Save each attempt.

### 4. Check

First version uses text-level checking, not professional phoneme-level pronunciation scoring.

The system should:

- transcribe the learner recording
- compare learner transcript with the original English sentence
- mark missing words
- mark extra words
- mark likely wrong words
- calculate a 0-100 score

### 5. Review

- Keep low-score sentences.
- Keep manually starred sentences.
- Show practice count per sentence.
- Show best score and latest score.
- Export study data for Anki or spreadsheet review.

## MVP Pages

### Practice Page

Left side:

- video player
- current sentence timing
- playback controls

Right side:

- sentence list
- English sentence
- Chinese meaning
- play original
- loop
- record
- replay my recording
- score
- star sentence

Bottom panel:

- original sentence
- learner transcript
- highlighted diff
- score
- attempt history

## Non Goals For MVP

- login
- cloud sync
- social feed
- mini program
- leaderboard
- payment
- full mobile UI
- professional phoneme-level pronunciation scoring

## Success Criteria

The MVP is useful if one learner can practice 20 minutes per day with less friction than manually pausing a video and recording separately.
