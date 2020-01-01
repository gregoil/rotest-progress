"""Utilities for rotest-progress bar."""
# pylint: disable=bare-except,global-statement
import sys
import time
import requests
import threading

import tqdm
import colorama
from rotest.core.models.case_data import TestOutcome


OUTCOME_TO_COLOR = {None: colorama.Fore.WHITE,
                    TestOutcome.SUCCESS: colorama.Fore.GREEN,
                    TestOutcome.ERROR: colorama.Fore.RED,
                    TestOutcome.EXPECTED_FAILURE: colorama.Fore.CYAN,
                    TestOutcome.FAILED: colorama.Fore.LIGHTRED_EX,
                    TestOutcome.SKIPPED: colorama.Fore.YELLOW,
                    TestOutcome.UNEXPECTED_SUCCESS: colorama.Fore.CYAN}


CURRENT_FORMAT = "{l_bar}{bar}| {n:.0f}/{total:.0f} seconds{postfix}"
UNKNOWN_FORMAT = "{l_bar}%%s{bar}%s| ? %%s{postfix}" % colorama.Fore.RESET
FULL_FORMAT = "{l_bar}%%s{bar}%s| {n:.0f}/{total:.0f} %%s{postfix}" % \
                                                            colorama.Fore.RESET


class DummyFile(object):
    """Tqdm wrapper for a file descriptor."""
    def __init__(self, stream):
        self.stream = stream
        self.encoding = stream.encoding

    def write(self, string):
        """Write using tqdm instead of the file."""
        tqdm.tqdm.write(string, file=self.stream, end="")

    def flush(self):
        """Flush the stream."""
        self.stream.flush()

NO_CONNECTION = False
STATISTICS_CACHE = {}
def get_statistics(test):
    """Try to get the statistics of a test.

    Args:
        test (AbstractTest): test instance to find its duration.

    Returns:
        number: average duration of the test or None if couldn't get it.
    """
    global NO_CONNECTION
    global STATISTICS_CACHE
    if not test.resource_manager or NO_CONNECTION:
        return None

    if test.data.name in STATISTICS_CACHE:
        return STATISTICS_CACHE[test.data.name]

    try:
        stats = test.resource_manager.get_statistics(test.data.name)
        STATISTICS_CACHE[test.data.name] = stats['avg']
        return stats['avg']

    except requests.exceptions.ConnectionError:
        NO_CONNECTION = True
        return None

    except:  # noqa
        return None


TRACER_EVENT = threading.Event()
WRAPPED_SETTRACE = False


def calculate_expected_time(root):
    print("Calculating tests average time...")
    recursive_calculate_time(root)
    print("Done calculating!")

def recursive_calculate_time(test):
    if hasattr(test, "_expected_time"):
        return

    if test.IS_COMPLEX:
        test._expected_time = len(list(test))
        for sub_test in test:
            recursive_calculate_time(sub_test)

    else:
        avg_time = get_statistics(test)
        if avg_time:
            test.logger.debug("%s avg runtime: %s", test.data.name, avg_time)
            test._expected_time = int(avg_time)

        else:
            test.logger.debug("No statistics for %s", test.data.name)
            test._expected_time = None


def create_tree_bar(test):
    """Create progress bar for a test in an hierarchical form."""
    desc = test.parents_count * '| ' + test.data.name
    unit_scale = False
    if test.IS_COMPLEX:
        total = test._expected_time

    else:
        avg_time = test._expected_time
        if avg_time:
            total = int(avg_time) * 10
            unit_scale = 0.1

        else:
            total = 1
            desc += " (No statistics)"

    test.progress_bar = tqdm.trange(total, desc=desc, unit_scale=unit_scale,
                                    position=test.identifier, leave=True,
                                    bar_format=get_format(test,
                                                          colorama.Fore.WHITE))
    test.progress_bar.finish = False
    test.progress_bar.start = False
    return test.progress_bar


def create_current_bar(test):
    """Create progress bar for a test in a single line."""
    index = 0
    total_tests = 0
    for sibling in test.parent:
        total_tests += 1

        if sibling is test:
            index = total_tests

    desc = "({} / {} in parent) {}".format(index,
                                           total_tests,
                                           test.data.name)

    avg_time = test._expected_time
    if avg_time:
        total = int(avg_time)

    else:
        total = 1
        desc += " (No statistics)"

    test.progress_bar = tqdm.trange(total*10, desc=desc, leave=False,
                                    position=1, unit_scale=0.1,
                                    bar_format=CURRENT_FORMAT)
    test.progress_bar.finish = False
    test.progress_bar.start = False
    return test.progress_bar


def get_format(test, color):
    """Return a bar formatter for a test in the given color."""
    if not hasattr(test, '_expected_time'):
        return UNKNOWN_FORMAT % (color, 'seconds')

    if test.IS_COMPLEX:
        return FULL_FORMAT % (color, 'tests')

    return FULL_FORMAT % (color, 'seconds')


def get_test_outcome(test):
    if hasattr(test.data, 'exception_type'):
        return test.data.exception_type

    else:
        if test.data.success is True:
            return TestOutcome.SUCCESS

        elif test.data.success is False:
            return TestOutcome.FAILED

    return None


def set_color(test):
    """Change the color of the progress bar for the given test."""
    color = OUTCOME_TO_COLOR[get_test_outcome(test)]
    test.progress_bar.bar_format = get_format(test, color)


def go_over_tests(test, use_color):
    """Iterate over test and sub-tests.

    Args:
        test (AbstractTest): Test or suite to iterate over.
        use_color (bool): whether to use colors in the progress bar.
    """
    if test.IS_COMPLEX:
        for index, sub_test in zip(test.progress_bar, test):
            go_over_tests(sub_test, use_color)
            if use_color and index == len(list(test)) - 1:
                set_color(test)

    else:
        for index in test.progress_bar:
            if not test.progress_bar.finish:
                time.sleep(0.1)
                if index == test.progress_bar.total - 1:
                    while not test.progress_bar.finish:
                        time.sleep(0.2)

                while not test.progress_bar.start or TRACER_EVENT.is_set():
                    time.sleep(0.2)

            if use_color and index == test.progress_bar.total - 1:
                set_color(test)


def wrap_settrace():
    """Wrap sys.settrace to apply or undo pause for the bars."""
    global WRAPPED_SETTRACE
    if not WRAPPED_SETTRACE:
        WRAPPED_SETTRACE = True
        old_settrace = sys.settrace

        def event_on_trace(function):
            """Wrapped settrace, sets or clears the pause flag for bars."""
            if function is None:
                TRACER_EVENT.clear()
            else:
                TRACER_EVENT.set()

            old_settrace(function)

        sys.settrace = event_on_trace
