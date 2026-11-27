import os
import glob
import subprocess
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Upper bounds so a hung yt-dlp process can never block a worker slot indefinitely.
METADATA_TIMEOUT_SECONDS = 180
AUDIO_DOWNLOAD_TIMEOUT_SECONDS = 2400
SECTION_DOWNLOAD_TIMEOUT_SECONDS = 600


def _run(cmd: List[str], timeout: int, what: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{what} timed out after {timeout}s") from e


class YouTubeStreamService:
    """
    Handles YouTube streams and videos up to 30 hours long.
    Crucial optimization: Never downloads the multi-gigabyte video stream up-front.
    Only extracts stream metadata and low-bitrate audio for energy spike analysis,
    then uses surgical byte-range section cutting (--download-sections).
    """

    @staticmethod
    def extract_metadata(url: str) -> Dict[str, Any]:
        """Extracts video metadata without downloading any media payload."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            "--socket-timeout", "30",
            "--",
            url,
        ]
        result = _run(cmd, METADATA_TIMEOUT_SECONDS, "Fetching YouTube stream details")
        if result.returncode != 0:
            logger.error(f"Failed to extract metadata for {url}: {result.stderr}")
            raise RuntimeError(f"Could not fetch YouTube stream details: {result.stderr.strip()[-300:]}")

        try:
            # yt-dlp may output multiple lines if warnings occur; take the last JSON line
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            info = json.loads(lines[-1])
            return {
                "id": info.get("id") or "video",
                "title": info.get("title") or "Untitled Gaming Stream",
                "channel": info.get("uploader") or info.get("channel") or "Unknown Creator",
                "duration": float(info.get("duration") or 0),
                "thumbnail": info.get("thumbnail"),
                "is_live": bool(info.get("is_live", False)),
                "was_live": bool(info.get("was_live", False)),
                "view_count": int(info.get("view_count") or 0),
            }
        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"Unexpected metadata parse error for {url}: {e}")
            raise RuntimeError(f"Could not parse YouTube stream details: {str(e)}") from e

    @staticmethod
    def download_lightweight_audio(url: str, output_path: str) -> str:
        """
        Downloads only compressed, low-bitrate mono audio (64kbps MP3)
        for audio energy/amplitude spike detection.
        """
        out_dir = os.path.dirname(output_path) or "."
        os.makedirs(out_dir, exist_ok=True)
        stem, _ = os.path.splitext(output_path)
        template = f"{stem}.%(ext)s"

        cmd = [
            "yt-dlp",
            "-f", "ba/b",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "64K",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000",
            "-o", template,
            "--no-playlist",
            "--",
            url,
        ]
        logger.info(f"Downloading lightweight audio for spike analysis: {url}")
        result = _run(cmd, AUDIO_DOWNLOAD_TIMEOUT_SECONDS, "Audio download")
        if result.returncode != 0:
            logger.error(f"yt-dlp audio download failed: {result.stderr}")
            raise RuntimeError(f"Failed to fetch audio stream: {result.stderr.strip()[-300:]}")

        expected_mp3 = f"{stem}.mp3"
        if os.path.exists(expected_mp3):
            return expected_mp3
        if os.path.exists(output_path):
            return output_path

        matches = glob.glob(f"{glob.escape(stem)}.*")
        if matches:
            return matches[0]
        raise FileNotFoundError(f"Expected audio output near {output_path} not found.")

    @staticmethod
    def download_exact_video_section(
        url: str,
        start_seconds: float,
        end_seconds: float,
        output_filepath: str,
        target_resolution: str = "1080p",
    ) -> str:
        """
        Surgically downloads ONLY the specified 15-30 second slice of video
        directly from YouTube using --download-sections "*start-end".
        """
        out_dir = os.path.dirname(output_filepath) or "."
        os.makedirs(out_dir, exist_ok=True)
        stem, _ = os.path.splitext(output_filepath)
        template = f"{stem}.%(ext)s"

        if target_resolution == "1080p":
            format_spec = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif target_resolution == "720p":
            format_spec = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:
            format_spec = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best"

        start_sec = max(0, int(start_seconds))
        end_sec = max(start_sec + 2, int(end_seconds))
        section_arg = f"*{start_sec}-{end_sec}"

        cmd = [
            "yt-dlp",
            "--download-sections", section_arg,
            "-f", format_spec,
            "--merge-output-format", "mp4",
            "--force-keyframes-at-cuts",
            "-o", template,
            "--no-playlist",
            "--",
            url,
        ]

        logger.info(f"Surgically cutting section {section_arg} for {url}")
        result = _run(cmd, SECTION_DOWNLOAD_TIMEOUT_SECONDS, f"Video section download {section_arg}")
        if result.returncode != 0:
            logger.error(f"yt-dlp surgical section download failed: {result.stderr}")
            raise RuntimeError(f"Failed to download video section: {result.stderr.strip()[-300:]}")

        expected_mp4 = f"{stem}.mp4"
        if os.path.exists(expected_mp4):
            return expected_mp4
        if os.path.exists(output_filepath):
            return output_filepath

        for ext in (".mp4", ".mkv", ".webm"):
            alt_path = f"{stem}{ext}"
            if os.path.exists(alt_path):
                return alt_path

        matches = glob.glob(f"{glob.escape(stem)}.*")
        if matches:
            return matches[0]
        raise FileNotFoundError(f"Expected cut output at {output_filepath} not found.")
