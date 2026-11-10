
from datetime import datetime, timezone, timedelta
import logging

from livekit.agents import function_tool, RunContext

logger = logging.getLogger("voiceagent.datetime")

# India Standard Time is UTC+05:30 and does not observe DST.
IST = timezone(timedelta(hours=5, minutes=30), name="IST")


@function_tool()
async def get_current_datetime(context: RunContext) -> dict:
    """
    Get the actual current date and time in India.

    Use this whenever the user asks for today's date,
    current time, weekday, current year, or date-related questions.
    """

    try:
        now = datetime.now(IST)

        result = {
            "date": now.strftime("%A, %d %B %Y"),
            "time": now.strftime("%I:%M:%S %p"),
            "weekday": now.strftime("%A"),
            "year": now.year,
            "timezone": "Asia/Kolkata",
            "utc_offset": "+05:30",
            "iso_datetime": now.isoformat(),
        }

        logger.info(
            "Datetime tool executed successfully: %s",
            result["iso_datetime"],
        )

        return result

    except Exception as exc:
        logger.exception("Datetime tool failed")

        return {
            "error": True,
            "message": str(exc),
        }
