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
        self.events_count = 0

    async def send_events(self, events: List[KubernetesEvent]):
        """
        Sends the given events
        """
        if not events:
            return
        self.events_count += len(events)
        print(f"Total events so far: {self.events_count}")
        #for event in events:
        #print(event.to_dict())
        print(f"going to send {len(events)} events")
        events_json = json.dumps(events, cls=KubernetesEventEncoder)
        #compressed_data = base64.b64encode(
        #zlib.compress(events_json.encode("utf-8"))
        #).decode("utf-8")
        data_to_send = {
            "epsagon_token": self.epsagon_token,
            "cluster_name": self.cluster_name,
            "data": events_json,
        }


        await self.client.post(self.url, json.dumps(data_to_send))
