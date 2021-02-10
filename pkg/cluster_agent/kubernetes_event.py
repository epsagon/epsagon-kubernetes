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
            return o.to_json()
        return super(KubernetesEventEncoder, self).default(o)


class KubernetesEventException(Exception):
    pass

class InvalidEventException(KubernetesEventException):
    pass

class KubernetesEventType(Enum):
    """
    Kubernetes event types parent class
    """
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    CLUSTER = "CLUSTER"


class KubernetesEvent:
    """
    Kubernetes event
    """
    EVENT_FIELDS = ("raw_object", "type")

    def __init__(self, event_type: KubernetesEventType, obj: Dict):
        """
        :param event_type:
        :param obj: the actual object the event related to
        """
        self.event_type = event_type
        self.obj = obj

    @classmethod
    def from_dict(cls, raw_data):
        """
        Instantiate a KubernetetEvent from a raw event dict
        """
        for field in cls.EVENT_FIELDS:
            if field not in raw_data:
                raise InvalidEventException(f"Missing `{field}` in event")
        obj = raw_data["raw_object"]
        event_type = raw_data["type"]
        if event_type not in (
            current_type.value for current_type in KubernetesEventType
        ):
            raise InvalidEventException(f"Unsupported `{event_type}` event type")
        return cls(KubernetesEventType(event_type), obj)

    def to_json(self):
        """
        Encode the kubernetes event as JSON
        """
        return json.dumps(
            {
                "type": self.event_type.value,
                "object": self.obj,
            },
            cls=DateTimeEncoder
        )

