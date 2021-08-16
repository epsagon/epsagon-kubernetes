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
    DEFAULT_GET_EVENTS_TIMEOUT = 1

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
        try:
            await self.events_sender.send_events(events)
        except asyncio.CancelledError:
            pass

    def _stop_all_workers(self):
        """
        Stops all workers
        """
        for worker in self.running_workers:
            if not worker.done():
                worker.cancel()
            elif not worker.cancelled():
                worker.exception()
        self.running_workers = set()

    def _check_failed_workers(self, workers):
        """
        Checks the finished workers status. If any worker had an error, then
        stopping the rest of the workers and raising an error.
        """
        for task in workers:
            task_exception = task.exception()
            if task_exception:
                self._stop_all_workers()
                raise task_exception

    def _get_finished_workers(self):
        """
        Gets the running workers tasks
        """
        return [task for task in self.running_workers if task.done()]

    async def start(self):
        """
        Starts the Forwarder. The forwarder will read up to MAX_EVENTS_TO_READ
        at each iteration using the events_manager, and sends them using the
        events_sender.
        """
        try:
            while True:
                events: List[KubernetesEvent] = await self.events_manager.get_events(
                    self.max_events_to_read,
                    timeout=self.DEFAULT_GET_EVENTS_TIMEOUT
                )
                self._check_failed_workers(self._get_finished_workers())
                if not events:
                    continue
                if len(self.running_workers) < self.max_workers_count:
                    self.running_workers.add(asyncio.create_task(
                        self._forward_events(events)
                    ))
                else:
                    finished, unfinished = await asyncio.wait(
                        self.running_workers,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    self._check_failed_workers(finished)
                    self.running_workers = unfinished
                    self.running_workers.add(asyncio.create_task(
                        self._forward_events(events)
                    ))
        except asyncio.CancelledError:
            self._stop_all_workers()

