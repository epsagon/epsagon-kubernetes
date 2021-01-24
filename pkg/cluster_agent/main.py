"""
Main module
"""
import time
import logging
from os import getenv
from datetime import datetime, timezone
from traceback import format_exc
from kubernetes import config, client
from cluster_scanner import ClusterScanner

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

    scanner = ClusterScanner(EPSAGON_TOKEN, CLUSTER_NAME, collector_url=COLLECTOR_URL)
    logging.debug("cluster scanner initialized")
    while True:
        try:
            update_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            logging.debug("Scanning cluster...")
            scanner.scan(update_time)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
