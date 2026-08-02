"""Unit tests untuk EventBus."""

import asyncio

import pytest


class TestEventBus:
    """Test suite untuk EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Subscribe dan publish event harus memanggil handler."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        bus.subscribe("test.event", handler)
        await bus.publish("test.event", {"key": "value"})

        assert len(received) == 1
        assert received[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_wildcard_subscriber(self):
        """Wildcard subscriber harus menerima semua event."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        all_received: list[str] = []

        async def wildcard_handler(payload: dict) -> None:
            all_received.append(payload.get("type", ""))

        bus.subscribe("*", wildcard_handler)
        await bus.publish("event.a", {"type": "a"})
        await bus.publish("event.b", {"type": "b"})

        assert "a" in all_received
        assert "b" in all_received

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        """Publish ke event tanpa subscriber tidak boleh raise exception."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        await bus.publish("no.one.listening", {})

    @pytest.mark.asyncio
    async def test_subscriber_error_isolated(self):
        """Error pada satu subscriber tidak boleh mempengaruhi subscriber lain."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        second_called = False

        async def failing_handler(payload: dict) -> None:
            raise RuntimeError("Intentional error")

        async def second_handler(payload: dict) -> None:
            nonlocal second_called
            second_called = True

        bus.subscribe("test.isolated", failing_handler)
        bus.subscribe("test.isolated", second_handler)

        await bus.publish("test.isolated", {})
        assert second_called is True

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Unsubscribe harus menghentikan panggilan ke handler."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        call_count = 0

        async def handler(payload: dict) -> None:
            nonlocal call_count
            call_count += 1

        bus.subscribe("test.unsub", handler)
        await bus.publish("test.unsub", {})
        bus.unsubscribe("test.unsub", handler)
        await bus.publish("test.unsub", {})

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Banyak subscriber untuk event yang sama semua harus dipanggil."""
        from guardian.core.event_bus import EventBus

        bus = EventBus()
        results: list[int] = []

        for i in range(5):
            async def make_handler(idx: int):
                async def handler(payload: dict) -> None:
                    results.append(idx)
                return handler
            bus.subscribe("test.multi", await make_handler(i))

        await bus.publish("test.multi", {})
        assert len(results) == 5
