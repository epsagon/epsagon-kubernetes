from asynctest.mock import patch, MagicMock
from kubernetes_event import KubernetesEvent, KubernetesEventType

FAKE_TIMESTAMP = 12345


@patch("time.time_ns", MagicMock(return_value=FAKE_TIMESTAMP))
def test_cluster_event_dict_structure():
    event_data = {"version": "1.19.0"}
    event = KubernetesEvent(KubernetesEventType.CLUSTER, event_data)
    expected_event_dict = {
        "metadata": {
            "kind": KubernetesEventType.CLUSTER.value,
            "timestamp": FAKE_TIMESTAMP,
        },
        "payload": event_data,
    }
    assert event.to_dict() == expected_event_dict
