"""
KubernetesEvent tests
"""
import time
import pytest
from asynctest.mock import patch, MagicMock
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    KubernetesEventType,
    WatchKubernetesEventType,
)

FAKE_TIMESTAMP = time.time_ns()

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
                "timestamp": FAKE_TIMESTAMP,
            },
            "payload": event.data,
        }
    elif type(event) == WatchKubernetesEvent:
        return {
            "metadata": {
                "kind": event.event_type.value.lower(),
                "timestamp": FAKE_TIMESTAMP,
            },
            "payload": {
                "type": event.watch_event_type.value,
                "object": event.data,
            }
        }

    raise Exception(f"Unsupported event type: {type(event)}")


@pytest.mark.asyncio
@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
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
        "type": event_type.value,
        "object": data,
    }


@pytest.mark.asyncio
@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
async def test_watch_to_dict():
    """ to_dict test """
    data = {
        "A": "a"
    }
    event_type = WatchKubernetesEventType.ADDED
    event = WatchKubernetesEvent(event_type, data)
    assert event.to_dict() == _get_expected_dict(event)


@pytest.mark.asyncio
@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
async def test_watch_get_resource_version():
    """ get_resource_version sanity test """
    resource_version = "3"
    data = {
        "A": "a",
        "metadata": {
            "resourceVersion": resource_version,
        }
    }
    event_type = WatchKubernetesEventType.ADDED
    event = WatchKubernetesEvent(event_type, data)
    assert event.to_dict() == _get_expected_dict(event)
    assert resource_version == event.get_resource_version()


@pytest.mark.asyncio
@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
async def test_watch_get_resource_version():
    """ get_resource_version test - no resource version """
    data = {
        "A": "a",
        "metadata2222": {
            "a": "b"
        }
    }
    event_type = WatchKubernetesEventType.ADDED
    event = WatchKubernetesEvent(event_type, data)
    assert event.to_dict() == _get_expected_dict(event)
    assert not event.get_resource_version()


@pytest.mark.asyncio
@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
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
