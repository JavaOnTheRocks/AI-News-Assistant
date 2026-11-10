
import logging

from livekit import agents
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    room_io,
)
from livekit.plugins import gnani, openai

from voice_agent.config import get_settings
from voice_agent.core.agent import VoiceAssistant
from voice_agent.observability.latency import LatencyMonitor


# --------------------------------------------------
# 1. LOGGING
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("voiceagent")


# --------------------------------------------------
# 2. CONFIGURATION
# --------------------------------------------------

settings = get_settings()

logger.info("Configuration loaded.")
logger.info("Agent: %s", settings.agent_name)
logger.info("LLM model: %s", settings.openai_model)
logger.info("STT locale: %s", settings.stt_language)
logger.info("STT format: %s", settings.stt_format)
logger.info("Sample rate: %s", settings.sample_rate)


# --------------------------------------------------
# 3. LIVEKIT SERVER
# --------------------------------------------------

server = AgentServer()


# --------------------------------------------------
# 4. SESSION ENTRYPOINT
# --------------------------------------------------

@server.rtc_session()
async def voice_agent_entrypoint(ctx: JobContext):

    logger.info("Starting VoiceAgent session.")

    await ctx.connect()

    # --------------------------------------------------
    # 5. GNANI STT
    # --------------------------------------------------

    stt = gnani.STT(
        language=settings.stt_language,
        format=settings.stt_format,
        sample_rate=settings.sample_rate,
        use_streaming=True,
        api_key=settings.gnani_api_key,
    )

    logger.info("STT initialized.")
    logger.info("Runtime STT format: %r", stt._opts.format)
    logger.info("Runtime STT language: %r", stt._opts.language)

    # --------------------------------------------------
    # 6. OPENAI LLM
    # --------------------------------------------------

    llm = openai.responses.LLM(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    )

    # --------------------------------------------------
    # 7. GNANI TTS
    # --------------------------------------------------

    tts = gnani.TTS(
        voice=settings.tts_voice,
        model=settings.tts_model,
        language=settings.tts_language,
        synthesize_method=settings.tts_synthesize_method,
        sample_rate=settings.sample_rate,
        api_key=settings.gnani_api_key,
    )

    logger.info("TTS initialized.")

    # --------------------------------------------------
    # 8. AGENT SESSION
    # --------------------------------------------------

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        transcription_timeout=8.0,
    )

    # --------------------------------------------------
    # 9. LATENCY MONITOR
    # --------------------------------------------------

    latency_monitor = LatencyMonitor()
    latency_monitor.attach(session)

    ctx.add_shutdown_callback(
        latency_monitor.print_summary
    )

    # --------------------------------------------------
    # 10. START SESSION
    # --------------------------------------------------

    assistant = VoiceAssistant(settings)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                sample_rate=settings.sample_rate,
            ),
            audio_output=room_io.AudioOutputOptions(
                sample_rate=48000,
            ),
        ),
    )

    logger.info("VoiceAgent session started successfully.")

    # --------------------------------------------------
    # 11. GREETING
    # --------------------------------------------------

    await session.generate_reply(
        instructions=(
            "Introduce yourself as an AI News Anchor. "
            "Tell the user they can ask about the latest "
            "AI, technology, business, science, startups, "
            "finance, Indian current affairs and world news. "
            "Invite the user to speak in English, Hindi or "
            "Hinglish. Keep the greeting natural and concise."
        )
    )


# --------------------------------------------------
# 12. RUN
# --------------------------------------------------

if __name__ == "__main__":
    agents.cli.run_app(server)
