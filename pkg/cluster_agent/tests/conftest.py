"""
Common test settings
"""
import asyncio
from asynctest.mock import MagicMock

# monkey patch MagicMock
async def async_magic():
    pass

MagicMock.__await__ = lambda x: async_magic().__await__()


async def run_coroutines_with_timeout(
        coroutines,
        verify_tasks_finished=True,
        timeout=1
):
    """
    Convert coroutines to tasks and runs them with a given timeout.
    :param coroutines: to run
    :param verify_coroutines_finished: verifies all the given coroutines
    finished running
    :param timeout: in seconds, to wait for all the coroutines to finish.
    :return: a list of the corresponding coroutines created tasks
    """
    tasks = [asyncio.ensure_future(coroutine) for coroutine in coroutines]
    finished, _ = await asyncio.wait(tasks, timeout=timeout)
    if verify_tasks_finished:
        assert len(finished) == len(tasks)

    return tasks
