"""Unified HTTP notification service for dashboard updates."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles HTTP notifications to the dashboard backend."""

    def __init__(self, backend_url: str = "http://localhost:5000"):
        """Initialize notification service.

        Args:
            backend_url: Base URL for the backend API
        """
        self.backend_url = backend_url.rstrip("/")
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="notifier"
        )

    def _fire_and_forget_post(
        self, endpoint: str, payload: Dict[str, Any], timeout: float = 0.5
    ) -> None:
        """Send POST request in background thread.

        Args:
            endpoint: API endpoint path (without base URL)
            payload: JSON payload to send
            timeout: Request timeout in seconds
        """

        def _send():
            try:
                url = f"{self.backend_url}{endpoint}"
                response = requests.post(url, json=payload, timeout=timeout)
                if response.status_code != 200:
                    logger.debug(
                        f"Notification to {endpoint} failed: {response.status_code}"
                    )
            except requests.exceptions.Timeout:
                logger.debug(f"Notification to {endpoint} timed out")
            except requests.exceptions.ConnectionError:
                logger.debug(f"Notification to {endpoint} failed: connection error")
            except Exception as exc:
                logger.debug(f"Notification to {endpoint} failed: {exc}")

        self._executor.submit(_send)

    def notify_dashboard_update(self, user_id: str) -> None:
        """Notify backend that dashboard data should be updated (non-blocking).

        Args:
            user_id: User identifier
        """
        # Use fire-and-forget to avoid blocking the main thread
        self._fire_and_forget_post(f"/api/notify/{user_id}", {}, timeout=1.0)

    def push_user_input(self, user_id: str, text: str) -> None:
        """Push user input text to backend immediately.

        Args:
            user_id: User identifier
            text: User input text
        """
        payload = {"text": text, "timestamp": datetime.now().isoformat()}
        self._fire_and_forget_post(f"/api/user-input/{user_id}", payload)

    def push_streaming_chunk(self, user_id: str, chunk: str, is_final: bool) -> None:
        """Push streaming text chunk to backend for real-time updates.

        Args:
            user_id: User identifier
            chunk: Text chunk to push
            is_final: Whether this is the final chunk
        """
        payload = {"chunk": chunk, "is_final": is_final}
        self._fire_and_forget_post(f"/api/stream-chunk/{user_id}", payload)

    def push_audio_chunk(
        self,
        user_id: str,
        chunk_b64: str,
        sample_rate: int,
        is_final: bool,
        text_hash: Optional[str] = None,
        text_preview: Optional[str] = None,
    ) -> None:
        """Push streaming audio chunk to backend for real-time playback.

        Args:
            user_id: User identifier
            chunk_b64: Base64-encoded PCM chunk (s16le mono)
            sample_rate: Audio sample rate (Hz)
            is_final: Whether this is the final chunk
            text_hash: Optional short hash of the synthesized text (debugging aid)
            text_preview: Optional short preview of the synthesized text (debugging aid)
        """
        payload = {
            "chunk": chunk_b64,
            "sample_rate": sample_rate,
            "is_final": is_final,
        }
        if text_hash is not None:
            payload["text_hash"] = text_hash
        if text_preview is not None:
            payload["text_preview"] = text_preview
        try:
            url = f"{self.backend_url}/api/audio-chunk/{user_id}"
            response = requests.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.warning("Audio chunk push failed: %s", response.status_code)
        except requests.exceptions.Timeout:
            logger.warning("Audio chunk push timed out")
        except requests.exceptions.ConnectionError:
            logger.warning("Audio chunk push failed: connection error")
        except Exception as exc:
            logger.warning(f"Audio chunk push failed: {exc}")

    def push_status(self, user_id: str, status: str) -> None:
        """Push processing status to backend for real-time updates.

        Args:
            user_id: User identifier
            status: Status message (e.g., "recording", "transcribing", "generating", "idle")
        """
        payload = {"status": status}
        self._fire_and_forget_post(f"/api/status/{user_id}", payload)

    def shutdown(self) -> None:
        """Shutdown the notification service and wait for pending requests."""
        self._executor.shutdown(wait=True)


# Global instance for backward compatibility
_default_service: Optional[NotificationService] = None


def get_default_service() -> NotificationService:
    """Get the default notification service instance."""
    global _default_service
    if _default_service is None:
        _default_service = NotificationService()
    return _default_service


def _get_service(backend_url: str) -> NotificationService:
    """Get a notification service instance for the given backend URL."""
    if backend_url != "http://localhost:5000":
        return NotificationService(backend_url)
    return get_default_service()


# Backward compatibility functions
def notify_dashboard_update(
    user_id: str, backend_url: str = "http://localhost:5000"
) -> None:
    """Notify dashboard update (backward compatibility)."""
    _get_service(backend_url).notify_dashboard_update(user_id)


def push_user_input(
    user_id: str, text: str, backend_url: str = "http://localhost:5000"
) -> None:
    """Push user input (backward compatibility)."""
    _get_service(backend_url).push_user_input(user_id, text)


def push_streaming_chunk(
    user_id: str, chunk: str, is_final: bool, backend_url: str = "http://localhost:5000"
) -> None:
    """Push streaming chunk (backward compatibility)."""
    _get_service(backend_url).push_streaming_chunk(user_id, chunk, is_final)


def push_audio_chunk(
    user_id: str,
    chunk_b64: str,
    sample_rate: int,
    is_final: bool,
    text_hash: Optional[str] = None,
    text_preview: Optional[str] = None,
    backend_url: str = "http://localhost:5000",
) -> None:
    """Push audio chunk (backward compatibility)."""
    _get_service(backend_url).push_audio_chunk(
        user_id,
        chunk_b64,
        sample_rate,
        is_final,
        text_hash=text_hash,
        text_preview=text_preview,
    )


def push_status(
    user_id: str, status: str, backend_url: str = "http://localhost:5000"
) -> None:
    """Push status (backward compatibility)."""
    _get_service(backend_url).push_status(user_id, status)
