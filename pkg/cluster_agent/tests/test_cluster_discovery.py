"""
ClusterDiscovery tests
"""
import asyncio
import socket
import pytest
import kubernetes_asyncio
from typing import List, Dict, Set
from collections import namedtuple
from asynctest.mock import patch
from cluster_discovery import ClusterDiscovery, WatchTarget
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    KubernetesEventType,
    WatchKubernetesEventType,
)
from conftest import run_coroutines_with_timeout

TEST_VERSION = "v1.18"
CLUSTER_EVENT = KubernetesEvent(
    KubernetesEventType.CLUSTER,
    {
        "version": TEST_VERSION
    }
)

# WatchTarget used to test the cluster discovery watchers
TestWatchTarget = namedtuple(
    "WatchTarget",
    [
        "name", # of the watch target
        "events", # to be sent from this watch target
        "error", # to be raised by this watch target
        "delay", # time to wait between each event
    ]
)


class KubernetesResourceObject:
    """ Test kubernetes resource object """
    def __init__(self, data: Dict):
        self.data = data

    def to_dict(self):
        """ to dict - gets the original data """
        return self.data

class EventsManager:
    """
    EventsManager, used for writing & validating given events
    """
    def __init__(self):
        self.events: Set[KubernetesEvent] = set()

    async def write_event(self, event: KubernetesEvent):
        """ Adds an event to the manager """
        self.events.add(event)


class EventsGenerator:
    """
    Events generator, used for each watch target
    """

    def __init__(self, events, delay=0):
        """
        :param events: to return one be one
        :param delay: between each event
        """
        self.i = 0 # current event
        self.events = events
        self.delay = delay

    def __aiter__(self):
        return self

    async def __anext__(self):
        """
        Gets the next event. Waits delay seconds between each event
        When done, sleeping "forever" - to simulate a "real" scenario where
        the events stream doesn't end.
        """
        i = self.i
        if self.i >= len(self.events):
            # sleeps forever, simulating a real scenario
            await asyncio.sleep(1000)
        self.i += 1
        if i:
            await asyncio.sleep(self.delay)
        return self.events[i]


class WatchMock:
    """
    A mock class for the kubernetes client Watch class
    """
    def stream(self, target: TestWatchTarget, resource_version=None):
        """
        Gets the events stream, raises an error if the
        TestWatchTarget is configured with one
        """
        if target.error:
            raise target.error

        return EventsGenerator(target.events, delay=target.delay)



class ClientMock:
    """
    A kubernetes API client mock class
    (used for the cluster version retrieval)
    """
    def __init__(self, error=None):
        """
        :param error: to raise when used
        """
        self.error = error

    async def get_code(self):
        """
        Gets the cluster version code. Raises an error if self.error
        """
        if self.error:
            raise self.error
        class VersionResponse:
            """ Version response, as returned from the API server """
            def __init__(self, git_version):
                """
                :param git_version: the cluster version to return
                """
                self.git_version = git_version

        return VersionResponse(TEST_VERSION)


def _patch_cluster_discovery_watch_targets(
        cluster_discovery: ClusterDiscovery,
        watch_targets: List[TestWatchTarget],
        version_client
):
    """
    Patches the cluster discovery obj - replace all watch targets and the
    cluster version client with the `fake` ones.
    """
    cluster_discovery.watch_targets = {
        target.name: WatchTarget(target) for target in watch_targets
    }
    cluster_discovery.version_client = version_client


@pytest.fixture
def raw_target_events() -> List[List[Dict]]:
    """
    Generate some events. Each events list item is for one `watch target`
    :return: A list of event lists
    """
    return [
        [
            {
                "type": "ADDED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "1a": "1a"})
                )
            },
            {
                "type": "ADDED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "1aa": "1aa"})
                )
            },
            {
                "type": "MODIFIED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "1m": "1m"})
                )
            },
            {
                "type": "DELETED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "1d": "1d"})
                )
            },
        ],
        [
            {
                "type": "ADDED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "2a": "2a"})
                )
            },
            {
                "type": "MODIFIED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "2m": "2m"})
                )
            },
            {
                "type": "MODIFIED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "2mm": "2mm"})
                )
            },
            {
                "type": "DELETED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "2d": "1d"})
                )
            },
        ],
        [
            {
                "type": "ADDED",
                WatchKubernetesEvent.OBJECT_FIELD_KEY: (
                    KubernetesResourceObject({ "3a": "3a"})
                )
            },
        ],
    ]


def _get_expected_events(
        raw_events: List[List[WatchKubernetesEvent]],
        cluster_event: KubernetesEvent
) -> Set[KubernetesEvent]:
    """
    Gets the expected events objects. Skips invalid events.
    If cluster_event is given then adding it to the expected events
    """
    events = {
        WatchKubernetesEvent.from_watch_dict(raw_event)
        for target_events in raw_events
        for raw_event in target_events
        if WatchKubernetesEvent.OBJECT_FIELD_KEY in raw_event # skip invalid test events
    }
    if cluster_event:
        events.add(cluster_event)

    return events


async def _run_cluster_discovery(
        cluster_discovery,
        events_manager,
        raw_events,
        cluster_event,
        watch_stream_error=None,
):
    """
    Runs the cluster discovery (cluster_discovery.start).
    Validates the task status (is running/task had an exception), and
    that the actual written events are the expected ones.
    """
    task = (await run_coroutines_with_timeout(
        (cluster_discovery.start(),),
        verify_tasks_finished=False,
        timeout=0.2
    ))[0]
    if watch_stream_error:
        expected_events = set()
        if type(watch_stream_error) == Exception:
            # unhandled error, task should be done
            assert task.done()
            assert type(task.exception()) == Exception
        else: # task is expected to run as error should be handled
            assert not task.done()
    else:
        expected_events = _get_expected_events(raw_events, cluster_event)
        # normal run - cluster discovery shouldn't stop
        assert not task.done()

    assert expected_events == events_manager.events
    if not task.done():
        task.cancel()


async def _test_cluster_discovery(
        raw_events,
        include_cluster_event=True,
        include_invalid_watch_event=False,
        watch_stream_error=None,
) -> ClusterDiscovery:
    """
    Tests the cluster discovery run.
    :param raw_events: to be read by the cluster discovery watch tasks
    :param include_cluster_event: indicates whether should expect a cluster info
    event or should raise an error for this request.
    :param include_invalid_watch_event: indicates whetherto include an invalid
    watch events
    :param watch_stream_error: error to be raised when the cluster discovery
    tries to watch its targets.
    :return: the cluster discovery object
    """
    cluster_event = None
    cluster_error = Exception()
    if include_cluster_event:
        cluster_event = CLUSTER_EVENT
        cluster_error = None

    version_client = ClientMock(error=cluster_error)
    manager = EventsManager()
    cluster_discovery = ClusterDiscovery(manager.write_event)
    if include_invalid_watch_event:
        for target_events in raw_events:
            target_events.append({ "invalid_event": "invalid"})

    # prepare watch targets - with events and possibly an error, if given
    targets = [
        TestWatchTarget(str(i), raw_events[i], watch_stream_error, 0.01)
        for i in range(len(raw_events))
    ]
    # replace watch targets & version cluent at cluster_discovery
    _patch_cluster_discovery_watch_targets(
        cluster_discovery, targets, version_client
    )
    # tests the cluster discovery run
    await _run_cluster_discovery(
        cluster_discovery,
        manager,
        raw_events,
        cluster_event=cluster_event,
        watch_stream_error=watch_stream_error
    )
    return cluster_discovery


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_sanity(_, raw_target_events):
    """
    Sanity test - read multiple events
    """
    await _test_cluster_discovery(raw_target_events, )


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_invalid_cluster_version(_, raw_target_events):
    """
    Tests multiple events with no cluster version info.
    Expects the cluster discovery to run & collect the watch events.
    """
    await _test_cluster_discovery(
        raw_target_events,
        include_cluster_event=False
    )


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_invalid_watch_event(_, raw_target_events):
    """
    Tests multiple events with some invalid watch events
    Expects the cluster discovery to run, collect the watch events and
    skip the invalid events.
    """
    await _test_cluster_discovery(
        raw_target_events,
        include_invalid_watch_event=True
    )


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_watch_stream_unhandled_error(_, raw_target_events):
    """
    Tests watch stream unhandled error - expect no events and the task to raise
    the error.
    """
    await _test_cluster_discovery(
        raw_target_events,
        include_cluster_event=False,
        watch_stream_error=Exception()
    )


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_watch_stream_handled_error(_, raw_target_events):
    """
    Tests watch stream handled error - expect no events and the task should
    still be running.
    """
    await _test_cluster_discovery(
        raw_target_events,
        include_cluster_event=False,
        watch_stream_error=socket.gaierror
    )


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
async def test_invalid_retry_interval_seconds(_):
    """
    Tests invalid retry interval seconds param
    """
    with pytest.raises(ValueError):
        ClusterDiscovery(None, retry_interval_seconds=-1)


@pytest.mark.asyncio
@patch("kubernetes_asyncio.client")
@patch("kubernetes_asyncio.watch.Watch", WatchMock)
async def test_stop(_, raw_target_events):
    """
    Tests cluster_discovery.stop - expect all discover tasks to be done
    """
    cluster_discovery: ClusterDiscovery = (
        await _test_cluster_discovery(raw_target_events, )
    )
    cluster_discovery.stop()
    # tasks are already cancelled - CancelledError will be raised when
    # they will be scheduled to run.
    # Waiting for the task objects status to be update for testing purpose.
    await asyncio.sleep(0.1)
    for task in cluster_discovery.discover_tasks:
        assert task.done() or task.cancelled()
