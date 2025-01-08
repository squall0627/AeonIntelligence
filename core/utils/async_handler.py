import asyncio
from asyncio import Future
from typing import Coroutine, Any


def async_task(func: Coroutine, *, name=None, callback=None, loop=None) -> asyncio.Task:
    """
    Creates an asynchronous task to execute the given coroutine, optionally assigning it a
    name, callback, and event loop.

    This function ensures that the correct event loop is used to schedule the task. If no
    loop is provided and no running loop is detected, a new event loop is created, set, and
    used for task execution. A callback, if provided, is assigned to be executed upon the
    completion of the task.

    :param func: A coroutine object representing the asynchronous operation to be executed.
    :param name: A string or None representing the optional name to assign to the task.
    :param callback: An optional callable that will be called when the task is done.
        The callback should accept the completed task as its only argument.
    :param loop: An asyncio-compatible event loop to schedule the task on.
        If None, the function will attempt to detect or create an appropriate loop.
    :return: An asyncio.Task object representing the created async task.
    :rtype: asyncio.Task
    :raises RuntimeError: If no event loop is running and cannot be created.
    """
    if loop is not None:
        task = loop.create_task(func, name=name)
    else:
        try:
            loop = asyncio.get_event_loop()
            # Ensure the loop is running
            if not loop.is_running():
                raise RuntimeError("Loop not running")

            # If there's a running loop, create a task
            task = asyncio.create_task(func, name=name)
        except RuntimeError:
            # If no loop or loop isn't running, create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Use the new loop to create the task
            task = loop.create_task(func, name=name)

    # Attach the callback if provided
    if callback:
        task.add_done_callback(callback)

    return task


def async_tasks(*funcs, callback=None) -> list[asyncio.Task]:
    """
    Executes multiple asynchronous functions concurrently, creating
    tasks for each function. Optionally accepts a callback function
    to execute upon the completion of individual tasks.

    :param funcs: The collection of asynchronous functions to execute.
    :type funcs: callable
    :param callback: Optional callback function to be executed after
        each task completes.
    :type callback: callable or None
    :return: A list of `asyncio.Task` objects representing the scheduled
        tasks for the provided asynchronous functions.
    :rtype: list[asyncio.Task]
    """
    try:
        loop = asyncio.get_event_loop()
        # Ensure the loop is running
        if not loop.is_running():
            raise RuntimeError("Loop not running")

        tasks = []
        for func in funcs:
            tasks.append(async_task(func, callback=callback))
        return tasks

    except RuntimeError:
        # If no loop or loop isn't running, create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Similar error handling ensures loop is running
        tasks = []
        for func in funcs:
            tasks.append(async_task(func, callback=callback, loop=loop))
        return tasks


def sync_run_task(func: Future | Coroutine) -> Any:
    """
    Synchronously runs an asynchronous task.

    This function accepts either a `Future` or a `Coroutine` object and executes it
    to completion in the event loop. If no event loop is currently available, it creates
    a new one and sets it as the active event loop. The function blocks until the
    asynchronous task is completed and returns its result.

    :param func: The asynchronous task to run. It can be either a `Future` or `Coroutine`.
    :type func: Future | Coroutine
    :return: The result of the completed asynchronous task.
    :rtype: Any
    """
    try:
        loop = asyncio.get_event_loop()  # Get current loop
    except RuntimeError:
        # If no loop is available, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the async function until completion
    return loop.run_until_complete(func)


def sync_run_tasks(*tasks, return_exceptions=False) -> (list[Any], list[Exception]):
    """
    Synchronously runs a collection of asynchronous tasks, and optionally separates successful results from exceptions.

    This function schedules the supplied asynchronous tasks to run concurrently and waits for their
    completion. It can also categorize the outcomes into successful results and exceptions based
    on the `return_exceptions` flag. This allows handling of results at higher granularity if required.

    :param tasks: The asynchronous tasks to be executed concurrently.
    :type tasks: AsyncIterable[Any]
    :param return_exceptions: A flag indicating whether exceptions should be separated from results.
                              If set to True, the function returns two lists (successes and exceptions).
    :type return_exceptions: bool
    :return: If `return_exceptions` is False, returns a single list of results. If `return_exceptions`
             is True, returns a tuple containing a list of successful results and a list of exceptions.
    :rtype: Union[list[Any], tuple[list[Any], list[Exception]]]
    """
    results = sync_run_task(asyncio.gather(*tasks, return_exceptions=return_exceptions))
    if return_exceptions:
        successes = [x for x in results if not isinstance(x, Exception)]
        exceptions = [x for x in results if isinstance(x, Exception)]
        return successes, exceptions
    else:
        return results, []
