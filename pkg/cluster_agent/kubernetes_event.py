"""
Kubernetes events
"""
import json
from typing import Dict
from enum import Enum
from encoders import DateTimeEncoder

class KubernetesEventEncoder(DateTimeEncoder):
    """
    JSON Encoder for kubernetes events
    """
    def default(self, o):  # pylint: disable=method-hidden
        """
        Overriding for specific serialization
        """
        if isinstance(o, KubernetesEvent):
            return json.dumps(o.to_dict(), cls=DateTimeEncoder)

        return super(KubernetesEventEncoder, self).default(o)


class KubernetesEventException(Exception):
    pass

class InvalidWatchEventException(KubernetesEventException):
    pass

class KubernetesEventType(Enum):
    """
    General kubernetes event types, used by Epsagon
    """
    CLUSTER = "CLUSTER"
    WATCH = "WATCH"


class WatchKubernetesEventType(Enum):
    """
    Kubernetes watch (from kubernetes apiserver) event types
    """
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class KubernetesEvent:
    """
    Abstract kubernetes event
    """

    def __init__(self, event_type: KubernetesEventType, data):
        """
        :param event_type:
        :param data: the actual event data
        """
        self.event_type = event_type
        self.data = data

    def get_formatted_payload(self):
        """
        Gets the kubernetes event data formatted.
        Inheriting classes can override this behaviour and format the payload
        as needed.
        By default, returns the raw data as given when initialized.
        """
        return self.data

    def to_dict(self):
        """
        Encode the kubernetes event as JSON
        """
        return  {
            "metadata": {
                "kind": self.event_type.value.lower(),
            },
            "payload": self.get_formatted_payload(),
        }

    def __eq__(self, other):
        """
        Checks equity by comparing the event type & data
        """
        return (
            type(self) == type(other) and
            self.event_type == other.event_type and
            self.data == other.data
        )

    def __hash__(self):
        """ gets the item hash """
        return hash(str(self.to_dict()))


class WatchKubernetesEvent(KubernetesEvent):
    """
    Kubernetes watch event
    """
    OBJECT_FIELD_KEY = "object"
    EVENT_FIELDS = (OBJECT_FIELD_KEY, "type")

    def __init__(
            self,
            watch_event_type: WatchKubernetesEventType,
            watched_obj: Dict
    ):
        """
        :param watch_event_type: kubernetes watch type
        :param watched_obj: the actual watched object the event related to
        """
        super().__init__(KubernetesEventType.WATCH, watched_obj)
        self.watch_event_type: WatchKubernetesEventType = watch_event_type

    @classmethod
    def from_watch_dict(cls, raw_data):
        """
        Instantiate a WatchKubernetesEvent from a raw watch event dict
        """
        for field in cls.EVENT_FIELDS:
            if field not in raw_data:
                raise InvalidWatchEventException(f"Missing `{field}` in event")

        obj = raw_data[cls.OBJECT_FIELD_KEY].to_dict()
        event_type = raw_data["type"]
        if event_type not in (
            current_type.value for current_type in WatchKubernetesEventType
        ):
            raise InvalidWatchEventException(
                f"Unsupported `{event_type}` watch event type"
            )
        return cls(WatchKubernetesEventType(event_type), obj)

    def get_resource_version(self):
        """
        Gets the watch kubernetes object resource version.
        If cannot extract resource version, returns None
        """
        return self.data.get("metadata", {}).get("resource_version")

    def get_formatted_payload(self):
        """
        Gets the watch kubernetes event data formatted.
        """
        return {
            "type": self.watch_event_type.value.lower(),
            "object": super().get_formatted_payload()
        }

    def __eq__(self, other):
        """
        Checks equity by comapring the data and the watch specific event type
        """
        return (
            type(self) == type(other) and
            self.watch_event_type == other.watch_event_type and
            self.data == other.data
        )

    def __hash__(self):
        """ gets the item hash """
        return hash(str(self.to_dict()))
