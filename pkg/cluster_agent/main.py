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
from logger_configurer import LoggerConfigurer

RESTART_WAIT_TIME_SECONDS = 60
EPSAGON_TOKEN = os.getenv("EPSAGON_TOKEN")
CLUSTER_NAME = os.getenv("EPSAGON_CLUSTER_NAME")
COLLECTOR_URL = os.getenv(
    "EPSAGON_COLLECTOR_URL",
    "https://collector.epsagon.com/resources/v1"
)
SHOULD_COLLECT_RESOURCES = os.getenv("EPSAGON_COLLECT_RESOURCES", "TRUE").upper() == "TRUE"
SHOULD_COLLECT_EVENTS = os.getenv("EPSAGON_COLLECT_EVENTS", "FALSE").upper() == "TRUE"
EPSAGON_CONF_DIR = "/etc/epsagon"
IS_DEBUG_FILE_PATH = f"{EPSAGON_CONF_DIR}/epsagon_debug"

def _get_log_file_name():
    """
    Gets the log file name, according to the configured collected data
    """
    if SHOULD_COLLECT_RESOURCES and SHOULD_COLLECT_EVENTS:
        return "resources_and_events_log"
    if SHOULD_COLLECT_RESOURCES:
        return "resources_log"
    return "events_log"

LOG_FILE_PATH = f"{os.getenv('HOME', '/tmp')}/{_get_log_file_name()}"
LOG_FORMAT = "%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s"
LOGGER_CONFIGURER = LoggerConfigurer(LOG_FORMAT, LOG_FILE_PATH)


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


def _reload_handler():
    """
    Reload configuration handler - reconfigures the main logger according
    to the current debug mode.
    """
    LOGGER_CONFIGURER.update_logger_level(_is_debug_mode())


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
                LOGGER_CONFIGURER.update_logger_level(debug_mode)
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
        should_collect_resources=SHOULD_COLLECT_RESOURCES,
        should_collect_events=SHOULD_COLLECT_EVENTS,
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
    LOGGER_CONFIGURER.configure_logger(is_debug)
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
