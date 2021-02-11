"""
KubernetesEvent forwarder
"""
import asyncio
from typing import List, Set
from kubernetes_event import KubernetesEvent
from events_manager import EventsManager
from events_sender import EventsSender


class Forwarder:
    """
    A generic KubernetesEvent forwarder
    """
    DEFAULT_MAX_WORKERS = 5
    DEFAULT_MAX_EVENTS_TO_READ = 100

    def __init__(
            self,
            events_manager: EventsManager,
            events_sender: EventsSender,
            max_workers: int = DEFAULT_MAX_WORKERS,
            max_events_to_read: int = DEFAULT_MAX_EVENTS_TO_READ
    ):
        """
        :param events_manager: used to read from events
        :param events_sender: used to send read events to
        :param max_workers: to forward read events
        :param max_events_to_read: to read from the events_manager
        """
        self.events_manager = events_manager
        self.events_sender = events_sender
        if max_workers < 1:
            raise ValueError("Invalid workers count value, must be > 0")
        self.max_workers_count: int = max_workers
        if max_events_to_read < 1:
            raise ValueError("Invalid max events to read value, must be > 0")
        self.max_events_to_read: int = max_events_to_read
        self.running_workers: Set[asyncio.Task] = set()

    async def _forward_events(self, events: List[KubernetesEvent]):
        """
        Forwards the given events list
        """
        await self.events_sender.send_events(events)

    async def start(self):
        """
        Starts the Forwarder. The forwarder will read up to MAX_EVENTS_TO_READ
        at each iteration using the events_manager, and sends them using the
        events_sender.
        """
        try:
            while True:
                events: List[KubernetesEvent] = (
                    await self.events_manager.get_events(
                        self.max_events_to_read
                ))
                if len(self.running_workers) < self.max_workers_count:
                    self.running_workers.add(asyncio.ensure_future(
                        self._forward_events(events)
                    ))
                else:
                    finished, unfinished = await asyncio.wait(
                        self.running_workers,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    self.running_workers = unfinished
                    self.running_workers.add(asyncio.ensure_future(
                        self._forward_events(events)
                    ))
        except asyncio.CancelledError:
            pass
