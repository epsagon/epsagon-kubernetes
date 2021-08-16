"""
Events managers module
"""
import abc
import logging
from asyncio import Queue, wait_for, TimeoutError
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

    async def _read_event(self, timeout: int=None):
        """
        Reads and returns an event. If timeout is given, then trying to read event up to
        the timeout given value.
        In case of timeout, returns None.
        """
        event = None
        try:
            event = await wait_for(self.get_event(), timeout=timeout)
        except TimeoutError:
            pass

        return event

    async def get_events(self, max_size: int, timeout: int=None) -> List[KubernetesEvent]:
        """
        Reads up to max_size events.
        The functions waits until the earlier:
        - there's at least one event. In this case, returns all the
        existing events.
        - timeout been passed (in case its given). In this case, an empty list is returned.
        :param max_size: of events to read
        If max_size < 1, then returning an empty list.
        If the current events count in the queue is less than max_size, then
        returns just the current events.
        :param timeout: If given, then setting this timeout for the first
        read event attempt. If no event is read during after the given timeout,
        the functions returns with an empty list.
        """
        if max_size < 1:
            return []

        first_event = await self._read_event(timeout=timeout)
        if not first_event:
            return []

        events = [first_event]
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
