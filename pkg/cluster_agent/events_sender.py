"""
Kubernetes Events sender
"""
import json
import base64
import zlib
from typing import List
from kubernetes_event import KubernetesEvent, KubernetesEventEncoder

class EventsSender:
    """
    Events sender
    """

    def __init__(self, client, url, cluster_name, epsagon_token):
        """
        :param client: used to send events by
        :param url: to send the events to
        """
        self.client = client
        self.url = url
        self.epsagon_token = epsagon_token
        self.cluster_name = cluster_name

    async def send_events(self, events: List[KubernetesEvent]):
        """
        Sends the given events
        """
        if not events:
            return

        data = json.dumps(
            {
                "epsagon_token": self.epsagon_token,
                "cluster_name": self.cluster_name,
                "events": events
            },
            cls=KubernetesEventEncoder
        )
        compressed_data = base64.b64encode(zlib.compress(data.encode("utf-8")))
        await self.client.post(self.url, compressed_data)
