# Video to text

Turns video or audio files into transcripts, on CPU, locally.

## Use it

1. Put your video or audio files into the **`input\`** folder.
2. Double-click **`Transcribe.bat`** (or run `python app.py`).
3. Transcripts appear in the **`output\`** folder.

That is the only mode — no dialogs, no command-line flags. Everything in
`input\` gets transcribed in one go.

A file is **skipped if its `.txt` already exists** in `output\`, so re-running
only picks up what is new. Delete a `.txt` to force that one to be redone.

The first run also downloads the Whisper model (~0.5 GB). That part is one-off.

## What you get

For `input\meeting.mp4`, in `output\`:

| File | Contents |
| --- | --- |
| `meeting.txt` | Readable transcript, one block per speaker turn |
| `meeting.srt` | Subtitles, with speaker prefixes |
| `meeting.json` | Everything, including per-word timings |

Non-media files in `input\` are ignored. If one file fails, the rest still run
and the failures are listed at the end.

## Settings

Edit the `CONFIG` block at the top of `app.py`:

```python
MODEL = "small"   # tiny | base | small | medium | large-v3  (bigger = slower)
LANGUAGE = None   # None = auto-detect, or "en", "hi", "ml", ...
ALIGN = True      # word-level timestamps
DIARIZE = True    # speaker labels (needs HF_TOKEN, see below)
SPEAKERS = None   # exact speaker count if you know it
```

Speed on this machine with `small`: roughly **35–40 s per minute of audio**, so
a 1-hour recording takes ~35 min.

## Requirements

- Python 3.9+ (tested on 3.13)
- **ffmpeg on PATH** — `winget install Gyan.FFmpeg`, then open a new window.
  Without it, video files cannot be read.
- **~6 GB free disk space.** The `.venv` alone is 3.9 GB, plus models
  (`small` ≈ 0.5 GB, alignment ≈ 0.4 GB, `large-v3` ≈ 3 GB). Running out
  mid-download shows up as `[Errno 28] No space left on device`.
  `.venv\Scripts\python -m pip cache purge` reclaims a couple of GB safely.

`setup.bat` does the rest. Run it on its own to install ahead of time or to
repair the environment.

## Speaker labels (optional)

Transcription works without this, but **everything lands in one unbroken block**
labelled `SPEAKER_??`. To get `SPEAKER_00` / `SPEAKER_01` turns:

1. Create a free **read** token at <https://huggingface.co/settings/tokens>.
2. While logged in, accept the licence on **both**:
   - <https://huggingface.co/pyannote/speaker-diarization-community-1>
   - <https://huggingface.co/pyannote/segmentation-3.0>
3. `setx HF_TOKEN hf_xxxxx` and open a new window.

Note that this separates voices but does not name them — you get
`SPEAKER_00`, not a person's actual name.
