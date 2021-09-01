"""
Main module - runs collector & cluster discovery
"""
import time
import logging
import asyncio
import socket
import os
import signal
import aiofiles
from datetime import datetime, timezone
from traceback import format_exc
from aiohttp import client_exceptions
from kubernetes_asyncio import config, client
from cluster_discovery import ClusterDiscovery
from events_manager import InMemoryEventsManager
from events_sender import EventsSender
from epsagon_client import EpsagonClient, EpsagonClientException
from forwarder import Forwarder

RESTART_WAIT_TIME_SECONDS = 60
EPSAGON_TOKEN = os.getenv("EPSAGON_TOKEN")
CLUSTER_NAME = os.getenv("EPSAGON_CLUSTER_NAME")
COLLECTOR_URL = os.getenv(
    "EPSAGON_COLLECTOR_URL",
    "https://collector.epsagon.com/resources/v1"
)
EPSAGON_CONF_DIR = "/etc/epsagon"
IS_DEBUG_FILE_PATH = f"{EPSAGON_CONF_DIR}/epsagon_debug"
LOG_FORMAT = "%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s"


async def _is_debug_mode():
    """
    Checks whether the agent runs in debug mode.
    Checks IS_DEBUG_FILE_PATH boolean value. In case of error reading the
    file content, using the EPSAGON_DEBUG env var.
    """
    try:
        async with aiofiles.open(IS_DEBUG_FILE_PATH, "r") as reader:
            return (await reader.read()).lower() == "true"
    except Exception: # pylint: disable=broad-except
        pass

    return os.getenv("EPSAGON_DEBUG", "").lower() == "true"


def _configure_logging(is_debug: bool):
    """
    Configures the main logger.
    :param is_debug: indicates whether to set debugging
    """
    # required for basicConfig to override current logger settings
    logging.getLogger().handlers = []
    logging.basicConfig(
        format=LOG_FORMAT,
        level=logging.DEBUG if is_debug else logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def _reload_handler():
    """
    Reload configuration handler - reconfigures the main logger according
    to the current debug mode.
    """
    _configure_logging(_is_debug_mode())


def _cancel_tasks(tasks):
    """
    Cancels the given tasks
    """
    for task in tasks:
        if not task.done():
            task.cancel()


async def _epsagon_conf_watcher(initial_debug_mode: bool):
    """
    Watches for changes in the epsagon conf.
    If debug mode has been changed, updates the main logger
    with the new logging level.
    """
    debug_mode = initial_debug_mode
    while True:
        try:
            current_debug_mode = await _is_debug_mode()
            if debug_mode != current_debug_mode:
                debug_mode = current_debug_mode
                _configure_logging(debug_mode)
        except Exception: # pylint: disable=broad-except
            pass
        await asyncio.sleep(120)


async def run(is_debug_mode):
    """
    Runs the cluster discovery & forwarder.
    """
    asyncio.create_task(_epsagon_conf_watcher(is_debug_mode))
    events_manager = InMemoryEventsManager()
    epsagon_client = await EpsagonClient.create(EPSAGON_TOKEN)
    events_sender = EventsSender(
        epsagon_client,
        COLLECTOR_URL,
        CLUSTER_NAME,
        EPSAGON_TOKEN
    )
    cluster_discovery = ClusterDiscovery(
        events_manager.write_event,
        should_collect_resources=(os.getenv("EPSAGON_COLLECT_RESOURCES", "TRUE").upper() == "TRUE"),
        should_collect_events=(os.getenv("EPSAGON_COLLECT_EVENTS", "FALSE").upper() == "TRUE"),
    )
    forwarder = Forwarder(
        events_manager,
        events_sender
    )
    while True:
        try:
            tasks = [
                asyncio.create_task(forwarder.start()),
                asyncio.create_task(cluster_discovery.start())
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
            await epsagon_client.close()
            break


def main():
    is_debug = asyncio.run(_is_debug_mode())
    _configure_logging(is_debug)
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
    if is_debug:
        loaded_conf = client.configuration.Configuration.get_default_copy()
        logging.debug(
            "Loaded cluster configuration:\nHost: %s\n"
            "Using SSL Cert? %s\nUsing API token? %s",
            loaded_conf.host,
            bool(loaded_conf.ssl_ca_cert),
            bool(loaded_conf.api_key)
        )
    loop = asyncio.new_event_loop()
    loop.add_signal_handler(signal.SIGHUP, _reload_handler)
    loop.run_until_complete(run(is_debug))
    loop.close()

if __name__ == "__main__":
    main()
