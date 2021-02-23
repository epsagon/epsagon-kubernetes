"""
EventsSender tests
"""
import base64
import json
import zlib
import pytest
from typing import Dict, List
from asynctest.mock import patch, MagicMock
from encoders import DateTimeEncoder
from epsagon_client import EpsagonClient
from events_sender import EventsSender
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    KubernetesEventType,
    WatchKubernetesEventType,
)

TEST_URL = "http://testurl/1"
TEST_CLUSTER_NAME = "test-cluster-name"
TEST_EPSAGON_TOKEN = "1234"


def _get_expected_data(
        events_sender: EventsSender,
        events: List[KubernetesEvent]
):
    """
    Gets the expected data to be sent given events list and events sender
    """
    events = [event.to_dict() for event in events]
    events_json = json.dumps(events, cls=DateTimeEncoder)
    compressed_data = base64.b64encode(
        zlib.compress(events_json.encode("utf-8"))
    ).decode("utf-8")
    data_to_send = {
        "epsagon_token": events_sender.epsagon_token,
        "cluster_name": events_sender.cluster_name,
        "data": compressed_data,
    }
    return json.dumps(data_to_send)


@pytest.mark.asyncio
@patch("epsagon_client.EpsagonClient")
async def test_send_events_sanity(epsagon_client_mock):
    epsagon_client_obj = epsagon_client_mock.return_value
    sender = EventsSender(
        epsagon_client_obj,
        TEST_URL,
        TEST_CLUSTER_NAME,
        TEST_EPSAGON_TOKEN
    )
    events = [
        KubernetesEvent(KubernetesEventType.CLUSTER, {"a": "b"}),
        WatchKubernetesEvent(WatchKubernetesEventType.ADDED, {"a": "b"}),
    ]
    await sender.send_events(events)
    epsagon_client_obj.post.assert_called_once_with(
        TEST_URL,
        _get_expected_data(sender, events)
    )


@pytest.mark.asyncio
@patch("epsagon_client.EpsagonClient")
async def test_send_no_events(epsagon_client_mock):
    epsagon_client_obj = epsagon_client_mock.return_value
    sender = EventsSender(
        epsagon_client_obj,
        TEST_URL,
        TEST_CLUSTER_NAME,
        TEST_EPSAGON_TOKEN
    )
    events = []
    await sender.send_events(events)
    epsagon_client_obj.post.assert_not_called()
