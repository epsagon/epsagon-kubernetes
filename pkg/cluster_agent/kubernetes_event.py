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
    Kubernetes event types
    """
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"

class KubernetesEvent:
    """
    Kubernetes event
    """

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
        if "object" not in raw_data:
            raise InvalidEventException("Missing `object` in event")
        obj = raw_data["object"]
        return cls(KubernetesEventType(raw_data.pop("type")), obj)

    def to_json(self):
        """
        Encode the kubernetes event as JSON
        """
        return json.dumps(
            {
                "type": self.event_type.value,
                "object": self.obj.to_dict(),
            },
            cls=DateTimeEncoder
        )

