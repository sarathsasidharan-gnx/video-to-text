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

## Offline / air-gapped install

For a machine that cannot reach PyPI or Hugging Face, use the **offline bundle**
on the [Releases page](https://github.com/sarathsasidharan-gnx/video-to-text/releases).

On the target machine you need only **Python 3.13** installed (any patch
version — 3.13.0, 3.13.7, whatever) plus ffmpeg on PATH.

1. Clone or download this repo.
2. From the latest Release, download and extract **next to `app.py`**:
   - `wheels.zip`  → gives you `wheels\` (every package, no download needed)
   - `models.zip`  → gives you `models\` (Whisper + alignment models)
3. Run **`install_offline.bat`**.
4. Put files in `input\`, run `Transcribe.bat`.

`install_offline.bat` passes `--no-index` to pip, so it physically cannot reach
the network — if it succeeds, the install is genuinely self-contained.

Models are read from `models\` in the project folder (the app sets `HF_HOME`
and `TORCH_HOME` there), so nothing is fetched at run time either.

### Why not commit the venv?

A virtual environment is not portable: it contains no Python of its own, bakes
absolute paths into `pyvenv.cfg` and 43 script shims, and holds files up to
2.2 GB that GitHub refuses outright (100 MB hard limit). Shipping wheels and
rebuilding on the target is both smaller and version-safe — the wheels are
`cp313`, and CPython keeps a stable ABI across all 3.13.x releases.

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
