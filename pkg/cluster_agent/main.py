"""
Main module
"""
import time
import logging
from os import getenv
from datetime import datetime, timezone
from traceback import format_exc
from kubernetes import client, config
from cluster_scanner import ClusterScanner

SCAN_INTERVAL_SECONDS = 60
EPSAGON_TOKEN = getenv("EPSAGON_TOKEN")
CLUSTER_NAME = getenv("CLUSTER_NAME")
logging.getLogger().setLevel(
    logging.DEBUG if (
        getenv("DEBUG_MODE", "").lower() == 'true'
    )
    else logging.INFO
)


def main():
    if not EPSAGON_TOKEN:
        logging.error("Missing epsagon token!")
        return
    if not CLUSTER_NAME:
        logging.error("Missing cluster name!")
        return

    config.load_incluster_config()
    while True:
        try:
            update_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            ClusterScanner(EPSAGON_TOKEN, CLUSTER_NAME).scan(update_time)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
