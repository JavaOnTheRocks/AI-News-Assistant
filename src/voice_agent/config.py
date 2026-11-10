
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Load .env from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # OpenAI
    openai_api_key: str
    openai_model: str

    # Gnani
    gnani_api_key: str

    # STT
    stt_language: str
    stt_format: str
    sample_rate: int

    # TTS
    tts_model: str
    tts_voice: str
    tts_language: str
    tts_synthesize_method: str

    # Agent
    agent_name: str

    # Tavily
    tavily_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv(
                "OPENAI_MODEL", "gpt-4.1-mini"
            ),

            gnani_api_key=os.getenv("GNANI_API_KEY", ""),

            stt_language=os.getenv(
                "GNANI_STT_LANGUAGE", "en-IN"
            ),
            stt_format=os.getenv(
                "GNANI_STT_FORMAT", "verbatim"
            ),
            sample_rate=int(
                os.getenv("GNANI_SAMPLE_RATE", "16000")
            ),

            tts_model=os.getenv(
                "GNANI_TTS_MODEL", "timbre-v3.0"
            ),
            tts_voice=os.getenv(
                "GNANI_TTS_VOICE", "Avinash"
            ),
            tts_language=os.getenv(
                "GNANI_TTS_LANGUAGE", "auto"
            ),
            tts_synthesize_method=os.getenv(
                "GNANI_TTS_SYNTHESIZE_METHOD", "websocket"
            ),

            agent_name=os.getenv(
                "AGENT_NAME", "AI News Anchor"
            ),

            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        )

    def validate(self) -> None:
        missing = []

        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")

        if not self.gnani_api_key:
            missing.append("GNANI_API_KEY")

        if missing:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )

        if self.sample_rate not in (8000, 16000, 44100, 48000):
            raise ValueError(
                f"Unsupported sample rate: {self.sample_rate}"
            )

        if self.stt_language not in (
            "en-IN", "hi-IN", "bn-IN", "gu-IN",
            "kn-IN", "ml-IN", "mr-IN", "pa-IN",
            "ta-IN", "te-IN",
        ):
            raise ValueError(
                f"Unsupported configured STT locale: "
                f"{self.stt_language}"
            )

        if self.stt_format not in ("verbatim", "transcribe"):
            raise ValueError(
                "GNANI_STT_FORMAT must be 'verbatim' "
                "or 'transcribe' for this plugin configuration."
            )


def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.validate()
    return settings
