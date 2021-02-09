"""
Cluster discovery - watch & publish events in the cluster
"""
import asyncio
import logging
import socket
import kubernetes_asyncio
from aiohttp.client_exceptions import ClientError
from kubernetes_event import (
    KubernetesEvent,
    KubernetesEventException,
    KubernetesEventType,
)

class ClusterDiscovery:
    """
    Cluster resources discovery - watches & publish events in cluster
    """

    # default time to wait between watch attemps
    RETRY_INTERVAL_SECONDS = 30

    def _create_watch_targets(self):
        """
        Creates watch targets - all pods, nodes & deployments.
        """
        return (
            self.client.list_pod_for_all_namespaces,
            self.client.list_node,
            self.apps_api_client.list_deployment_for_all_namespaces,
        )

    def __init__(self, event_handler, api_client=None):
        """
        :param event_handler: to write events to
        :param api_client: of the cluster to discover. If not given, using the
        default one.
        """
        self.event_handler = event_handler
        self.client = kubernetes_asyncio.client.CoreV1Api(api_client=api_client)
        self.version_client = kubernetes_asyncio.client.VersionApi(api_client=api_client)
        self.apps_api_client = kubernetes_asyncio.client.AppsV1Api(api_client=api_client)
        self.watch_targets = self._create_watch_targets()
        self.watch_tasks = []

    async def _start_watch(self, target):
        """
        Watches given cluster endpoint.
        For each streamed event, creating KubernetesEvent and writing the
        event to the event handler. Ignoring invalid event object.
        """
        w = kubernetes_asyncio.watch.Watch()
        try:
            async for event in w.stream(target):
                try:
                    kubernetes_event = KubernetesEvent.from_dict(event)
                    await self.event_handler(kubernetes_event)
                except KubernetesEventException:
                    logging.debug("Skipping invalid event")
        except asyncio.CancelledError:
            pass

    def _stop_all(self):
        """
        Stops all watch tasks
        """
        for task in self.discover_tasks:
            if not task.cancelled():
                task.cancel()

    async def _get_cluster_version(self):
        """
        Gets the cluster version
        """
        try:
            version: str = (await self.version_client.get_code()).git_version
            try:
                data = { "version": version }
                kubernetes_event = KubernetesEvent(KubernetesEventType.NEW_CLUSTER, data)
                await self.event_handler(kubernetes_event)
            except KubernetesEventException:
                logging.debug("Failed to retrieve cluster version")
        except asyncio.CancelledError:
            pass

    async def start(self):
        """
        Starts watch task per target (see _create_watch_targets).
        In case of network issues, stopping all tasks and restarting
        after RETRY_INTERVAL_SECONDS.
        """
        try:
            self.discover_tasks = [
                asyncio.ensure_future(self._start_watch(target))
                for target in self.watch_targets
            ]
            self.discover_tasks.append(
                asyncio.ensure_future(self._get_cluster_version())
            )
            await asyncio.gather(
                *self.discover_tasks,
                loop = asyncio.get_event_loop()
            )
        except (ClientError, socket.gaierror):
            self._stop_all()
            wait_time = self.RETRY_INTERVAL_SECONDS
            logging.error("Connection error, retrying in %d seconds", wait_time)
            await asyncio.sleep(wait_time)
            await self.start()
        except asyncio.CancelledError:
            self._stop_all()


    def stop(self):
        """
        Stops the cluster discovery
        """
        self._stop_all()

