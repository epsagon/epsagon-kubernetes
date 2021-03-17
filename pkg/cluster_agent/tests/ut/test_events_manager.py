"""
EventsManager tests
"""
import asyncio
import pytest
from events_manager import InMemoryEventsManager
from kubernetes_event import WatchKubernetesEvent, WatchKubernetesEventType
from conftest import run_coroutines_with_timeout

DEFAULT_MAX_SIZE = 2

@pytest.fixture
def in_memory_events_manager():
    """
    In memory events manager fixture
    """
    return InMemoryEventsManager()


@pytest.mark.asyncio
async def test_is_empty_sanity(in_memory_events_manager):
    """
    is_empty sanity test
    """
    assert in_memory_events_manager.is_empty()


@pytest.mark.asyncio
async def test_is_empty_with_data(in_memory_events_manager):
    """
    is_empty test with events being written to events manager
    """
    assert in_memory_events_manager.is_empty()
    event = WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
    await in_memory_events_manager.write_event(event)
    assert not in_memory_events_manager.is_empty()
    await run_coroutines_with_timeout((in_memory_events_manager.get_event(), ))
    assert in_memory_events_manager.is_empty()


@pytest.mark.asyncio
async def test_get_and_write_sanity(in_memory_events_manager):
    """
    sanity test for write_event and get_event
    """
    event = WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
    await in_memory_events_manager.write_event(event)
    task = (await run_coroutines_with_timeout(
        (in_memory_events_manager.get_event(), )
    ))[0]
    assert event == task.result()


@pytest.mark.asyncio
async def test_get_events_sanity(in_memory_events_manager):
    """
    sanity test for get_events
    """
    events = [
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
        WatchKubernetesEvent(WatchKubernetesEventType.DELETED, {"a": "c"}),
    ]
    for event in events:
        await in_memory_events_manager.write_event(event)
    task = (await run_coroutines_with_timeout(
        (in_memory_events_manager.get_events(max_size=DEFAULT_MAX_SIZE), )
    ))[0]
    assert events == task.result()


@pytest.mark.asyncio
async def test_get_events_custom_max_size(in_memory_events_manager):
    """
    test for get_events with a custom max size
    """
    custom_max_size = 1
    events = [
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
        WatchKubernetesEvent(WatchKubernetesEventType.DELETED, {"a": "c"}),
    ]
    for event in events:
        await in_memory_events_manager.write_event(event)
    for i, event in enumerate(events):
        task = (await run_coroutines_with_timeout(
            (in_memory_events_manager.get_events(max_size=custom_max_size), )
        ))[0]
        assert events[i:i + custom_max_size] == task.result()


@pytest.mark.asyncio
async def test_get_events_zero_max_size(in_memory_events_manager):
    """
    test for get_events with max size = 0
    """
    events = [
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
        WatchKubernetesEvent(WatchKubernetesEventType.DELETED, {"a": "c"}),
    ]
    for event in events:
        await in_memory_events_manager.write_event(event)
    task = (await run_coroutines_with_timeout(
        (in_memory_events_manager.get_events(max_size=0), )
    ))[0]
    assert [] == task.result()


@pytest.mark.asyncio
async def test_clean_sanity(in_memory_events_manager):
    """
    sanity test for clean method
    """
    events = [
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
        WatchKubernetesEvent(WatchKubernetesEventType.DELETED, {"a": "c"}),
    ]
    for event in events:
        await in_memory_events_manager.write_event(event)
    in_memory_events_manager.clean()
    assert in_memory_events_manager.is_empty()


@pytest.mark.asyncio
async def test_clean_no_events(in_memory_events_manager):
    """
    test for clean method where the manager is already empty
    """
    assert in_memory_events_manager.is_empty()
    in_memory_events_manager.clean()
    assert in_memory_events_manager.is_empty()
