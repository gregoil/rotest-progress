""""""
import sys
import time
import threading

import tqdm
import colorama


bar_format = "{l_bar}%%s{bar}%s| {n_fmt}/{total_fmt} %%s{postfix}" % colorama.Fore.RESET
unknown_format = "{l_bar}%%s{bar}%s| ? %%s{postfix}" % colorama.Fore.RESET


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


def create_bar(test):
    if hasattr(test, 'progress_bar'):
        return test.progress_bar

    desc = test.parents_count * '| ' + test.data.name
    if test.IS_COMPLEX:
        total = len(test._tests)

    else:
        avg_time = get_statistics(test)
        if avg_time:
            test.logger.debug("Test avg runtime: %s", avg_time)
            total = int(avg_time)

        else:
            test.logger.debug("Couldn't get test statistics")
            test._no_statistics = True
            total = 1
            desc += " (No statistics)"

    test.progress_bar = tqdm.trange(total, desc=desc, leave=True, position=test.identifier,
                                    bar_format=get_format(test, colorama.Fore.WHITE))
    test.progress_bar.finish = False
    return test.progress_bar


def get_format(test, color):
    if hasattr(test, '_no_statistics'):
        return unknown_format % (color, 'seconds')

    if test.IS_COMPLEX:
        return bar_format % (color, 'tests')

    else:
        return bar_format % (color, 'seconds')


def set_color(test, color):
    test.progress_bar.bar_format = get_format(test, color)
    test.progress_bar.update(0)


def go_over_tests(test):
    if test.IS_COMPLEX:
        for _, sub_test in zip(create_bar(test), test):
            go_over_tests(sub_test)

    else:
        for _ in create_bar(test):
            if test.progress_bar.finish:
                continue
            time.sleep(1)
            if test.progress_bar.n == test.progress_bar.total - 1:
                while not test.progress_bar.finish:
                    time.sleep(0.2)

            while tracer_event.is_set():
                time.sleep(0.2)


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
