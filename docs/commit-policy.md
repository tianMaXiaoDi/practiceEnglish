# Commit Policy

This repository should be committed in small working stages.

## Commit After Each Stage

Commit when a milestone or clearly usable slice is complete:

- docs update
- study pack generator works
- practice page opens
- recording works
- scoring works
- review mode works

## Do Not Commit

Do not commit personal or generated artifacts:

- videos
- audio
- recordings
- cookies
- Whisper model files
- downloaded binaries
- logs
- temporary project folders

## Git Commands

Use the repository-local proxy when GitHub direct access fails:

```powershell
git config --local http.proxy http://127.0.0.1:7897
git config --local https.proxy http://127.0.0.1:7897
```

For normal staged updates:

```powershell
git status --short
git add <specific-files>
git commit -m "<short description>"
git push
```

Avoid `git add .` when generated study projects are present.
