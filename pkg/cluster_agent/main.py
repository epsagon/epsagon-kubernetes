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
CLUSTER_NAME = getenv("EPSAGON_CLUSTER_NAME")
logging.getLogger().setLevel(
    logging.DEBUG if (
        getenv("EPSAGON_DEBUG", "").lower() == 'true'
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
    scanner = ClusterScanner(EPSAGON_TOKEN, CLUSTER_NAME)
    while True:
        try:
            update_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            scanner.scan(update_time)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
