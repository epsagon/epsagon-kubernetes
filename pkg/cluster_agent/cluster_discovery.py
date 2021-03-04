"""
Cluster discovery - watch & publish events in the cluster
"""
import asyncio
import logging
import socket
from dataclasses import dataclass
from typing import Callable, Any, Dict
from traceback import format_exc
import kubernetes_asyncio
from aiohttp.client_exceptions import ClientError
from kubernetes_event import (
    KubernetesEvent,
    WatchKubernetesEvent,
    WatchKubernetesEventType,
    KubernetesEventException,
    KubernetesEventType,
)

@dataclass
class WatchTarget:
    """ watch target """
    endpoint: Callable # endpoint to watch
    last_resource_version: Any = None # used to avoid full resyncs

class ClusterDiscoveryException(Exception):
    pass

class ErrorWatchEventException(ClusterDiscoveryException):
    pass

class ClusterDiscovery:
    """
    Cluster resources discovery - watches & publish events in cluster
    """

    # default time to wait between watch attemps
    RETRY_INTERVAL_SECONDS = 30

    def _create_watch_targets(self) -> Dict[str, WatchTarget]:
        """
        Creates watch targets - all pods, nodes & deployments.
        """
        return {
            "Pod": WatchTarget(self.client.list_pod_for_all_namespaces),
            "Node": WatchTarget(self.client.list_node),
            "Namespace": WatchTarget(self.client.list_namespace),
            "Deployment": WatchTarget(
                self.apps_api_client.list_deployment_for_all_namespaces,
            ),
        }

    def __init__(
            self,
            event_handler,
            api_client=None,
            retry_interval_seconds=RETRY_INTERVAL_SECONDS
    ):
        """
        :param event_handler: to write events to
        :param api_client: of the cluster to discover. If not given, using the
        default one.
        """
        self.i = 0
        self.event_handler = event_handler
        self.client = kubernetes_asyncio.client.CoreV1Api(api_client=api_client)
        self.version_client = kubernetes_asyncio.client.VersionApi(api_client=api_client)
        self.apps_api_client = kubernetes_asyncio.client.AppsV1Api(api_client=api_client)
        self.watch_targets = self._create_watch_targets()
        self.watch_tasks = []
        if retry_interval_seconds < 0:
            raise ValueError("Retry interval seconds must be bigger than 0")

        self.retry_interval_seconds = retry_interval_seconds


    def _update_resource_version(
            self,
            kind,
            target: WatchTarget,
            resource_version
    ):
        """
        Updates the resource version of given kind & watch targets.
        """
        self.watch_targets[kind].last_resource_version = resource_version


    async def _get_initial_list(self, kind, target):
        """
        Performs initial list of given watch target endpoint.
        """
        response = await target()
        for item in response.items:
            item.kind = kind
            kubernetes_event = WatchKubernetesEvent(
                WatchKubernetesEventType.ADDED,
                item.to_dict()
            )
            await self.event_handler(kubernetes_event)

        return response.metadata.resource_version


    async def _run_watch(self, kind, target, stream):
        """
        Runs the watch stream of given watch target and watch resource kind.
        """
        async for event in stream:
            try:
                event_type = event.get("type")
                if not event_type or event_type.lower() == "error":
                    raise ErrorWatchEventException("Received an error event")

                kubernetes_event = WatchKubernetesEvent.from_watch_dict(event)
                await self.event_handler(kubernetes_event)
                self._update_resource_version(
                    kind,
                    target,
                    kubernetes_event.get_resource_version()
                )
            except KubernetesEventException:
                logging.debug("Skipping invalid event")


    async def _start_watch(self, kind, target):
        """
        Watches given cluster endpoint.
        For each streamed event, creating KubernetesEvent and writing the
        event to the event handler. Ignoring invalid event object.
        """
        if not target.last_resource_version:
            # resource first time retrieval
            resource_version = await self._get_initial_list(kind, target.endpoint)
            self._update_resource_version(
                kind,
                target,
                resource_version
            )
        else:
            # continue watch from last preserved resource version
            resource_version = target.last_resource_version

        try:
            w = kubernetes_asyncio.watch.Watch()
            stream = w.stream(target.endpoint, resource_version=resource_version)
            await self._run_watch(kind, target, stream)
        except ClientError:
            # resource version timeout, restarting watch
            # from last preserved resource version
            await self._start_watch(kind, target)
        except ErrorWatchEventException:
            logging.debug("Restarting %s watch due to an error event", kind)
            self._update_resource_version(kind, target, None)
            await self._start_watch(kind, target)
        except asyncio.CancelledError:
            pass

    def _stop_all(self):
        """
        Stops all watch tasks
        """
        for task in self.discover_tasks:
            if not task.done():
                task.cancel()

    async def _collect_cluster_info(self):
        """
        Collects the cluster info
        """
        try:
            version = None
            try:
                version: str = (await self.version_client.get_code()).git_version
            except Exception as exception:
                logging.debug("Could not extract cluster version")
                logging.error(str(exception))
                logging.error(format_exc())
            try:
                data = {"version": version}
                kubernetes_event = KubernetesEvent(KubernetesEventType.CLUSTER, data)
                await self.event_handler(kubernetes_event)
            except KubernetesEventException:
                logging.debug("Failed to create cluster event")
                raise
        except asyncio.CancelledError:
            pass

    async def start(self):
        """
        Starts watch task per target (see _create_watch_targets) and runs
        more discovery tasks such as retrieving cluster level information.
        In case of watch resync issues, restarting all watches from the last
        preserved resource version.
        In case of other network issues, stopping all tasks and restarting
        after RETRY_INTERVAL_SECONDS.
        """
        try:
            await self._collect_cluster_info()
            self.discover_tasks = [
                asyncio.ensure_future(self._start_watch(kind, target))
                for kind, target in self.watch_targets.items()
            ]
            await asyncio.gather(
                *self.discover_tasks,
                loop = asyncio.get_event_loop()
            )
        except (socket.gaierror, ClientError):
            self.stop()
            logging.error(
                "Connection error, retrying in %d seconds",
                self.retry_interval_seconds
            )
            await asyncio.sleep(self.retry_interval_seconds)
            await self.start()
        except asyncio.CancelledError:
            self._stop_all()


    def stop(self):
        """
        Stops the cluster discovery.
        """
        # reset resource version for all watch targets
        for target in self.watch_targets.values():
             target.last_resource_version = None
        self._stop_all()

