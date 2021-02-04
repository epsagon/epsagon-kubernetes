"""
Events managers module
"""
import abc
import logging
from asyncio import Queue
from typing import List
from kubernetes_event import KubernetesEvent


class EventsManager(abc.ABC):
    """
    An abstract asynchronous events manager - used to read from & write to
    asynchronously.
    Each specific events manager should inherit from this class.
    """

    @abc.abstractmethod
    def is_empty(self) -> bool:
        """
        Returns whether there're no unread events
        """
        raise NotImplementedError


    @abc.abstractmethod
    async def write_event(self, event: KubernetesEvent):
        """
        Writes an event
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_event(self) -> KubernetesEvent:
        """
        Reads an event
        """
        raise NotImplementedError


    async def get_events(self, max_size) -> List[KubernetesEvent]:
        """
        Reads up to max_size events.
        Waits until there's at least one event. Then, reading up to max_size
        events (or all existing events if it's less than max_size)
        """
        events = [await self.get_event()]
        while not self.is_empty() and len(events) < max_size:
            events.append(await self.get_event())

        return events


class InMemoryEventsManager(EventsManager):
    """
    Im memory events manager
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events_queue = Queue()

    def is_empty(self) -> bool:
        return self.events_queue.empty()

    async def write_event(self, event: KubernetesEvent):
        await self.events_queue.put(event)

    async def get_event(self) -> KubernetesEvent:
        return await self.events_queue.get()

    def clean(self):
        """
        Cleans all events.
        """
        self.events_queue = Queue()
