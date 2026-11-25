import os
import subprocess
import logging
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class AudioSpikeDetector:
    """
    Detects high-energy gaming highlights, screaming, hype moments, and teamfights
    from long stream audio using chunked RMS energy analysis.
    Memory-efficient: streams audio data in blocks to prevent OOM on 20-30h streams.
    """

    @staticmethod
    def detect_high_action_moments(
        audio_file_path: str,
        total_duration: float,
        target_clips: int = 5,
        min_clip_duration: float = 15.0,
        max_clip_duration: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """
        Scans audio file in 1-second time bins via FFmpeg PCM stream to compute RMS decibels.
        Returns candidate highlight intervals [start, end, duration, score].
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        logger.info(f"Analyzing audio energy spikes for file: {audio_file_path}")

        # Sample PCM 8kHz 16-bit mono -> 1 sec = 8000 samples = 16000 bytes
        sample_rate = 8000
        bytes_per_sample = 2
        block_size_bytes = sample_rate * bytes_per_sample

        cmd = [
            "ffmpeg",
            "-i", audio_file_path,
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-f", "s16le",
            "-",
        ]

        rms_values: List[float] = []
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            assert proc.stdout is not None
            while True:
                raw_bytes = proc.stdout.read(block_size_bytes)
                if not raw_bytes or len(raw_bytes) < block_size_bytes:
                    break
                samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples ** 2)) + 1e-6)
                rms_values.append(rms)
        except Exception as e:
            logger.error(f"Error during audio stream analysis: {e}")
            raise
        finally:
            if proc is not None:
                if proc.stdout:
                    proc.stdout.close()
                proc.wait()

        effective_duration = float(total_duration) if total_duration and total_duration > 0 else float(len(rms_values))
        if effective_duration <= 0:
            effective_duration = max_clip_duration

        if not rms_values:
            logger.warning("No audio samples extracted. Falling back to default distribution.")
            step = effective_duration / (target_clips + 1)
            fallback_clips = []
            for i in range(1, target_clips + 1):
                start = round(max(0.0, min(effective_duration - min_clip_duration, i * step)), 1)
                dur = round(min(min_clip_duration, max(2.0, effective_duration - start)), 1)
                fallback_clips.append(
                    {
                        "start": start,
                        "end": round(start + dur, 1),
                        "duration": dur,
                        "score": 50.0,
                    }
                )
            return fallback_clips

        rms_array = np.array(rms_values, dtype=np.float32)
        max_rms = float(np.max(rms_array)) or 1.0
        db_array = 20.0 * np.log10(rms_array / max_rms + 1e-6)

        baseline = float(np.median(db_array))
        window_size = int(min_clip_duration)
        if len(db_array) < window_size:
            dur = round(min(effective_duration, max_clip_duration), 1)
            return [
                {
                    "start": 0.0,
                    "end": dur,
                    "duration": dur,
                    "score": 85.0,
                }
            ]

        kernel = np.ones(window_size) / window_size
        smoothed_energy = np.convolve(db_array, kernel, mode="valid")

        selected_candidates: List[Dict[str, Any]] = []
        # Adapt minimum distance between clips for shorter videos while keeping 180s for long streams
        min_distance_seconds = 180.0 if effective_duration > (target_clips * 200) else max(25.0, effective_duration / max(1, target_clips + 1))

        sorted_indices = np.argsort(smoothed_energy)[::-1]

        for idx in sorted_indices:
            peak_start = float(idx)
            if peak_start + max_clip_duration > effective_duration:
                peak_start = max(0.0, effective_duration - max_clip_duration)

            overlaps = any(
                abs(cand["start"] - peak_start) < min_distance_seconds
                for cand in selected_candidates
            )

            if not overlaps:
                raw_score = float(smoothed_energy[idx])
                normalized_score = min(99.0, max(60.0, 75.0 + (raw_score - baseline) * 2.0))

                clip_dur = 22.0
                if peak_start + clip_dur > effective_duration:
                    clip_dur = max(2.0, effective_duration - peak_start)

                selected_candidates.append(
                    {
                        "start": round(peak_start, 1),
                        "end": round(peak_start + clip_dur, 1),
                        "duration": round(clip_dur, 1),
                        "score": round(normalized_score, 1),
                    }
                )

                if len(selected_candidates) >= target_clips:
                    break

        selected_candidates.sort(key=lambda x: x["start"])
        return selected_candidates
