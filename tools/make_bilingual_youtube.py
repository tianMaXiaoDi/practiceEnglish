import argparse
import csv
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path


WHISPERCPP_URL = "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en-q5_1.bin?download=true"
MODEL_FILE = "ggml-tiny.en-q5_1.bin"


def run(cmd, cwd=None):
    print("+ " + " ".join(str(x) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=cwd, check=True)


def run_capture(cmd):
    return subprocess.check_output([str(x) for x in cmd], text=True, stderr=subprocess.STDOUT).strip()


def script_dir():
    return Path(__file__).resolve().parent


def find_exe(name):
    found = shutil.which(name)
    if found:
        return Path(found)
    return None


def find_ffmpeg(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
    found = find_exe("ffmpeg")
    if found:
        return found
    candidates = list(Path.cwd().glob("**/ffmpeg.exe"))
    if candidates:
        return candidates[0]
    raise SystemExit("ffmpeg not found. Install ffmpeg or pass --ffmpeg <path-to-ffmpeg.exe>.")


def find_deno(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
    found = find_exe("deno")
    if found:
        return found
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    try:
        if local.exists():
            hits = list(local.glob("DenoLand.Deno*/deno.exe"))
            if hits:
                return hits[0]
    except OSError:
        return None
    return None


def require_python_module(module, package=None):
    try:
        return __import__(module)
    except ImportError as exc:
        package = package or module
        print(f"Installing missing Python package: {package}", flush=True)
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", package],
                check=True,
            )
            return __import__(module)
        except Exception as install_exc:
            raise SystemExit(
                f"Missing Python package '{package}'. Install it with: python -m pip install --user {package}"
            ) from install_exc


def download_file(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    print(f"Downloading {url}", flush=True)
    urllib.request.urlretrieve(url, path)


def ensure_whispercpp(work_dir, whispercpp_dir=None, model_url=MODEL_URL, model_file=MODEL_FILE):
    base = Path(whispercpp_dir) if whispercpp_dir else work_dir / "whispercpp"
    exe = base / "bin" / "Release" / "whisper-cli.exe"
    if not exe.exists():
        zip_path = base / "whisper-bin-x64.zip"
        download_file(WHISPERCPP_URL, zip_path)
        (base / "bin").mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(base / "bin")
    if not exe.exists():
        raise SystemExit(f"whisper-cli.exe not found after setup: {exe}")

    model = base / "models" / model_file
    if not model.exists():
        download_file(model_url, model)
    return exe, model


def yt_dlp_download(url, out_dir, ffmpeg, cookies=None, deno=None):
    require_python_module("yt_dlp", "yt-dlp")
    output_template = out_dir / "source.%(ext)s"
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ffmpeg-location",
        str(ffmpeg.parent),
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_template),
    ]
    if cookies and Path(cookies).exists():
        cmd += ["--cookies", str(Path(cookies))]
    if deno:
        cmd += ["--js-runtimes", f"deno:{deno}", "--remote-components", "ejs:github"]
    cmd.append(url)

    try:
        run(cmd)
    except subprocess.CalledProcessError:
        # yt-dlp can fail on Windows after completing downloads when a .part file is locked.
        part = out_dir / "source.f399.mp4.part"
        video = out_dir / "source.f399.mp4"
        audio = next(iter(out_dir.glob("source.f251*.webm")), None)
        if part.exists() and audio:
            try:
                part.rename(video)
            except OSError:
                time.sleep(2)
                part.rename(video)
            merged = out_dir / "source.mp4"
            run([ffmpeg, "-y", "-i", video, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", merged])
            return merged
        raise

    mp4 = out_dir / "source.mp4"
    if mp4.exists():
        return mp4
    files = sorted(out_dir.glob("source*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if files:
        return files[0]
    raise SystemExit("Download completed but source MP4 was not found.")


def ass_time_from_ms(ms):
    seconds = max(0, ms / 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - math.floor(seconds)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text):
    text = html.unescape((text or "").strip())
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def ffmpeg_filter_path(path):
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:")


def write_ass(path, rows):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EN,Arial,48,&H00FFFFFF,&H00FFFFFF,&H00131313,&H90000000,-1,0,0,0,100,100,0,0,1,4,1,2,120,120,128,1
Style: ZH,Microsoft YaHei,54,&H00F6F6F6,&H00FFFFFF,&H00131313,&H90000000,-1,0,0,0,100,100,0,0,1,4,1,2,120,120,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with path.open("w", encoding="utf-8-sig", newline="\n") as f:
        f.write(header)
        for row in rows:
            f.write(f"Dialogue: 0,{ass_time_from_ms(row['start'])},{ass_time_from_ms(row['end'])},EN,,0,0,0,,{ass_escape(row['en'])}\n")
            f.write(f"Dialogue: 0,{ass_time_from_ms(row['start'])},{ass_time_from_ms(row['end'])},ZH,,0,0,0,,{ass_escape(row['zh'])}\n")


def translate_lines(lines):
    deep_translator = require_python_module("deep_translator", "deep-translator")
    translator = deep_translator.GoogleTranslator(source="en", target="zh-CN")
    translated = []
    for i, line in enumerate(lines, 1):
        print(f"Translating {i}/{len(lines)}", flush=True)
        for attempt in range(4):
            try:
                translated.append(translator.translate(line))
                break
            except Exception:
                if attempt == 3:
                    translated.append("")
                else:
                    time.sleep(2 + attempt)
    return translated


def transcribe_with_whispercpp(whisper_cli, model, wav, out_prefix, language="en"):
    run([whisper_cli, "-m", model, "-f", wav, "-l", language, "-oj", "-osrt", "-of", out_prefix])
    json_path = Path(str(out_prefix) + ".json")
    if not json_path.exists():
        raise SystemExit(f"Whisper JSON not created: {json_path}")
    return json_path


def make_wav(ffmpeg, source, wav, start=None, duration=None):
    cmd = [ffmpeg, "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", source]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", wav]
    run(cmd)


def burn_subtitles(ffmpeg, source, ass, output, start=None, duration=None):
    cmd = [ffmpeg, "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", source]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf",
        f"subtitles='{ffmpeg_filter_path(ass)}'",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output,
    ]
    run(cmd)


def preview_frame(ffmpeg, output, preview):
    run([ffmpeg, "-y", "-ss", "1", "-i", output, "-vframes", "1", preview])


def seconds_to_stamp(seconds):
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - math.floor(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def clean_filename(value):
    value = re.sub(r"https?://", "", value or "video", flags=re.I)
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff._-]+", "-", value).strip("-._")
    return value[:80] or "video"


def rows_from_whisper_json(json_path):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("transcription", [])
    english = [" ".join((item.get("text") or "").split()) for item in items]
    chinese = translate_lines(english)
    rows = []
    for i, item in enumerate(items):
        if not english[i]:
            continue
        offsets = item.get("offsets", {})
        rows.append(
            {
                "id": f"s{i + 1:04d}",
                "index": i + 1,
                "start": int(offsets.get("from", 0)),
                "end": int(offsets.get("to", 0)),
                "en": english[i],
                "zh": chinese[i],
            }
        )
    return rows


def build_segments(rows):
    segments = []
    for row in rows:
        start_ms = int(row["start"])
        end_ms = int(row["end"])
        segments.append(
            {
                "id": row["id"],
                "index": row["index"],
                "startMs": start_ms,
                "endMs": end_ms,
                "start": start_ms / 1000,
                "end": end_ms / 1000,
                "duration": max(0, end_ms - start_ms) / 1000,
                "startText": seconds_to_stamp(start_ms / 1000),
                "endText": seconds_to_stamp(end_ms / 1000),
                "english": row["en"],
                "chinese": row["zh"],
            }
        )
    return segments


def write_segments(path, segments, meta):
    payload = {
        "schemaVersion": 1,
        "meta": meta,
        "segments": segments,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_study_tsv(path, segments):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["index", "start", "end", "english", "chinese", "notes"])
        for seg in segments:
            writer.writerow([seg["index"], seg["startText"], seg["endText"], seg["english"], seg["chinese"], ""])


def write_anki_csv(path, segments):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["English", "Chinese", "Time", "Tags"])
        for seg in segments:
            writer.writerow([seg["english"], seg["chinese"], seg["startText"], "practiceEnglish"])


def write_attempts_seed(path):
    if not path.exists():
        path.write_text(
            json.dumps({"schemaVersion": 1, "attempts": [], "stars": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def write_practice_html(path, segments, meta):
    template = script_dir() / "templates" / "practice.html"
    if not template.exists():
        raise SystemExit(f"practice.html template not found: {template}")
    content = template.read_text(encoding="utf-8")
    content = content.replace("__SEGMENTS_JSON__", json.dumps(segments, ensure_ascii=False))
    content = content.replace("__PROJECT_META_JSON__", json.dumps(meta, ensure_ascii=False))
    path.write_text(content, encoding="utf-8")


def copy_source_to_project(source, out_dir):
    target = out_dir / "source.mp4"
    source = Path(source).resolve()
    if source == target.resolve():
        return target
    if not target.exists():
        shutil.copy2(source, target)
    return target


def main():
    parser = argparse.ArgumentParser(description="Create a local English study pack from YouTube/local videos.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url")
    src.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("projects") / "study-pack")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--start", type=float)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--cookies", type=Path)
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--deno", type=Path)
    parser.add_argument("--whispercpp-dir", type=Path)
    parser.add_argument("--model-url", default=MODEL_URL)
    parser.add_argument("--model-file", default=MODEL_FILE)
    parser.add_argument("--project-title")
    parser.add_argument("--no-copy-source", action="store_true")
    args = parser.parse_args()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg(args.ffmpeg)
    deno = find_deno(args.deno) if args.url else None
    cookies = args.cookies or (out_dir / "cookies.txt")
    cookies = cookies if cookies.exists() else None

    if args.url:
        source = yt_dlp_download(args.url, out_dir, ffmpeg, cookies=cookies, deno=deno)
    else:
        source = args.input.resolve()
        if not source.exists():
            raise SystemExit(f"Input video not found: {source}")

    project_source = source if args.no_copy_source else copy_source_to_project(source, out_dir)
    title = args.project_title or clean_filename(Path(source).stem if args.input else args.url)
    wav = out_dir / "audio.wav"
    ass = out_dir / "bilingual.ass"
    output = args.output.resolve() if args.output else out_dir / "bilingual.mp4"
    preview = out_dir / "preview.jpg"

    make_wav(ffmpeg, source, wav, start=args.start, duration=args.duration)
    whisper_cli, model = ensure_whispercpp(out_dir, args.whispercpp_dir, args.model_url, args.model_file)
    json_path = transcribe_with_whispercpp(whisper_cli, model, wav, out_dir / "transcript", language="en")
    rows = rows_from_whisper_json(json_path)
    segments = build_segments(rows)
    meta = {
        "title": title,
        "source": str(project_source.name if not args.no_copy_source else Path(source).resolve()),
        "video": output.name,
        "start": args.start or 0,
        "duration": args.duration,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_ass(ass, rows)
    write_segments(out_dir / "segments.json", segments, meta)
    write_study_tsv(out_dir / "study.tsv", segments)
    write_anki_csv(out_dir / "anki.csv", segments)
    write_attempts_seed(out_dir / "attempts.json")
    (out_dir / "recordings").mkdir(exist_ok=True)
    write_practice_html(out_dir / "practice.html", segments, meta)
    burn_subtitles(ffmpeg, source, ass, output, start=args.start, duration=args.duration)
    preview_frame(ffmpeg, output, preview)

    print(f"Wrote video: {output}", flush=True)
    print(f"Wrote subtitles: {ass}", flush=True)
    print(f"Wrote segments: {out_dir / 'segments.json'}", flush=True)
    print(f"Wrote study table: {out_dir / 'study.tsv'}", flush=True)
    print(f"Wrote Anki CSV: {out_dir / 'anki.csv'}", flush=True)
    print(f"Wrote practice page: {out_dir / 'practice.html'}", flush=True)
    print(f"Wrote preview: {preview}", flush=True)


if __name__ == "__main__":
    main()
