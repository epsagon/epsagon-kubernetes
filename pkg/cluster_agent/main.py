"""
Main module
"""
import time
import json
import logging
from os import getenv
from typing import Dict
from datetime import datetime, timezone
from traceback import format_exc
from kubernetes import config, client
from requests import post, exceptions as requests_exceptions
from requests.auth import HTTPBasicAuth
from encoders import DateTimeEncoder
from cluster_scanner import ClusterScanner, ScanResult

SCAN_INTERVAL_SECONDS = 60
EPSAGON_TOKEN = getenv("EPSAGON_TOKEN")
DEFAULT_CLUSTER_NAME = "K8s Cluster"
CLUSTER_NAME = getenv("EPSAGON_CLUSTER_NAME", DEFAULT_CLUSTER_NAME)
COLLECTOR_URL = getenv(
    "EPSAGON_COLLECTOR_URL",
    "https://collector.epsagon.com/resources/v1"
)
IS_DEBUG_MODE = getenv("EPSAGON_DEBUG", "").lower() == "true"
logging.getLogger().setLevel(logging.DEBUG if IS_DEBUG_MODE else logging.INFO)


def _send_to_epsagon(data: Dict):
    """
    Sends data to Epsagon
    """
    try:
        post(
            COLLECTOR_URL,
            data=json.dumps(data, cls=DateTimeEncoder),
            headers={"Content-Type": "application/json"},
            auth=HTTPBasicAuth(EPSAGON_TOKEN, ""),
        )
        logging.debug("data sent.")
    except requests_exceptions.RequestException as err:
        logging.error(
            "Failed to send data to Epsagon - %s: %s",
            str(err),
            format_exc()
        )


def _handle_scan_result(scan_result: ScanResult, update_time):
    """
    handle scan result - parse and sends to Epsagon
    """
    data = {
        "update_time": update_time.timestamp(),
        "epsagon_token": EPSAGON_TOKEN,
        "cluster": {
            "name": CLUSTER_NAME,
        }
    }
    if scan_result.cluster_version:
        data["cluster"]["version"] = scan_result.cluster_version
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
    logging.info("Sending data to Epsagon")
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
    _send_to_epsagon(data)


def main():
    if not EPSAGON_TOKEN:
        logging.error(
            "Missing Epsagon token. "
            "Make sure to configure EPSAGON_TOKEN in cluster_agent_deployment.yaml"
        )
        return

    config.load_incluster_config()
    logging.info("Loaded cluster config")
    if IS_DEBUG_MODE:
        loaded_conf = client.configuration.Configuration.get_default_copy()
        logging.debug(
            "Loaded cluster configuration:\nHost: %s\n"
            "Using SSL Cert? %s\nUsing API token? %s",
            loaded_conf.host,
            bool(loaded_conf.ssl_ca_cert),
            bool(loaded_conf.api_key)
        )

    scanner = ClusterScanner()
    logging.debug("cluster scanner initialized")
    while True:
        try:
            update_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            logging.debug("Scanning cluster...")
            scan_result: ScanResult = scanner.scan()
            if not scan_result.cluster_version:
                logging.error(
                    "Failed to scan cluster. Will retry in %s",
                    SCAN_INTERVAL_SECONDS
                )
            else:
                _handle_scan_result(scan_result, update_time)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
