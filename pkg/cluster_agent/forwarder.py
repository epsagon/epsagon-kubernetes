"""
KubernetesEvent forwarder
"""
import asyncio
from typing import List
from kubernetes_event import KubernetesEvent
from events_manager import EventsManager
from events_sender import EventsSender


class Forwarder:
    """
    A generic KubernetesEvent forwarder
    """

    MAX_EVENTS_TO_READ = 300

    def __init__(
            self,
            events_manager: EventsManager,
            events_sender: EventsSender
    ):
        """
        :param events_manager: used to read from events
        :param events_sender: used to send read events to
        """
        self.events_manager = events_manager
        self.events_sender = events_sender

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
                        self.MAX_EVENTS_TO_READ
                ))
                await self.events_sender.send_events(events)
        except asyncio.CancelledError:
            pass
