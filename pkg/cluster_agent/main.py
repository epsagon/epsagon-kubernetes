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
logging.getLogger().setLevel(logging.INFO)


def main():
    #if not EPSAGON_TOKEN:
    #    raise Exception("missing epsagon token!")
    config.load_incluster_config()
    while True:
        try:
            update_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            ClusterScanner(EPSAGON_TOKEN).scan(update_time)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
