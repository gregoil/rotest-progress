""""""
import sys
import time
import threading

import tqdm
import colorama
from rotest.core.models.case_data import TestOutcome


default_color = colorama.Fore.WHITE
outcome_to_color = {TestOutcome.SUCCESS: colorama.Fore.GREEN,
                    TestOutcome.ERROR: colorama.Fore.RED,
                    TestOutcome.EXPECTED_FAILURE: colorama.Fore.CYAN,
                    TestOutcome.FAILED: colorama.Fore.LIGHTRED_EX,
                    TestOutcome.SKIPPED: colorama.Fore.YELLOW,
                    TestOutcome.UNEXPECTED_SUCCESS: colorama.Fore.CYAN}


current_format = "{l_bar}{bar}| {n:.0f}/{total:.0f} seconds{postfix}"
bar_format = "{l_bar}%%s{bar}%s| {n:.0f}/{total:.0f} %%s{postfix}" % colorama.Fore.RESET
unknown_format = "{l_bar}%%s{bar}%s| ? %%s{postfix}" % colorama.Fore.RESET


class DummyFile(object):
    file = None

    def __init__(self, file):
        self.file = file

    def write(self, x):
        x = x.rstrip('\r\n')
        if len(x) > 0:
            return tqdm.tqdm.write(x, file=self.file, end="")

    def flush(self):
        self.file.flush()


def get_statistics(test):
    if not test.resource_manager:
        print("No manager")
        return None

    try:
        stats = test.resource_manager.get_statistics(test.data.name)
        return stats['avg']

    except:
        return None


tracer_event = threading.Event()
wrapped_settrace = False


def create_tree_bar(test):
    desc = test.parents_count * '| ' + test.data.name
    if test.IS_COMPLEX:
        total = len(test._tests)
        unit_scale = False

    else:
        avg_time = get_statistics(test)
        if avg_time:
            test.logger.debug("Test avg runtime: %s", avg_time)
            total = int(avg_time) * 10
            unit_scale = 0.1

        else:
            test.logger.debug("Couldn't get test statistics")
            test._no_statistics = True
            total = 1
            desc += " (No statistics)"

    test.progress_bar = tqdm.trange(total, desc=desc, unit_scale=unit_scale,
                                    position=test.identifier, leave=True,
                                    bar_format=get_format(test, colorama.Fore.WHITE))
    test.progress_bar.finish = False
    return test.progress_bar


def create_current_bar(test):
    index = 0
    total_tests = 0
    for sibling in test.parent:
        total_tests += 1

        if sibling is test:
            index = total_tests

    desc = "({} / {} in parent) {}".format(index,
                                           total_tests,
                                           test.data.name)

    avg_time = get_statistics(test)
    if avg_time:
        test.logger.debug("Test avg runtime: %s", avg_time)
        total = int(avg_time)

    else:
        test.logger.debug("Couldn't get test statistics")
        test._no_statistics = True
        total = 1
        desc += " (No statistics)"

    test.progress_bar = tqdm.trange(total*10, desc=desc, leave=False,
                                    position=0, unit_scale=0.1,
                                    bar_format=current_format)
    test.progress_bar.finish = False
    return test.progress_bar


def get_format(test, color):
    if hasattr(test, '_no_statistics'):
        return unknown_format % (color, 'seconds')

    if test.IS_COMPLEX:
        return bar_format % (color, 'tests')

    else:
        return bar_format % (color, 'seconds')


def set_color(test):
    color = default_color
    if hasattr(test.data, 'exception_type'):
        color = outcome_to_color.get(test.data.exception_type, color)

    else:
        if test.data.success is True:
            color = outcome_to_color.get(TestOutcome.SUCCESS)

        elif test.data.success is False:
            color = outcome_to_color.get(TestOutcome.FAILED)

    test.progress_bar.bar_format = get_format(test, color)


def go_over_tests(test, use_color):
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

                while tracer_event.is_set():
                    time.sleep(0.2)

            if use_color and index == test.progress_bar.total - 1:
                set_color(test)


def wrap_settrace():
    global wrapped_settrace
    if not wrapped_settrace:
        wrapped_settrace = True
        old_settrace = sys.settrace

        def event_on_trace(function):
            if function is None:
                tracer_event.clear()
            else:
                tracer_event.set()
            old_settrace(function)

        sys.settrace = event_on_trace
