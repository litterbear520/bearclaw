from abc import ABC, abstractmethod
from typing import Any

from bus.events import InboundMessage, OutboundMessage
from bus.queue import MessageBus


class BaseChannel(ABC):

    name: str = "base"

    def __init__(self, bus: MessageBus):
        self.bus = bus
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        pass

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            metadata=metadata or {},
        )
        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        return self._running