
import streamlit as st
import tempfile
import os
import subprocess
import re
import imageio_ffmpeg
from faster_whisper import WhisperModel

st.set_page_config(
    page_title="ClipGenius AI",
    page_icon="🎬",
    layout="centered"
)

@st.cache_resource
def load_model():
    return WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8"
    )

def score_text(text):
    words = re.findall(r"\b\w+\b", text.lower())

    if not words:
        return 0

    hooks = [
        "wait", "what", "why", "how", "crazy",
        "insane", "actually", "never", "best",
        "worst", "secret", "funny", "imagine",
        "bro", "seriously", "unbelievable",
        "believe", "wow", "amazing"
    ]

    hook_score = sum(w in hooks for w in words)
    questions = text.count("?")
    excitement = text.count("!")
    length_score = min(len(words) / 35, 1)

    score = (
        hook_score * 5
        + questions * 4
        + excitement * 3
        + length_score * 15
    )

    return min(round(score), 100)


def find_highlights(segments, duration):
    candidates = []

    start = 0
    clip_length = 30
    step = 10

    while start < duration:
        end = min(start + clip_length, duration)

        text = " ".join(
            seg.text.strip()
            for seg in segments
            if seg.start < end and seg.end > start
        )

        if len(text.split()) >= 12:
            candidates.append({
                "start": start,
                "end": end,
                "text": text,
                "score": score_text(text)
            })

        start += step

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    selected = []

    for candidate in candidates:
        overlaps = any(
            candidate["start"] < item["end"]
            and candidate["end"] > item["start"]
            for item in selected
        )

        if not overlaps:
            selected.append(candidate)

        if len(selected) == 5:
            break

    return selected


def make_clip(input_path, start, end, output_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg, "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(end - start),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1000:])


st.title("🎬 ClipGenius AI")
st.caption("Find your best moments. Create your Shorts.")

st.divider()

st.subheader("1. Upload your video")

st.info(
    "Upload a video you own or have permission to edit. "
    "YouTube links are references only in this version."
)

video = st.file_uploader(
    "Choose your video",
    type=["mp4", "mov", "mkv", "webm"]
)

if video:

    st.video(video)

    if st.button(
        "✨ Find my best clips",
        type="primary",
        use_container_width=True
    ):

        try:
            with tempfile.TemporaryDirectory() as folder:

                input_path = os.path.join(
                    folder, "original.mp4"
                )

                audio_path = os.path.join(
                    folder, "audio.wav"
                )

                with open(input_path, "wb") as f:
                    f.write(video.getbuffer())

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

                extract = subprocess.run(
                    [
                        ffmpeg, "-y",
                        "-i", input_path,
                        "-vn",
                        "-ac", "1",
                        "-ar", "16000",
                        audio_path
                    ],
                    capture_output=True,
                    text=True
                )

                if extract.returncode != 0:
                    raise RuntimeError("Audio extraction failed.")

                st.write("🎧 Analysing speech...")

                model = load_model()

                segments, info = model.transcribe(
                    audio_path,
                    vad_filter=True
                )

                transcript = list(segments)

                if not transcript:
                    st.warning("No clear speech detected.")
                    st.stop()

                duration = info.duration

                st.write("🧠 Finding interesting moments...")

                highlights = find_highlights(
                    transcript, duration
                )

                if not highlights:
                    st.warning("Couldn't find enough speech for clips.")
                    st.stop()

                results = []

                for i, item in enumerate(highlights):

                    output_path = os.path.join(
                        folder, f"clip_{i+1}.mp4"
                    )

                    make_clip(
                        input_path,
                        item["start"],
                        item["end"],
                        output_path
                    )

                    with open(output_path, "rb") as f:
                        clip_bytes = f.read()

                    results.append({
                        **item,
                        "video": clip_bytes
                    })

                st.session_state["clips"] = results

        except Exception as e:
            st.error(f"Something went wrong: {e}")

if "clips" in st.session_state:

    st.divider()
    st.header("🏆 Your best moments")

    for i, clip in enumerate(
        st.session_state["clips"]
    ):

        st.subheader(f"Clip {i+1}")

        st.progress(clip["score"] / 100)

        st.caption(
            f"Highlight score: {clip['score']}/100"
        )

        st.caption(
            f"Time: {clip['start']:.0f}s – "
            f"{clip['end']:.0f}s"
        )

        st.write(clip["text"])

        st.video(clip["video"])

        st.download_button(
            f"⬇️ Download Clip {i+1}",
            data=clip["video"],
            file_name=f"clipgenius_{i+1}.mp4",
            mime="video/mp4",
            key=f"download_{i}"
        )

st.divider()

st.caption("ClipGenius AI | AI Highlight Finder v2")
