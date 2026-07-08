import argparse
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


MODEL_FILE = "ggml-tiny.en-q5_1.bin"


def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def find_exe(name):
    found = shutil.which(name)
    return Path(found) if found else None


def find_ffmpeg(explicit=None, project_dir=None):
    if explicit and Path(explicit).exists():
        return Path(explicit)
    found = find_exe("ffmpeg")
    if found:
        return found
    if project_dir:
        hits = list(Path(project_dir).glob("**/ffmpeg.exe"))
        if hits:
            return hits[0]
    raise FileNotFoundError("ffmpeg not found. Pass --ffmpeg <path-to-ffmpeg.exe>.")


def find_whisper(whispercpp_dir, project_dir, model_file=MODEL_FILE):
    base = Path(whispercpp_dir) if whispercpp_dir else Path(project_dir) / "whispercpp"
    exe = base / "bin" / "Release" / "whisper-cli.exe"
    model = base / "models" / model_file
    if not exe.exists():
        raise FileNotFoundError(f"whisper-cli.exe not found: {exe}")
    if not model.exists():
        raise FileNotFoundError(f"Whisper model not found: {model}")
    return exe, model


def load_segments(project_dir):
    data = json.loads((Path(project_dir) / "segments.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data.get("segments", [])}


def load_attempts(path):
    if not path.exists():
        return {"schemaVersion": 1, "attempts": [], "stars": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("schemaVersion", 1)
    data.setdefault("attempts", [])
    data.setdefault("stars", [])
    return data


def save_attempts(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", (text or "").lower())


def compare_words(expected, actual):
    import difflib

    exp = normalize_words(expected)
    act = normalize_words(actual)
    matcher = difflib.SequenceMatcher(a=exp, b=act)
    tokens = []
    missing = []
    extra = []
    changed = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for word in exp[i1:i2]:
                tokens.append({"text": word, "kind": "ok"})
        elif tag == "delete":
            for word in exp[i1:i2]:
                missing.append(word)
                tokens.append({"text": word, "kind": "missing"})
        elif tag == "insert":
            for word in act[j1:j2]:
                extra.append(word)
                tokens.append({"text": word, "kind": "extra"})
        elif tag == "replace":
            expected_words = exp[i1:i2]
            actual_words = act[j1:j2]
            changed.append({"expected": expected_words, "actual": actual_words})
            for word in expected_words:
                missing.append(word)
                tokens.append({"text": word, "kind": "missing"})
            for word in actual_words:
                extra.append(word)
                tokens.append({"text": word, "kind": "extra"})

    score = round(max(0, matcher.ratio() * 100 - len(missing) * 2 - len(extra)))
    return {
        "score": score,
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "tokens": tokens,
    }


def transcribe_recording(ffmpeg, whisper_cli, model, input_audio, output_prefix):
    wav = Path(str(output_prefix) + ".16k.wav")
    run([ffmpeg, "-y", "-i", input_audio, "-ac", "1", "-ar", "16000", wav])
    run([whisper_cli, "-m", model, "-f", wav, "-l", "en", "-oj", "-of", output_prefix])
    json_path = Path(str(output_prefix) + ".json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    texts = [" ".join((item.get("text") or "").split()) for item in data.get("transcription", [])]
    return " ".join(text for text in texts if text)


def extension_from_content_type(content_type):
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if content_type == "audio/webm":
        return ".webm"
    if content_type == "audio/mp4":
        return ".m4a"
    if content_type == "audio/wav":
        return ".wav"
    return mimetypes.guess_extension(content_type) or ".webm"


def make_handler(project_dir, ffmpeg, whisper_cli, model):
    project_dir = Path(project_dir).resolve()
    segments = load_segments(project_dir)
    attempts_path = project_dir / "attempts.json"
    recordings_dir = project_dir / "recordings"
    recordings_dir.mkdir(exist_ok=True)

    class PracticeHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(project_dir), **kwargs)

        def _json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self._json(200, load_attempts(attempts_path))
                return
            if parsed.path == "/":
                self.path = "/practice.html"
            super().do_GET()

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/stars":
                query = parse_qs(parsed.query)
                segment_id = (query.get("segment_id") or [""])[0]
                if segment_id not in segments:
                    self._json(400, {"error": f"unknown segment_id: {segment_id}"})
                    return
                data = load_attempts(attempts_path)
                stars = set(data.get("stars", []))
                if segment_id in stars:
                    stars.remove(segment_id)
                    starred = False
                else:
                    stars.add(segment_id)
                    starred = True
                data["stars"] = sorted(stars)
                save_attempts(attempts_path, data)
                self._json(200, {"segmentId": segment_id, "starred": starred, "state": data})
                return

            if parsed.path != "/api/attempts":
                self._json(404, {"error": "not found"})
                return

            query = parse_qs(parsed.query)
            segment_id = (query.get("segment_id") or [""])[0]
            segment = segments.get(segment_id)
            if not segment:
                self._json(400, {"error": f"unknown segment_id: {segment_id}"})
                return

            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self._json(400, {"error": "empty recording"})
                return

            attempt_id = str(uuid.uuid4())
            ext = extension_from_content_type(self.headers.get("Content-Type"))
            audio_path = recordings_dir / f"{segment_id}_{attempt_id}{ext}"
            audio_path.write_bytes(self.rfile.read(length))
            prefix = recordings_dir / f"{segment_id}_{attempt_id}"

            try:
                transcript = transcribe_recording(ffmpeg, whisper_cli, model, audio_path, prefix)
                diff = compare_words(segment["english"], transcript)
                now = datetime.now().isoformat(timespec="seconds")
                attempt = {
                    "id": attempt_id,
                    "segmentId": segment_id,
                    "createdAt": now,
                    "recording": str(audio_path.relative_to(project_dir)).replace("\\", "/"),
                    "transcript": transcript,
                    "score": diff["score"],
                    "diff": diff,
                }
                data = load_attempts(attempts_path)
                data.setdefault("attempts", []).append(attempt)
                save_attempts(attempts_path, data)
                self._json(200, attempt)
            except Exception as exc:
                self._json(500, {"error": str(exc)})

    return PracticeHandler


def main():
    parser = argparse.ArgumentParser(description="Serve a local Practice English study pack.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--whispercpp-dir", type=Path)
    parser.add_argument("--model-file", default=MODEL_FILE)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not (project_dir / "practice.html").exists():
        raise SystemExit(f"practice.html not found in project: {project_dir}")
    ffmpeg = find_ffmpeg(args.ffmpeg, project_dir)
    whisper_cli, model = find_whisper(args.whispercpp_dir, project_dir, args.model_file)

    handler = make_handler(project_dir, ffmpeg, whisper_cli, model)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving {project_dir}", flush=True)
    print(f"Open {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
