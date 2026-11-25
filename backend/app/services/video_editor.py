import os
import subprocess
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class VideoEditor:
    """
    FFmpeg video processing engine:
    - 9:16 vertical reframing (split blurred background or center crop)
    - Advanced SubStation Alpha (.ass) subtitle file creation with karaoke word highlights
    - High-performance H.264 burning and thumbnail generation
    """

    @staticmethod
    def format_ass_timestamp(seconds: float) -> str:
        """Converts float seconds to ASS format: H:MM:SS.cs"""
        seconds = max(0.0, float(seconds))
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int(round((seconds - int(seconds)) * 100))
        if centisecs >= 100:
            centisecs = 99
        return f"{hrs}:{mins:02d}:{secs:02d}.{centisecs:02d}"

    @staticmethod
    def hex_to_ass_color(color: str, fallback: str = "&H00FFFFFF") -> str:
        """Converts #RRGGBB hex or &H... ASS color into ASS &H00BBGGRR format."""
        if not color:
            return fallback
        c = color.strip()
        if c.startswith("&H") or c.startswith("&h"):
            return c
        if c.startswith("#") and len(c) == 7:
            r, g, b = c[1:3], c[3:5], c[5:7]
            return f"&H00{b.upper()}{g.upper()}{r.upper()}"
        return fallback

    @staticmethod
    def _escape_ass_text(text: str) -> str:
        """Escapes special ASS override characters so user/transcript text never corrupts tags."""
        return (
            text.replace("\\", "")
            .replace("{", "(")
            .replace("}", ")")
            .replace("\r", " ")
            .replace("\n", " ")
            .strip()
        )

    @classmethod
    def generate_ass_subtitles(
        cls,
        words_data: List[Dict[str, Any]],
        output_ass_path: str,
        style_config: Optional[Dict[str, Any]] = None,
        hook_headline: Optional[str] = None,
    ) -> str:
        """
        Creates an .ass subtitle file with TikTok/Instagram style karaoke text
        where the currently spoken word illuminates with highlight_color.
        """
        style = style_config or {}
        font_name = style.get("font_family", "Montserrat")
        font_size = int(style.get("font_size", 46))
        primary_color = cls.hex_to_ass_color(style.get("primary_color", "#FFFFFF"), "&H00FFFFFF")
        highlight_color = cls.hex_to_ass_color(style.get("highlight_color", "#FFD700"), "&H0000D7FF")
        outline_color = cls.hex_to_ass_color(style.get("outline_color", "#000000"), "&H00000000")
        outline_width = int(style.get("outline_width", 3))

        # In ASS karaoke (\k), SecondaryColour is shown BEFORE a word is spoken and PrimaryColour AFTER/DURING.
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookHeader,{font_name},48,{primary_color},{primary_color},{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,4,2,8,40,40,240,1
Style: KaraokeBody,{font_name},{font_size},{highlight_color},{primary_color},{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{outline_width},2,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        if hook_headline:
            safe_hook = cls._escape_ass_text(hook_headline).upper()
            if safe_hook:
                ass_content += f"Dialogue: 1,0:00:00.00,0:00:04.50,HookHeader,,0,0,0,,{safe_hook}\n"

        if words_data:
            chunk_size = 4
            for i in range(0, len(words_data), chunk_size):
                chunk = words_data[i:i + chunk_size]
                if not chunk:
                    continue

                chunk_start = float(chunk[0]["start"])
                chunk_end = float(chunk[-1]["end"])

                if (chunk_end - chunk_start) < 1.2:
                    chunk_end = chunk_start + 1.2

                start_ts = cls.format_ass_timestamp(chunk_start)
                end_ts = cls.format_ass_timestamp(chunk_end)

                dialogue_tokens = []
                for w in chunk:
                    duration_cs = max(10, int((float(w["end"]) - float(w["start"])) * 100))
                    safe_word = cls._escape_ass_text(str(w["word"])).upper()
                    if safe_word:
                        dialogue_tokens.append(f"{{\\k{duration_cs}}}{safe_word}")

                if dialogue_tokens:
                    karaoke_line = " ".join(dialogue_tokens)
                    ass_content += f"Dialogue: 0,{start_ts},{end_ts},KaraokeBody,,0,0,0,,{karaoke_line}\n"

        os.makedirs(os.path.dirname(output_ass_path), exist_ok=True)
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return output_ass_path

    @classmethod
    def render_vertical_reel(
        cls,
        input_video_path: str,
        output_video_path: str,
        ass_subtitles_path: Optional[str] = None,
        resolution: str = "720p",
        mode: str = "blur_split",
    ) -> str:
        """
        Converts gameplay footage into 9:16 vertical reel using FFmpeg.
        Burns subtitles and encodes with optimal fast streaming parameters.
        """
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

        if resolution == "1080p":
            width, height = 1080, 1920
        else:
            width, height = 720, 1280

        if mode == "blur_split":
            filter_complex = (
                f"[0:v]split=2[bg_in][fg_in];"
                f"[bg_in]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,boxblur=20:5[bg];"
                f"[fg_in]scale={width}:{height}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
            )
            final_v_stream = "[base]"
        else:
            # Works safely for 16:9, 4:3, and already-vertical inputs without invalid crop widths
            filter_complex = (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1[base]"
            )
            final_v_stream = "[base]"

        if ass_subtitles_path and os.path.exists(ass_subtitles_path):
            escaped_ass = (
                ass_subtitles_path.replace("\\", "/")
                .replace(":", "\\:")
                .replace("'", "\\'")
            )
            filter_complex += f";{final_v_stream}subtitles='{escaped_ass}'[v_out]"
            final_map = "[v_out]"
        else:
            final_map = final_v_stream

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_video_path,
            "-filter_complex", filter_complex,
            "-map", final_map,
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_video_path,
        ]

        logger.info(f"Rendering vertical reel: {output_video_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg rendering failed: {result.stderr}")
            raise RuntimeError(f"FFmpeg render failure: {result.stderr.strip()[-300:]}")

        return output_video_path

    @classmethod
    def generate_thumbnail(cls, video_path: str, thumbnail_path: str, timestamp_sec: float = 1.0) -> Optional[str]:
        """Extracts a frame from the rendered clip to serve as cover thumbnail."""
        os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
        for ts in (timestamp_sec, 0.0):
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "3",
                thumbnail_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(thumbnail_path):
                return thumbnail_path
        logger.warning(f"Could not generate thumbnail for {video_path}")
        return None
