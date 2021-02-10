"""
Main module - runs collector & cluster discovery
"""
import time
import logging
import asyncio
import socket
from os import getenv
from datetime import datetime, timezone
from traceback import format_exc
from aiohttp import client_exceptions
from kubernetes_asyncio import config, client
from cluster_discovery import ClusterDiscovery
from events_manager import InMemoryEventsManager
from events_sender import EventsSender
from epsagon_client import EpsagonClient, EpsagonClientException
from forwarder import Forwarder

RESTART_WAIT_TIME_SECONDS = 300
EPSAGON_TOKEN = getenv("EPSAGON_TOKEN")
CLUSTER_NAME = getenv("EPSAGON_CLUSTER_NAME")
COLLECTOR_URL = getenv(
    "EPSAGON_COLLECTOR_URL",
    "https://collector.epsagon.com/resources/v1"
)
IS_DEBUG_MODE = getenv("EPSAGON_DEBUG", "").lower() == "true"
DEFAULT_COLLECTOR_WORKERS_COUNT = 3
logging.getLogger().setLevel(logging.DEBUG if IS_DEBUG_MODE else logging.INFO)

def _cancel_tasks(tasks):
    """
    Cancels the given tasks
    """
    for task in tasks:
        if not task.cancelled():
            task.cancel()


async def run():
    """
    Runs the cluster discovery & forwarder.
    """
    events_manager = InMemoryEventsManager()
    epsagon_client = await EpsagonClient.create(EPSAGON_TOKEN)
    events_sender = EventsSender(epsagon_client, COLLECTOR_URL)
    cluster_discovery = ClusterDiscovery(events_manager.write_event)
    forwarder = Forwarder(
        events_manager,
        events_sender,
        max_workers=DEFAULT_COLLECTOR_WORKERS_COUNT
    )
    while True:
        try:
            tasks = [
                asyncio.ensure_future(forwarder.start()),
                asyncio.ensure_future(cluster_discovery.start())
            ]
            await asyncio.gather(*tasks)
        except (
                client_exceptions.ClientError,
                socket.gaierror,
                ConnectionRefusedError,
                EpsagonClientException
        ):
            logging.error(
                "Connection error, restarting agent in %d seconds",
                RESTART_WAIT_TIME_SECONDS
            )
            _cancel_tasks(tasks)
            events_manager.clean()
            await asyncio.sleep(RESTART_WAIT_TIME_SECONDS)
        except Exception as exception:
            logging.error(str(exception))
            logging.error(format_exc())
            logging.info("Agent is exiting due to an unexpected error")
            _cancel_tasks(tasks)
            await psagon_client.close()
            break


def main():
    if not EPSAGON_TOKEN:
        logging.error(
            "Missing Epsagon token. "
            "Make sure to configure EPSAGON_TOKEN in cluster_agent_deployment.yaml"
        )
        return

    if not CLUSTER_NAME:
        logging.error(
            "Missing cluster name. "
            "Make sure to configure EPSAGON_CLUSTER_NAME in cluster_agent_deployment.yaml"
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
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run())
    loop.close()

if __name__ == "__main__":
    main()
