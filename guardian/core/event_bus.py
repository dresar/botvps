"""Async EventBus — pub/sub antar komponen Serverinka Guardian."""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Sistem publish/subscribe async untuk komunikasi antar-plugin.

    Plugin tidak boleh saling mengimport secara langsung. Sebagai gantinya,
    mereka berkomunikasi melalui EventBus dengan cara publish event dan
    subscribe ke event yang mereka minati.

    Error pada satu subscriber tidak menghentikan subscriber lain
    atau publisher.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard_subscribers: list[EventHandler] = []

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Daftarkan handler untuk event tertentu.

        Args:
            event_name: Nama event. Gunakan "*" untuk menerima semua event.
            handler: Async function yang menerima payload dict.
        """
        if event_name == "*":
            self._wildcard_subscribers.append(handler)
        else:
            self._subscribers[event_name].append(handler)
        logger.debug("Handler terdaftar untuk event.", event_name=event_name)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Hapus handler dari daftar subscriber.

        Args:
            event_name: Nama event.
            handler: Handler yang akan dihapus.
        """
        if event_name == "*":
            self._wildcard_subscribers = [
                h for h in self._wildcard_subscribers if h is not handler
            ]
        elif event_name in self._subscribers:
            self._subscribers[event_name] = [
                h for h in self._subscribers[event_name] if h is not handler
            ]

    async def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        """Publikasikan event ke semua subscriber secara async.

        Error pada satu subscriber tidak memblokir subscriber lain.

        Args:
            event_name: Nama event yang dipublikasikan.
            payload: Data event. Default ke dict kosong.
        """
        if payload is None:
            payload = {}

        handlers = list(self._subscribers.get(event_name, []))
        handlers.extend(self._wildcard_subscribers)

        if not handlers:
            logger.debug("Tidak ada subscriber untuk event.", event_name=event_name)
            return

        logger.debug(
            "Mempublikasikan event.",
            event_name=event_name,
            subscriber_count=len(handlers),
        )
        tasks = [self._invoke_handler(handler, event_name, payload) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _invoke_handler(
        self,
        handler: EventHandler,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        """Panggil handler dengan isolasi error.

        Args:
            handler: Handler yang akan dipanggil.
            event_name: Nama event.
            payload: Data event.
        """
        try:
            await handler(payload)
        except Exception:
            logger.exception(
                "Error pada event subscriber.",
                event_name=event_name,
                handler=getattr(handler, "__qualname__", str(handler)),
            )

    def subscriber_count(self, event_name: str) -> int:
        """Jumlah subscriber untuk event tertentu.

        Args:
            event_name: Nama event.

        Returns:
            Jumlah subscriber.
        """
        return len(self._subscribers.get(event_name, []))

    def clear(self) -> None:
        """Hapus semua subscriber. Digunakan untuk cleanup."""
        self._subscribers.clear()
        self._wildcard_subscribers.clear()
