"""
KubernetesEvent tests
"""
import pytest
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    KubernetesEventType,
    WatchKubernetesEventType,
)

@pytest.mark.asyncio
async def test_initialize():
    """ Initialize sanity test """
    for current_type in KubernetesEventType:
        KubernetesEvent(current_type, {})


@pytest.mark.asyncio
async def test_get_formatted_payload():
    """ get_formatted_payload test """
    data = {
        "A": "a"
    }
    event = KubernetesEvent(KubernetesEventType.CLUSTER, data)
    assert event.get_formatted_payload() == data


def _get_expected_dict(event):
    """ Gets the expected event dict """
    if type(event) == KubernetesEvent:
        return {
            "metadata": {
                "kind": event.event_type.value.lower(),
            },
            "payload": event.data,
        }
    elif type(event) == WatchKubernetesEvent:
        return {
            "metadata": {
                "kind": event.event_type.value.lower(),
            },
            "payload": {
                "type": event.watch_event_type.value.lower(),
                "object": event.data,
            }
        }

    raise Exception(f"Unsupported event type: {type(event)}")


@pytest.mark.asyncio
async def test_to_dict():
    """ to_dict test """
    data = {
        "A": "a"
    }
    event_type = KubernetesEventType.CLUSTER
    event = KubernetesEvent(event_type, data)
    assert event.to_dict() == _get_expected_dict(event)


@pytest.mark.asyncio
async def test_equity():
    """ __eq__ test """
    all_data = [
        {
            "A": "a"
        },
        {
            "A": "a"
        },
        {
            "B": "a"
        },
    ]
    event_type = KubernetesEventType.CLUSTER
    events = [
        KubernetesEvent(event_type, event_data)
        for event_data in all_data
    ]
    assert events[0] == events[1]
    assert events[0] != events[2]


@pytest.mark.asyncio
async def test_watch_initialize():
    """ Watch events - initialize sanity test """
    for current_type in WatchKubernetesEventType:
        WatchKubernetesEvent(current_type, {})


@pytest.mark.asyncio
async def test_watch_get_formatted_payload():
    """ get_formatted_payload test """
    data = {
        "A": "a"
    }
    event_type = WatchKubernetesEventType.ADDED
    event = WatchKubernetesEvent(event_type, data)
    assert event.get_formatted_payload() == {
        "type": event_type.value.lower(),
        "object": data,
    }


@pytest.mark.asyncio
async def test_watch_to_dict():
    """ to_dict test """
    data = {
        "A": "a"
    }
    event_type = WatchKubernetesEventType.ADDED
    event = WatchKubernetesEvent(event_type, data)
    assert event.to_dict() == _get_expected_dict(event)


@pytest.mark.asyncio
async def test_watch_equity():
    """ __eq__ test """
    all_data = [
        {
            "A": "a"
        },
        {
            "A": "a"
        },
        {
            "B": "a"
        },
    ]
    event_type = WatchKubernetesEventType.ADDED
    events = [
        WatchKubernetesEvent(event_type, event_data)
        for event_data in all_data
    ]
    assert events[0] == events[1]
    assert events[0] != events[2]
