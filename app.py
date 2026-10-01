#!/usr/bin/env python3
"""
CPU-only speaker-labelled transcription with WhisperX.

How to use it
-------------
  1. Drop video or audio files into the  input\\  folder.
  2. Double-click  Transcribe.bat   (or run:  python app.py)
  3. Transcripts appear in the  output\\  folder.

For every input file, three outputs are written:
  <name>.txt   - readable transcript, one block per speaker turn
  <name>.srt   - subtitles with speaker prefixes
  <name>.json  - full structured output (segment + word level timings)

A file is skipped if its .txt already exists in output\\, so re-running only
picks up what is new. Delete the .txt to force a redo.

Setup (once)
------------
  setup.bat                    # creates .venv and installs everything
  ffmpeg must be on PATH:  winget install Gyan.FFmpeg

Speaker labels (optional)
-------------------------
Without a Hugging Face token you still get a full transcript, just no
"SPEAKER_01" labels - everything lands in one block. To enable them:
  1. https://huggingface.co/settings/tokens  -> create a READ token
  2. Accept the licence on BOTH of these pages while logged in:
       https://huggingface.co/pyannote/speaker-diarization-community-1
       https://huggingface.co/pyannote/segmentation-3.0
  3. setx HF_TOKEN hf_xxxxx     then open a new window

Settings live in the CONFIG block below - edit them there.
"""

import json
import os
import sys
import time
from pathlib import Path

# ----------------------------------------------------------------------- CONFIG
MODEL = "small"      # tiny | base | small | medium | large-v3  (bigger = slower)
LANGUAGE = None      # None = auto-detect, or force a code like "en", "hi", "ml"
ALIGN = True         # word-level timestamps
DIARIZE = True       # speaker labels (needs HF_TOKEN, see above)
SPEAKERS = None      # exact speaker count if you know it, else None
BATCH_SIZE = 4       # keep small on CPU
THREADS = max(1, (os.cpu_count() or 4) - 1)
# --------------------------------------------------------------------------- end

HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "input"
OUTPUT_DIR = HERE / "output"
MODELS_DIR = HERE / "models"

# Keep downloaded models inside the project instead of the user profile, so an
# offline machine can be handed a models\ folder and never reach the internet.
# Set HF_HOME / TORCH_HOME yourself beforehand to override this.
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(MODELS_DIR / "torch"))

MEDIA_EXTS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
}

DEVICE = "cpu"
COMPUTE_TYPE = "int8"  # float16 is GPU-only; int8 is the right CPU choice

# Keep thread libraries from fighting each other on CPU.
os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 4) // 2)))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# ------------------------------------------------------------------------ output
def ts(seconds, srt=False):
    """Seconds -> 00:01:23,456 (srt) or 00:01:23 (readable)."""
    seconds = max(0.0, float(seconds or 0))
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{int((seconds % 1) * 1000):03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def merge_turns(segments):
    """Collapse consecutive segments from the same speaker into one turn."""
    turns = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        who = seg.get("speaker", "SPEAKER_??")
        if turns and turns[-1]["speaker"] == who:
            turns[-1]["text"] += " " + text
            turns[-1]["end"] = seg.get("end", turns[-1]["end"])
        else:
            turns.append(
                {"speaker": who, "start": seg.get("start", 0.0),
                 "end": seg.get("end", 0.0), "text": text}
            )
    return turns


def write_outputs(result, stem):
    segments = result.get("segments", [])

    # JSON - everything, including per-word timings
    (OUTPUT_DIR / f"{stem}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # TXT - readable speaker turns
    turns = merge_turns(segments)
    lines = [f"[{ts(t['start'])} - {ts(t['end'])}] {t['speaker']}\n{t['text']}\n"
             for t in turns]
    (OUTPUT_DIR / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")

    # SRT - subtitles
    srt = []
    for i, seg in enumerate(segments, 1):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        who = seg.get("speaker")
        srt.append(
            f"{i}\n{ts(seg.get('start'), True)} --> {ts(seg.get('end'), True)}\n"
            f"{(who + ': ') if who else ''}{text}\n"
        )
    (OUTPUT_DIR / f"{stem}.srt").write_text("\n".join(srt), encoding="utf-8")

    return turns


# -------------------------------------------------------------------------- work
def transcribe_one(src, whisperx, model, align_cache, diarizer):
    """Transcribe one file and write its three outputs. Returns elapsed seconds."""
    t0 = time.time()

    audio = whisperx.load_audio(str(src))
    minutes = len(audio) / 16000 / 60
    print(f"  duration: {minutes:.1f} min", flush=True)

    result = model.transcribe(audio, batch_size=BATCH_SIZE)
    language = result.get("language", LANGUAGE or "en")
    print(f"  language: {language} | segments: {len(result.get('segments', []))}",
          flush=True)

    # word-level timestamps
    if ALIGN:
        print("  aligning word timings...", flush=True)
        try:
            if language not in align_cache:
                align_cache[language] = whisperx.load_align_model(
                    language_code=language, device=DEVICE
                )
            align_model, meta = align_cache[language]
            result = whisperx.align(
                result["segments"], align_model, meta, audio, DEVICE,
                return_char_alignments=False,
            )
            result["language"] = language
        except Exception as e:
            print(f"  ! alignment skipped ({e}) - segment timings retained", flush=True)

    # speaker labels
    if diarizer is not None:
        print("  identifying speakers...", flush=True)
        try:
            kwargs = {"num_speakers": SPEAKERS} if SPEAKERS else {}
            diarization = diarizer(audio, **kwargs)
            result = whisperx.assign_word_speakers(diarization, result)
            found = {s.get("speaker") for s in result["segments"] if s.get("speaker")}
            print(f"  speakers found: {len(found)}", flush=True)
        except Exception as e:
            print(f"  ! diarization failed ({e}) - transcript kept without speakers",
                  flush=True)

    turns = write_outputs(result, src.stem)
    elapsed = time.time() - t0
    print(f"  done in {elapsed/60:.1f} min -> {src.stem}.txt / .srt / .json",
          flush=True)
    if turns:
        print(f"  first line: {turns[0]['text'][:80]}", flush=True)
    return elapsed


def load_diarizer(whisperx):
    """Build the speaker-labelling pipeline, or return None with a reason printed."""
    if not DIARIZE:
        return None
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("HF_TOKEN not set - transcripts will have no speaker labels.")
        print("  (see the notes at the top of app.py to enable them)\n")
        return None
    try:
        return whisperx.diarize.DiarizationPipeline(use_auth_token=token, device=DEVICE)
    except Exception as e:
        print(f"! could not load the speaker model ({e}) - carrying on without\n")
        return None


# -------------------------------------------------------------------------- main
def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)

    found = sorted(f for f in INPUT_DIR.iterdir()
                   if f.is_file() and f.suffix.lower() in MEDIA_EXTS)
    todo = [f for f in found if not (OUTPUT_DIR / f"{f.stem}.txt").exists()]
    skipped = len(found) - len(todo)

    print(f"input : {INPUT_DIR}")
    print(f"output: {OUTPUT_DIR}\n")

    if not found:
        print("Nothing to do - the input folder is empty.")
        print("Put your video or audio files in it and run this again.")
        return 0
    if not todo:
        print(f"All {len(found)} file(s) already transcribed. Nothing new to do.")
        print("Delete a .txt from the output folder to redo that one.")
        return 0

    if skipped:
        print(f"Skipping {skipped} file(s) already transcribed.")
    print(f"Transcribing {len(todo)} file(s) with '{MODEL}' on CPU "
          f"({THREADS} threads).")
    print("The first run also downloads the model - that part is one-off.\n")

    # torchaudio/torchcodec grumble about optional ffmpeg shared libs they never
    # use here (audio reaches whisperx as a numpy array via the ffmpeg binary).
    import warnings

    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    import torch
    import whisperx

    torch.set_num_threads(THREADS)

    # Loaded once and reused for every file.
    model = whisperx.load_model(
        MODEL, device=DEVICE, compute_type=COMPUTE_TYPE,
        threads=THREADS, language=LANGUAGE,
    )
    diarizer = load_diarizer(whisperx)
    align_cache = {}

    total = 0.0
    failed = []
    for i, src in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {src.name}", flush=True)
        try:
            total += transcribe_one(src, whisperx, model, align_cache, diarizer)
        except Exception as e:
            print(f"  ! FAILED: {type(e).__name__}: {e}", flush=True)
            failed.append(src.name)
        print(flush=True)

    done = len(todo) - len(failed)
    print(f"Finished {done}/{len(todo)} file(s) in {total/60:.1f} min.")
    if failed:
        print("Failed: " + ", ".join(failed))
    print(f"Transcripts are in: {OUTPUT_DIR}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        status = main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        status = 130
    except Exception:
        import traceback

        traceback.print_exc()
        status = 1

    try:
        input("\nPress Enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass
    sys.exit(status)
