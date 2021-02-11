"""
Forwarder tests
"""
import pytest
import asyncio
from typing import List
from events_manager import EventsManager, InMemoryEventsManager
from forwarder import Forwarder
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    WatchKubernetesEventType,
)
from conftest import run_coroutines_with_timeout

DEFAULT_MAX_EVENTS_TO_READ = Forwarder.DEFAULT_MAX_EVENTS_TO_READ
DEFAULT_MAX_WORKERS = Forwarder.DEFAULT_MAX_WORKERS
DEFAULT_EVENTS_COUNT = 1000

class EventsManagerMock(InMemoryEventsManager):
    """ EventsManager mock, verifies max events to read """
    def __init__(self, expected_max_size):
        """
        :param expected_max_size: the expected max size when using get_events
        """
        super().__init__()
        self.expected_max_size = expected_max_size

    async def get_events(self, max_size: int) -> List[KubernetesEvent]:
        """
        Asserts the given max size,
        """
        assert max_size == self.expected_max_size
        return await super().get_events(max_size)

class EventsSenderMock:
    """ EventsSender mock, verifies max worker senders """
    def __init__(self, expected_max_workers: int):
        """
        :param expected_max_workers: the expected max size of workers used
        to send events
        """
        self.expected_max_workers = expected_max_workers
        self.current_workers_count = 0
        self.events = set()

    async def send_events(self, events: List[KubernetesEvent]):
        """
        Asserts the current number of workers <= expected max workers and saves
        the given events.
        when called, using asyncio.sleep to simulate a "real" send scenario
        """
        self.current_workers_count += 1
        assert self.current_workers_count <= self.expected_max_workers
        for event in events:
            self.events.add(event)
        await asyncio.sleep(0.1)
        self.current_workers_count -= 1


async def _write_events(
        events: List[KubernetesEvent],
        events_manager: EventsManager
):
    """
    Writes given events using given events manager.
    After each written event, returns control to event loop using asyncio.sleep
    Used to simulate a real scenario where the event loop gets control between
    calls to write_event
    """
    for event in events:
        await events_manager.write_event(event)
        asyncio.sleep(0)


def _generate_kubernetes_events(count: int) -> List[KubernetesEvent]:
    """ Generates <count> kubernetes event """
    return [
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {i: i})
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_sanity():
    """
    sanity test - runs forwarder while writing events, verifies all events are sent.
    """
    events_manager = EventsManagerMock(DEFAULT_MAX_EVENTS_TO_READ)
    events_sender = EventsSenderMock(DEFAULT_MAX_WORKERS)
    events: List[KubernetesEvent] = _generate_kubernetes_events(DEFAULT_EVENTS_COUNT)
    events_write_task, forwarder_task = await run_coroutines_with_timeout(
        (
            _write_events(events, events_manager),
            Forwarder(events_manager, events_sender).start()
        ),
        verify_tasks_finished=False,
        timeout=0.5,
    )
    assert events_write_task.done()
    assert not forwarder_task.done()
    forwarder_task.cancel()
    assert set(events) == events_sender.events


@pytest.mark.asyncio
async def test_max_events_to_read():
    """
    Runs forwarder while writing events, verifies all events are sent and
    verifies no more than the given max events to read are read.
    """
    max_events_to_read = 10
    events_manager = EventsManagerMock(max_events_to_read)
    events_sender = EventsSenderMock(DEFAULT_MAX_WORKERS)
    events: List[KubernetesEvent] = _generate_kubernetes_events(DEFAULT_EVENTS_COUNT)
    events_write_task, forwarder_task = await run_coroutines_with_timeout(
        (
            _write_events(events, events_manager),
            Forwarder(
                events_manager,
                events_sender,
                max_events_to_read=max_events_to_read
            ).start(),
        ),
        verify_tasks_finished=False,
        timeout=3,
    )
    assert events_write_task.done()
    assert not forwarder_task.done()
    forwarder_task.cancel()
    assert set(events) == events_sender.events

@pytest.mark.asyncio
async def test_max_workers():
    """
    Runs forwarder while writing events, verifies all events are sent and
    verifies no more than the given workers count ran
    concurrently (asyncronously)
    """
    max_workers = 2
    events_manager = EventsManagerMock(DEFAULT_MAX_EVENTS_TO_READ)
    events_sender = EventsSenderMock(max_workers)
    events: List[KubernetesEvent] = _generate_kubernetes_events(DEFAULT_EVENTS_COUNT)
    events_write_task, forwarder_task = await run_coroutines_with_timeout(
        (
            _write_events(events, events_manager),
            Forwarder(
                events_manager,
                events_sender,
                max_workers=max_workers
            ).start(),
        ),
        verify_tasks_finished=False,
        timeout=1,
    )
    assert events_write_task.done()
    assert not forwarder_task.done()
    forwarder_task.cancel()
    assert set(events) == events_sender.events
