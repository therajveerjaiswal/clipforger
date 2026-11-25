import os
import sys
import tempfile
import types
import unittest

ROOT_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_BACKEND not in sys.path:
    sys.path.insert(0, ROOT_BACKEND)


def _install_stubs():
    """Stub optional heavy third-party packages if not installed in the local test environment."""
    optional_modules = [
        "numpy",
        "faster_whisper",
        "google",
        "google.generativeai",
        "boto3",
        "botocore",
        "botocore.config",
        "supabase",
        "razorpay",
        "celery",
        "fastapi",
        "fastapi.security",
        "fastapi.middleware",
        "fastapi.middleware.cors",
        "fastapi.responses",
        "pydantic",
        "pydantic_settings",
    ]
    for name in optional_modules:
        if name in sys.modules:
            continue
        try:
            __import__(name)
        except ImportError:
            mod = types.ModuleType(name)
            if name == "fastapi":
                class HTTPException(Exception):
                    def __init__(self, status_code=400, detail=""):
                        self.status_code = status_code
                        self.detail = detail
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
                    HTTP_429_TOO_MANY_REQUESTS=429,
                    HTTP_500_INTERNAL_SERVER_ERROR=500,
                    HTTP_503_SERVICE_UNAVAILABLE=503,
                )
            elif name == "fastapi.security":
                mod.HTTPBearer = lambda *a, **kw: None
                mod.HTTPAuthorizationCredentials = object
            elif name == "pydantic":
                class BaseModel:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                    def model_dump(self):
                        return dict(self.__dict__)
                mod.BaseModel = BaseModel
                mod.Field = lambda default=None, **kw: default
                mod.field_validator = lambda *a, **kw: (lambda fn: fn)
                mod.model_validator = lambda *a, **kw: (lambda fn: fn)
            elif name == "pydantic_settings":
                class BaseSettings:
                    def __init__(self, **kwargs):
                        for cls in reversed(self.__class__.__mro__):
                            for k, v in getattr(cls, "__dict__", {}).items():
                                if k.isupper() and not k.startswith("_"):
                                    setattr(self, k, kwargs.get(k, v))
                mod.BaseSettings = BaseSettings
                mod.SettingsConfigDict = lambda **kw: {}
            elif name == "supabase":
                mod.create_client = lambda **kw: types.SimpleNamespace()
                mod.Client = object
            elif name == "botocore.config":
                mod.Config = lambda **kw: None
            elif name == "celery":
                class Celery:
                    def __init__(self, *a, **kw):
                        self.conf = types.SimpleNamespace(update=lambda **u: None)
                    def task(self, *a, **kw):
                        def wrap(fn):
                            fn.delay = lambda **k: None
                            fn.apply = lambda **k: None
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

    def test_r2_storage_lazy_init_without_credentials(self):
        from app.services.r2_storage import R2StorageService

        svc = R2StorageService()
        self.assertFalse(svc.is_r2_configured)
        self.assertIsNone(svc._s3_client)

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


if __name__ == "__main__":
    unittest.main()
