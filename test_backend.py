import os
import sys
import tempfile
import types
import unittest

ROOT_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_BACKEND not in sys.path:
    sys.path.insert(0, ROOT_BACKEND)


def _install_stubs():
    """Stub optional heavy third-party packages if not installed (or incompatible major version) locally."""
    optional_modules = [
        "pydantic",
        "pydantic_settings",
        "numpy",
        "faster_whisper",
        "supabase",
        "razorpay",
        "celery",
        "celery.exceptions",
        "httpx",
        "fastapi",
        "fastapi.concurrency",
        "fastapi.security",
        "fastapi.middleware",
        "fastapi.middleware.cors",
        "fastapi.responses",
    ]
    pydantic_stubbed = False
    for name in optional_modules:
        if name in sys.modules:
            if name == "pydantic" and not hasattr(sys.modules[name], "field_validator"):
                pass
            elif pydantic_stubbed and name.startswith("fastapi"):
                pass
            else:
                continue
        try:
            if pydantic_stubbed and name.startswith("fastapi"):
                raise ImportError("stub fastapi alongside stubbed pydantic")
            imported = __import__(name)
            if name == "pydantic" and not hasattr(imported, "field_validator"):
                raise ImportError("pydantic v2 required")
            if name == "supabase" and not hasattr(imported, "create_client"):
                raise ImportError("supabase namespace folder shadowed SDK")
            continue
        except ImportError:
            if name == "pydantic":
                pydantic_stubbed = True
            mod = types.ModuleType(name)
            if name == "fastapi":
                class HTTPException(Exception):
                    def __init__(self, status_code=400, detail="", headers=None):
                        self.status_code = status_code
                        self.detail = detail
                        self.headers = headers
                        super().__init__(detail)
                class APIRouter:
                    def __getattr__(self, _):
                        return lambda *a, **kw: (lambda fn: fn)
                mod.HTTPException = HTTPException
                mod.APIRouter = APIRouter
                mod.BackgroundTasks = object
                mod.Depends = lambda x=None: x
                mod.Request = object
                mod.Security = lambda x=None: x
                mod.Query = lambda *a, **kw: None
                mod.Header = lambda *a, **kw: None
                mod.status = types.SimpleNamespace(
                    HTTP_201_CREATED=201,
                    HTTP_400_BAD_REQUEST=400,
                    HTTP_401_UNAUTHORIZED=401,
                    HTTP_403_FORBIDDEN=403,
                    HTTP_404_NOT_FOUND=404,
                    HTTP_409_CONFLICT=409,
                    HTTP_429_TOO_MANY_REQUESTS=429,
                    HTTP_500_INTERNAL_SERVER_ERROR=500,
                    HTTP_502_BAD_GATEWAY=502,
                    HTTP_503_SERVICE_UNAVAILABLE=503,
                )
            elif name == "fastapi.security":
                mod.HTTPBearer = lambda *a, **kw: None
                mod.HTTPAuthorizationCredentials = object
            elif name == "pydantic":
                import re as _re

                class ValidationError(ValueError):
                    pass

                class _FieldSpec:
                    def __init__(self, default=None, pattern=None, ge=None, le=None, **kw):
                        self.default = default
                        self.pattern = pattern
                        self.ge = ge
                        self.le = le

                class BaseModel:
                    def __init__(self, **kwargs):
                        for cls in reversed(self.__class__.__mro__):
                            for k, v in getattr(cls, "__dict__", {}).items():
                                if k.startswith("_") or callable(v):
                                    continue
                                if isinstance(v, _FieldSpec):
                                    val = kwargs.get(k, v.default)
                                    if v.pattern is not None and (not isinstance(val, str) or not _re.match(v.pattern, val)):
                                        raise ValidationError(f"{k} failed pattern {v.pattern}")
                                    if v.ge is not None and val < v.ge:
                                        raise ValidationError(f"{k} < {v.ge}")
                                    if v.le is not None and val > v.le:
                                        raise ValidationError(f"{k} > {v.le}")
                                    setattr(self, k, val)
                                else:
                                    setattr(self, k, kwargs.get(k, v))
                        for k, v in kwargs.items():
                            if not hasattr(self, k):
                                setattr(self, k, v)

                    def model_dump(self):
                        return dict(self.__dict__)

                mod.BaseModel = BaseModel
                mod.ValidationError = ValidationError
                mod.Field = lambda default=None, **kw: _FieldSpec(default=default, **kw)
                mod.field_validator = lambda *a, **kw: (lambda fn: fn)
                mod.model_validator = lambda *a, **kw: (lambda fn: fn)
            elif name == "pydantic_settings":
                class BaseSettings:
                    def __init__(self, **kwargs):
                        for cls in reversed(self.__class__.__mro__):
                            for k, v in getattr(cls, "__dict__", {}).items():
                                if k.isupper() and not k.startswith("_"):
                                    setattr(self, k, kwargs.get(k, v))
                        if hasattr(self, "sync_redis_urls"):
                            self.sync_redis_urls()
                mod.BaseSettings = BaseSettings
                mod.SettingsConfigDict = lambda **kw: {}
            elif name == "supabase":
                mod.create_client = lambda **kw: types.SimpleNamespace()
                mod.Client = object
            elif name == "celery.exceptions":
                class SoftTimeLimitExceeded(Exception):
                    pass
                mod.SoftTimeLimitExceeded = SoftTimeLimitExceeded
            elif name == "fastapi.concurrency":
                mod.run_in_threadpool = lambda fn, *a, **kw: fn(*a, **kw)
            elif name == "celery":
                class Celery:
                    def __init__(self, *a, **kw):
                        self.conf = types.SimpleNamespace(update=lambda **u: None)
                    def task(self, *a, **kw):
                        def wrap(fn):
                            fn.delay = lambda **k: None
                            fn.apply = lambda **k: None
                            fn.run = lambda **k: fn(None, **k)
                            return fn
                        return wrap
                mod.Celery = Celery
            elif name == "faster_whisper":
                mod.WhisperModel = object
            elif name == "razorpay":
                mod.Client = lambda **kw: None
            sys.modules[name] = mod


_install_stubs()


class ClipForgeBackendTests(unittest.TestCase):
    def test_video_editor_ass_formatting(self):
        from app.services.video_editor import VideoEditor

        self.assertEqual(VideoEditor.hex_to_ass_color("#FFFFFF"), "&H00FFFFFF")
        self.assertEqual(VideoEditor.hex_to_ass_color("#FFD700"), "&H0000D7FF")
        self.assertEqual(VideoEditor.hex_to_ass_color("&H00112233"), "&H00112233")
        self.assertEqual(VideoEditor.format_ass_timestamp(0), "0:00:00.00")
        self.assertEqual(VideoEditor.format_ass_timestamp(65.5), "0:01:05.50")
        self.assertEqual(VideoEditor._escape_ass_text("hello {world}\n"), "hello (world)")

        with tempfile.TemporaryDirectory() as td:
            ass_path = os.path.join(td, "sub.ass")
            VideoEditor.generate_ass_subtitles(
                [{"word": "clutch", "start": 0.2, "end": 0.9}],
                ass_path,
                style_config={"primary_color": "#FFFFFF", "highlight_color": "#FFD700"},
                hook_headline="CRAZY {PLAY}!",
            )
            with open(ass_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("&H0000D7FF,&H00FFFFFF", content)
            self.assertIn("CRAZY (PLAY)!", content)

    def test_supabase_storage_upload_and_delete(self):
        import app.services.supabase_storage as storage_mod
        from app.services.supabase_storage import SupabaseStorageService

        uploaded = {}
        removed = []

        class FakeBucket:
            def upload(self, path, file, file_options):
                uploaded["path"] = path
                uploaded["bytes"] = file
                uploaded["options"] = file_options

            def get_public_url(self, path):
                return f"https://demo.supabase.co/storage/v1/object/public/clips/{path}?"

            def remove(self, keys):
                removed.extend(keys)

        class FakeStorage:
            def create_bucket(self, bucket, options=None):
                return {"name": bucket}

            def from_(self, bucket):
                return FakeBucket()

        fake_client = types.SimpleNamespace(storage=FakeStorage())
        orig_get_admin = storage_mod.get_supabase_admin
        storage_mod.get_supabase_admin = lambda: fake_client
        try:
            svc = SupabaseStorageService()
            with tempfile.TemporaryDirectory() as td:
                sample_path = os.path.join(td, "clip.mp4")
                with open(sample_path, "wb") as f:
                    f.write(b"fake-mp4-data")
                url = svc.upload_file(sample_path, "clips/u1/c1.mp4", "video/mp4")
            self.assertEqual(url, "https://demo.supabase.co/storage/v1/object/public/clips/clips/u1/c1.mp4")
            self.assertEqual(uploaded["bytes"], b"fake-mp4-data")
            self.assertEqual(uploaded["options"]["content-type"], "video/mp4")
            self.assertTrue(svc.delete_file("clips/u1/c1.mp4"))
            self.assertEqual(removed, ["clips/u1/c1.mp4"])
        finally:
            storage_mod.get_supabase_admin = orig_get_admin

    def test_upstash_rediss_url_adds_ssl_cert_reqs(self):
        from app.core.config import _ensure_rediss_ssl_param

        raw = "rediss://default:secret@example-12345.upstash.io:6379"
        fixed = _ensure_rediss_ssl_param(raw, "required")
        self.assertIn("ssl_cert_reqs=CERT_REQUIRED", fixed)
        # Idempotent if already present
        self.assertEqual(_ensure_rediss_ssl_param(fixed, "required"), fixed)
        # Non-TLS redis:// URLs are untouched
        plain = "redis://localhost:6379/0"
        self.assertEqual(_ensure_rediss_ssl_param(plain, "required"), plain)

    def test_youtube_id_extraction(self):
        from app.api.v1.endpoints.jobs import extract_youtube_id
        from fastapi import HTTPException

        self.assertEqual(extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(
            extract_youtube_id("https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(extract_youtube_id("https://youtu.be/dQw4w9WgXcQ?t=12"), "dQw4w9WgXcQ")
        self.assertEqual(extract_youtube_id("https://www.youtube.com/live/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_youtube_id("https://youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        with self.assertRaises(HTTPException):
            extract_youtube_id("https://example.com/notyoutube")

    def test_client_ip_validation(self):
        from app.core.security import _valid_ip

        self.assertEqual(_valid_ip("203.0.113.5, 10.0.0.1"), "203.0.113.5")
        self.assertEqual(_valid_ip("2001:db8::1"), "2001:db8::1")
        self.assertIsNone(_valid_ip("invalid-ip"))
        self.assertIsNone(_valid_ip(""))

    def test_razorpay_signature_verification(self):
        import hmac
        import hashlib
        from app.services.razorpay_service import RazorpayService

        svc = RazorpayService()
        svc.key_secret = "test_secret_123"
        svc.webhook_secret = "wh_secret_456"

        sig = hmac.new(b"test_secret_123", b"pay_1|sub_1", hashlib.sha256).hexdigest()
        self.assertTrue(svc.verify_payment_signature("pay_1", "sub_1", sig))
        self.assertFalse(svc.verify_payment_signature("pay_1", "sub_1", "bad_sig"))

        body = b'{"event":"subscription.charged"}'
        wh_sig = hmac.new(b"wh_secret_456", body, hashlib.sha256).hexdigest()
        self.assertTrue(svc.verify_webhook_signature(body, wh_sig))
        self.assertFalse(svc.verify_webhook_signature(body, "wrong"))

    def test_ai_analyzer_json_extraction(self):
        from app.services.ai_analyzer import AIAnalyzer

        parsed = AIAnalyzer._extract_json_object('Sure!\n```json\n{"title": "CLUTCH!", "hook": "Wait", "viral_score": 95}\n```')
        self.assertEqual(parsed["title"], "CLUTCH!")
        self.assertEqual(parsed["viral_score"], 95)

    def test_youtube_lookalike_hosts_are_rejected(self):
        from app.api.v1.endpoints.jobs import extract_youtube_id, canonical_youtube_url
        from fastapi import HTTPException

        for bad in (
            "https://evilyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.evil.io/watch?v=dQw4w9WgXcQ",
            "https://notyoutu.be/dQw4w9WgXcQ",
            "http://[invalid/watch?v=dQw4w9WgXcQ",
            "",
        ):
            with self.assertRaises(HTTPException, msg=bad):
                extract_youtube_id(bad)

        self.assertEqual(extract_youtube_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_youtube_id("youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(
            canonical_youtube_url("dQw4w9WgXcQ"), "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

    def test_forwarded_headers_only_trusted_from_proxies(self):
        from types import SimpleNamespace
        from app.core.security import get_client_ip

        def req(peer, **headers):
            return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)

        # A direct (untrusted) client cannot spoof its IP.
        self.assertEqual(get_client_ip(req("203.0.113.9", **{"X-Forwarded-For": "1.2.3.4"})), "203.0.113.9")
        self.assertEqual(get_client_ip(req("203.0.113.9", **{"CF-Connecting-IP": "1.2.3.4"})), "203.0.113.9")
        # Behind a trusted proxy the forwarded value is used.
        self.assertEqual(get_client_ip(req("10.1.2.3", **{"CF-Connecting-IP": "198.51.100.7"})), "198.51.100.7")
        # Client-supplied left-most XFF entries are ignored: take the right-most untrusted hop.
        self.assertEqual(
            get_client_ip(req("10.1.2.3", **{"X-Forwarded-For": "6.6.6.6, 198.51.100.7, 10.0.0.9"})),
            "198.51.100.7",
        )
        self.assertEqual(get_client_ip(req("10.1.2.3")), "10.1.2.3")

    def test_device_fingerprint_is_bounded(self):
        from types import SimpleNamespace
        from app.core.security import get_device_fingerprint

        request = SimpleNamespace(
            client=SimpleNamespace(host="203.0.113.9"),
            headers={"X-Device-Fingerprint": "a" * 500},
        )
        self.assertEqual(len(get_device_fingerprint(request)), 128)

    def test_ai_score_is_clamped(self):
        from app.services.ai_analyzer import AIAnalyzer

        self.assertEqual(AIAnalyzer._clamp_score(9500), 99.0)
        self.assertEqual(AIAnalyzer._clamp_score(-4), 0.0)
        self.assertEqual(AIAnalyzer._clamp_score("92.54"), 92.5)
        self.assertIsNone(AIAnalyzer._clamp_score("n/a"))
        self.assertIsNone(AIAnalyzer._clamp_score(float("nan")))

    def test_ai_fallback_does_not_fake_a_score(self):
        from app.services.ai_analyzer import AIAnalyzer
        from app.core.config import settings

        original = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = ""
        try:
            result = AIAnalyzer.generate_hook_and_caption("hello", "Valorant")
        finally:
            settings.GEMINI_API_KEY = original
        self.assertIsNone(result["viral_score"])
        self.assertTrue(result["title"] and result["hook"])

    def test_ai_gemini_model_fallback_chain(self):
        from app.services.ai_analyzer import AIAnalyzer
        from app.core.config import settings

        calls = []

        def fake_call(model, prompt):
            calls.append(model)
            if model == "dead-model":
                raise RuntimeError("404 model retired")
            return '{"title": "BIG PLAY", "hook": "Watch this", "viral_score": 1234}'

        orig_call, orig_key, orig_models = AIAnalyzer._call_gemini, settings.GEMINI_API_KEY, settings.GEMINI_MODELS
        AIAnalyzer._call_gemini = staticmethod(fake_call)
        settings.GEMINI_API_KEY = "key"
        settings.GEMINI_MODELS = "dead-model, live-model"
        try:
            result = AIAnalyzer.generate_hook_and_caption("clip text", "Game")
        finally:
            AIAnalyzer._call_gemini = orig_call
            settings.GEMINI_API_KEY = orig_key
            settings.GEMINI_MODELS = orig_models

        self.assertEqual(calls, ["dead-model", "live-model"])
        self.assertEqual(result["title"], "BIG PLAY")
        self.assertEqual(result["viral_score"], 99.0)

    def test_ass_caption_lines_never_overlap(self):
        from app.services.video_editor import VideoEditor

        words = [
            {"word": "one", "start": 0.0, "end": 0.2},
            {"word": "two", "start": 0.2, "end": 0.4},
            {"word": "three", "start": 0.4, "end": 0.6},
            {"word": "four", "start": 0.6, "end": 0.8},
            {"word": "five", "start": 0.9, "end": 1.0},
            {"word": "six", "start": 1.0, "end": 1.1},
        ]
        with tempfile.TemporaryDirectory() as td:
            ass_path = os.path.join(td, "sub.ass")
            VideoEditor.generate_ass_subtitles(words, ass_path)
            with open(ass_path, encoding="utf-8") as f:
                lines = [ln for ln in f if ln.startswith("Dialogue:") and ",KaraokeBody," in ln]

        def to_s(ts):
            h, m, sec = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)

        spans = [(to_s(ln.split(",")[1]), to_s(ln.split(",")[2])) for ln in lines]
        self.assertEqual(len(spans), 2)
        self.assertLessEqual(spans[0][1], spans[1][0])

    def test_subtitle_style_validation(self):
        from pydantic import ValidationError
        from app.models.schemas import SubtitleStyle

        SubtitleStyle()  # defaults are valid
        for bad in (
            {"primary_color": "red"},
            {"font_family": "Arial,0,0\nDialogue: x"},
            {"font_size": 9999},
            {"outline_width": -1},
        ):
            with self.assertRaises(ValidationError, msg=str(bad)):
                SubtitleStyle(**bad)

    def test_spike_detector_finds_loud_burst_within_bounds(self):
        import shutil
        import wave
        import numpy as np
        from app.services.spike_detector import AudioSpikeDetector

        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not installed")

        rate, seconds = 8000, 120
        rng = np.random.default_rng(0)
        audio = (rng.normal(0, 200, rate * seconds)).astype(np.int16)
        audio[60 * rate:80 * rate] = rng.normal(0, 12000, 20 * rate).clip(-32000, 32000).astype(np.int16)

        with tempfile.TemporaryDirectory() as td:
            wav_path = os.path.join(td, "audio.wav")
            with wave.open(wav_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(audio.tobytes())

            moments = AudioSpikeDetector.detect_high_action_moments(
                audio_file_path=wav_path, total_duration=float(seconds), target_clips=1
            )

        self.assertEqual(len(moments), 1)
        m = moments[0]
        self.assertGreaterEqual(m["start"], 0)
        self.assertLessEqual(m["end"], seconds + 1e-6)
        self.assertLess(m["start"], 80)   # clip overlaps the loud 60-80s burst
        self.assertGreater(m["end"], 60)


if __name__ == "__main__":
    unittest.main()
