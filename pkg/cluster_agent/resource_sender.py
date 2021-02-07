"""
K8s Resource sender
"""
import json
import logging
from typing import Dict
from datetime import datetime
from traceback import format_exc
from requests import post, exceptions as requests_exceptions
from requests.auth import HTTPBasicAuth
from encoders import DateTimeEncoder
from cluster_scanner import ResourceScanResult

def _resource_scan_result_to_dict(
        scan_result: ResourceScanResult,
        cluster_name: str,
        update_time: datetime
) -> Dict:
    """
    Parses resource scan result and formats it to a dict to be sent to Epsagon
    """
    data = {
        "update_time": update_time.timestamp(),
        "cluster": {
            "name": cluster_name,
            "version": scan_result.cluster_version,
        }
    }

    if scan_result.nodes:
        data["resources"] = [
            item.to_dict()
            for item in (
                    scan_result.nodes +
                    scan_result.pods +
                    scan_result.deployments
            )
        ]
    if scan_result.amazon_cw_data:
        data["cw_configmap"] = scan_result.amazon_cw_data
    logging.debug(
        "Cluster version %s\nNodes count: %s\n"
        "Pods count: %s\nDeployments count: %s\nTotal resources count: %s",
        (
            scan_result.cluster_version
            if scan_result.cluster_version else "Unknown"
        ),
        len(scan_result.nodes),
        len(scan_result.pods),
        len(scan_result.deployments),
        len(data["resources"])
    )
    return data


class ResourceSender:
    """
    A class to handle resource scan results - formats and sends
    the result to Epsagon
    """
    def __init__(self, epsagon_token: str, collector_url: str):
        self.epsagon_token = epsagon_token
        self.collector_url = collector_url

    def send_resource_scan_result(
            self,
            data: ResourceScanResult,
            cluster_name: str,
            update_time: datetime
    ):
        """
        Parses & sends resource scan result to Epsagon
        """
        data_to_send = _resource_scan_result_to_dict(data, cluster_name, update_time)
        data_to_send["epsagon_token"] = self.epsagon_token
        logging.debug("Sending data to Epsagon")
        try:
            post(
                self.collector_url,
                data=json.dumps(data_to_send, cls=DateTimeEncoder),
                headers={"Content-Type": "application/json"},
                auth=HTTPBasicAuth(self.epsagon_token, ""),
            )
            logging.debug("data sent.")
        except requests_exceptions.RequestException as err:
            logging.error(
                "Failed to send data to Epsagon - %s: %s",
                str(err),
                format_exc()
            )
