
import logging
import time
import statistics
from collections import defaultdict

logger = logging.getLogger("voiceagent.latency")


class LatencyMonitor:
    """
    Terminal-friendly voice-agent latency monitoring.

    Tracks:
    - Final transcription events
    - Transcript-to-speaking-state latency (proxy)
    - LiveKit turn metrics
    - LLM TTFT / TTFS / TPS
    - TTS TTFB
    - E2E latency when provided by LiveKit
    - Running averages and p95 statistics

    Important:
    LiveKit's e2e_latency is reported as supplied by the SDK.
    It is not assumed to equal first-audible-audio latency.
    """

    METRIC_UNITS = {
        "llm_node_ttft": "s",
        "llm_node_ttfs": "s",
        "tts_node_ttfb": "s",
        "e2e_latency": "s",
        "playback_latency": "s",
        "llm_node_tps": "tokens/s",
    }

    def __init__(self, print_every_turn: bool = True):

        self.print_every_turn = print_every_turn

        self.turn_count = 0
        self.transcript_count = 0
        self.error_count = 0

        self.last_final_transcript_at = None

        self.metrics = defaultdict(list)

        self.started_at = time.perf_counter()

    # --------------------------------------------------
    # FORMAT HELPERS
    # --------------------------------------------------

    @staticmethod
    def format_time(value):

        if value is None:
            return "N/A"

        return f"{value * 1000:.2f} ms"

    @staticmethod
    def percentile(values, percentile=95):

        if not values:
            return None

        ordered = sorted(values)

        index = round(
            (len(ordered) - 1) * percentile / 100
        )

        return ordered[index]

    def add_metric(self, name, value):

        if value is None:
            return

        try:
            value = float(value)
        except (TypeError, ValueError):
            return

        if value < 0:
            return

        self.metrics[name].append(value)

    # --------------------------------------------------
    # TERMINAL DISPLAY
    # --------------------------------------------------

    @staticmethod
    def print_header():

        print("\n" + "=" * 65)
        print("             VOICEAGENT AI | LATENCY MONITOR")
        print("=" * 65)

    def print_event(self, title, message):

        print(f"\n[{title}] {message}")

    def print_turn_metrics(self, metrics):

        self.turn_count += 1

        print("\n" + "-" * 65)
        print(f" TURN {self.turn_count} | PERFORMANCE REPORT")
        print("-" * 65)

        metric_labels = {
            "llm_node_ttft": "LLM First Token (TTFT)",
            "llm_node_ttfs": "LLM First Speech (TTFS)",
            "llm_node_tps": "LLM Generation Speed",
            "tts_node_ttfb": "TTS First Byte (TTFB)",
            "playback_latency": "Playback Latency",
            "e2e_latency": "End-to-End Latency",
        }

        for key, label in metric_labels.items():

            value = getattr(metrics, key, None)

            if value is None and isinstance(metrics, dict):
                value = metrics.get(key)

            if value is None:
                continue

            self.add_metric(key, value)

            if key == "llm_node_tps":

                formatted = f"{float(value):.2f} tokens/sec"

            else:

                formatted = self.format_time(float(value))

            print(f" {label:<30}: {formatted}")

        self.print_event(
            "STATUS",
            "Turn metrics recorded successfully"
        )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    def print_summary(self):

        print("\n\n" + "=" * 65)
        print("              VOICEAGENT AI | SESSION SUMMARY")
        print("=" * 65)

        duration = time.perf_counter() - self.started_at

        print(f" Session Duration       : {duration:.2f} seconds")
        print(f" Final Transcriptions   : {self.transcript_count}")
        print(f" Completed Turns        : {self.turn_count}")
        print(f" Pipeline Errors        : {self.error_count}")

        print("\n LATENCY STATISTICS")
        print("-" * 65)

        summary_keys = [
            "llm_node_ttft",
            "llm_node_ttfs",
            "tts_node_ttfb",
            "e2e_latency",
        ]

        for key in summary_keys:

            values = self.metrics.get(key, [])

            if not values:
                continue

            average = statistics.mean(values)
            minimum = min(values)
            maximum = max(values)
            p95 = self.percentile(values, 95)

            label = key.replace("_", " ").upper()

            print(f"\n {label}")
            print(f"   Average : {self.format_time(average)}")
            print(f"   Minimum : {self.format_time(minimum)}")
            print(f"   Maximum : {self.format_time(maximum)}")
            print(f"   P95     : {self.format_time(p95)}")

        print("\n" + "=" * 65)
        print("             END OF LATENCY REPORT")
        print("=" * 65 + "\n")

    # --------------------------------------------------
    # LIVEKIT EVENT REGISTRATION
    # --------------------------------------------------

    def attach(self, session):

        self.print_header()

        self.print_event(
            "MONITOR",
            "Latency monitoring started"
        )

        # ----------------------------------------------
        # FINAL USER TRANSCRIPTION
        # ----------------------------------------------

        @session.on("user_input_transcribed")
        def on_user_input_transcribed(event):

            if not event.is_final:
                return

            self.transcript_count += 1

            self.last_final_transcript_at = time.perf_counter()

            self.print_event(
                "USER INPUT",
                f"Final transcription received | "
                f"Language: {event.language or 'Unknown'}"
            )

            # Do not print complete user transcripts by default.
            # This avoids exposing private conversations in logs.

        # ----------------------------------------------
        # AGENT SPEAKING STATE
        # ----------------------------------------------

        @session.on("agent_state_changed")
        def on_agent_state_changed(event):

            state = getattr(
                event.new_state,
                "value",
                str(event.new_state),
            ).lower()

            if "speaking" not in state:
                return

            if self.last_final_transcript_at is None:
                return

            elapsed = (
                time.perf_counter()
                - self.last_final_transcript_at
            )

            self.add_metric(
                "transcript_to_speaking_state",
                elapsed
            )

            self.print_event(
                "VOICE RESPONSE",
                "Transcript-to-speaking-state: "
                f"{self.format_time(elapsed)}"
            )

            self.last_final_transcript_at = None

        # ----------------------------------------------
        # LIVEKIT TURN METRICS
        # ----------------------------------------------

        @session.on("conversation_item_added")
        def on_conversation_item_added(event):

            item = event.item

            metrics = getattr(
                item,
                "metrics",
                None
            )

            if metrics is None:
                return

            self.print_turn_metrics(metrics)

        # ----------------------------------------------
        # PIPELINE ERRORS
        # ----------------------------------------------

        @session.on("error")
        def on_error(event):

            self.error_count += 1

            error = getattr(
                event,
                "error",
                event
            )

            source = getattr(
                event,
                "source",
                "unknown"
            )

            self.print_event(
                "ERROR",
                f"Source: {source} | Error: {error}"
            )

            logger.error(
                "Voice pipeline error | source=%s | error=%s",
                source,
                error,
            )
