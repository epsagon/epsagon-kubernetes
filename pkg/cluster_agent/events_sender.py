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

    def __init__(self, client, url):
        """
        :param client: used to send events by
        :param url: to send the events to
        """
        self.client = client
        self.url = url

    async def send_events(self, events: List[KubernetesEvent]):
        """
        Sends the given events
        """
        data = json.dumps(events, cls=KubernetesEventEncoder)
        compressed_data = base64.b64encode(zlib.compress(data.encode("utf-8")))
        await self.client.post(self.url, compressed_data)
