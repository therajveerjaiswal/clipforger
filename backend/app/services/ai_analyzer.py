import json
import re
import logging
from typing import Dict, Any, Optional
from faster_whisper import WhisperModel
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    Transcribes audio segments with word-level timestamps using Faster-Whisper,
    and analyzes viral hooks/titles using Gemini Flash API.
    """

    _whisper_instance: Optional[WhisperModel] = None

    @classmethod
    def get_whisper(cls) -> WhisperModel:
        if cls._whisper_instance is None:
            logger.info(
                f"Loading faster-whisper model: {settings.WHISPER_MODEL_SIZE} "
                f"on {settings.WHISPER_DEVICE} ({settings.WHISPER_COMPUTE_TYPE})"
            )
            cls._whisper_instance = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
        return cls._whisper_instance

    @staticmethod
    def transcribe_segment(audio_segment_path: str) -> Dict[str, Any]:
        """
        Transcribes the exact 15-30s slice, returning word-level timestamps
        for ASS karaoke subtitle generation.
        """
        whisper = AIAnalyzer.get_whisper()
        segments, info = whisper.transcribe(
            audio_segment_path,
            beam_size=5,
            word_timestamps=True,
            language=None,  # auto-detect language
        )

        full_text = []
        words_data = []

        for segment in segments:
            full_text.append(segment.text.strip())
            if segment.words:
                for word in segment.words:
                    clean_word = word.word.strip()
                    if clean_word:
                        words_data.append(
                            {
                                "word": clean_word,
                                "start": round(word.start, 2),
                                "end": round(word.end, 2),
                                "probability": round(word.probability, 2),
                            }
                        )

        joined_text = " ".join(full_text).strip()
        return {
            "text": joined_text if joined_text else "High Action Gaming Gameplay",
            "language": info.language,
            "words": words_data,
        }

    @staticmethod
    def _extract_json_object(raw_text: str) -> Dict[str, Any]:
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            clean = match.group(0)
        return json.loads(clean)

    @staticmethod
    def generate_hook_and_caption(transcript: str, game_title: str = "Gaming Stream") -> Dict[str, Any]:
        """
        Uses Gemini Flash to formulate a viral social media hook and title for TikTok/Reels/Shorts.
        """
        if not settings.GEMINI_API_KEY:
            return {
                "title": f"INSANE MOMENT IN {game_title[:24].upper()}! 🔥",
                "hook": "Wait until the very end...",
                "viral_score": 88.0,
            }

        genai.configure(api_key=settings.GEMINI_API_KEY)
        prompt = f"""
        You are a top gaming social media editor who creates viral TikToks and YouTube Shorts with millions of views.
        Context: Gaming stream highlight clip.
        Game / Stream context: {game_title}
        Clip Dialogue: "{transcript}"

        Generate a short, viral JSON response:
        1. "title": Catchy all-caps title (max 6 words, with 1-2 emojis).
        2. "hook": A 1-sentence curiosity hook to show on screen in the first 3 seconds.
        3. "viral_score": A number between 70.0 and 99.0 reflecting the excitement level.

        Return ONLY valid JSON in format:
        {{"title": "...", "hook": "...", "viral_score": 92.5}}
        """

        for model_name in ("gemini-2.0-flash", "gemini-1.5-flash"):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                data = AIAnalyzer._extract_json_object(response.text or "")
                return {
                    "title": str(data.get("title", "UNBELIEVABLE PLAY! 🎮")),
                    "hook": str(data.get("hook", "You won't believe what happened!")),
                    "viral_score": float(data.get("viral_score", 85.0)),
                }
            except Exception as e:
                logger.warning(f"Gemini model '{model_name}' failed: {e}")

        return {
            "title": "UNREAL GAMING MOMENT! 🚀",
            "hook": "Wait for this reaction...",
            "viral_score": 84.0,
        }
