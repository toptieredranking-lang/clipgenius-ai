
import streamlit as st
import subprocess
import tempfile
import os
import imageio_ffmpeg

st.set_page_config(
    page_title="ClipGenius AI",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 ClipGenius AI")
st.caption("Turn long videos into engaging Shorts.")

st.divider()

st.subheader("1. Your video")

youtube_url = st.text_input(
    "YouTube video link (reference only)",
    placeholder="Paste your video URL here"
)

video = st.file_uploader(
    "Upload your original video",
    type=["mp4", "mov", "mkv", "webm"]
)

if video:
    st.video(video)

    st.divider()
    st.subheader("2. Choose your clip")

    start = st.number_input(
        "Start time (seconds)",
        min_value=0,
        value=0
    )

    end = st.number_input(
        "End time (seconds)",
        min_value=1,
        value=30
    )

    if st.button("✂️ Generate my Short", type="primary"):

        if end <= start:
            st.error("End time must be after start time.")

        else:
            with st.spinner("Creating your clip..."):

                with tempfile.TemporaryDirectory() as folder:

                    input_path = os.path.join(
                        folder, "original.mp4"
                    )

                    output_path = os.path.join(
                        folder, "clipgenius_short.mp4"
                    )

                    with open(input_path, "wb") as f:
                        f.write(video.getbuffer())

                    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

                    command = [
                        ffmpeg,
                        "-y",
                        "-ss", str(start),
                        "-i", input_path,
                        "-t", str(end - start),
                        "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
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

                    if result.returncode == 0:

                        with open(output_path, "rb") as f:
                            clip_data = f.read()

                        st.success("Your Short is ready!")

                        st.video(clip_data)

                        st.download_button(
                            "⬇️ Download your Short",
                            data=clip_data,
                            file_name="clipgenius_short.mp4",
                            mime="video/mp4"
                        )

                    else:
                        st.error("Video processing failed.")
                        st.caption(result.stderr[-1500:])

else:
    st.info(
        "Upload a video you own or have permission to edit "
        "to get started."
    )

st.divider()
st.caption("ClipGenius AI | Version 1.0")
