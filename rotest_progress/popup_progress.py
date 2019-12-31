from __future__ import absolute_import

import tkinter
import threading
from itertools import count
from tkinter.ttk import Progressbar, Style

from rotest.core.models.case_data import TestOutcome
from rotest.core.result.handlers.abstract_handler import AbstractResultHandler

from .utils import (get_test_outcome, wrap_settrace, go_over_tests,
                    calculate_expected_time)


OUTCOME_TO_STYLE = {None: 'white',
                    TestOutcome.SUCCESS: 'green',
                    TestOutcome.ERROR: 'maroon',
                    TestOutcome.EXPECTED_FAILURE: 'FUCHSIA',
                    TestOutcome.FAILED: 'red',
                    TestOutcome.SKIPPED: 'yellow',
                    TestOutcome.UNEXPECTED_SUCCESS: 'AQUA'}


def create_window(test):
    watcher_thread = threading.Thread(target=_create_thread,
                                      kwargs={"test": test})
    watcher_thread.setDaemon(True)
    watcher_thread.start()
    return watcher_thread


def _create_thread(test):
    """Iterate over test and sub-tests.

    Args:
        test (AbstractTest): Test or suite to iterate over.
        use_color (bool): whether to use colors in the progress bar.
    """
    window = tkinter.Tk()
    frame = tkinter.Frame(window)
    frame.pack()
    iterate_over_tests(test, frame)
    window.mainloop()


def iterate_over_tests(test, window, depth=0, row=count()):
    create_tree_bar(test, window, depth, next(row))
    if test.IS_COMPLEX:
        for sub_test in test:
            iterate_over_tests(sub_test, window, depth+1, row)


class ProgressContainer(object):
    def __init__(self, test, label, progress_bar):
        self.test = test
        self.label = label
        self.progress_bar = progress_bar
        self.counter = 0
        self.finish = False
        self.start = False
        self.total = self.progress_bar['length']
        self.style_name = str(test.identifier)+".Horizontal.TProgressbar"

    def __iter__(self):
        value = self.progress_bar['value']
        while value < self.total:
            Style().configure(self.style_name, background=OUTCOME_TO_STYLE[get_test_outcome(self.test)])

            if self.finish:
                self.progress_bar['value'] = self.total
                return

            yield value

            value += 1
            self.progress_bar['value'] = value


def create_tree_bar(test, window, depth, row):
    """Create progress bar for a test in an hierarchical form."""
    desc = test.data.name
    if test.IS_COMPLEX:
        total = test._expected_time

    else:
        avg_time = test._expected_time
        if avg_time:
            total = int(avg_time) * 10

        else:
            total = 10
            desc += " (No statistics)"

    label = tkinter.Label(window, text=desc, height=1)
    style = Style()
    style.theme_use('clam')
    name = str(test.identifier)+".Horizontal.TProgressbar"
    style.configure(name, foreground='red', background='red')
    progress = Progressbar(window, orient=tkinter.HORIZONTAL, maximum=total,
                           length=100, mode='determinate', style=name)

    progress.__next__ = None
    progress.__iter__ = None
    test.progress_bar = ProgressContainer(test, label, progress)

    label.grid(column=depth, row=row)
    progress.grid(column=depth+1, row=row)


class TkinterProgressHandler(AbstractResultHandler):
    """FullProgressHandler interface."""
    NAME = 'tk_progress'
    watcher_thread = None
    tkinter_thread = None

    def start_test_run(self):
        """Called once before any tests are executed."""
        wrap_settrace()
        calculate_expected_time(self.main_test)
        self.tkinter_thread = create_window(self.main_test)
        while not hasattr(self.main_test, "progress_bar"):
            pass

        self.watcher_thread = threading.Thread(target=go_over_tests,
                                               kwargs={"test": self.main_test,
                                                       "use_color": False})
        self.watcher_thread.setDaemon(True)
        self.watcher_thread.start()

    def start_test(self, test):
        """Called when the given test is about to be run."""
        test.progress_bar.start = True

    def stop_test(self, test):
        """Called when the given test has been run.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """
        if test.progress_bar:
            test.progress_bar.finish = True

    def stop_composite(self, test):
        """Called when the given TestSuite has been run.

        Args:
            test (rotest.core.suite.TestSuite): test item instance.
        """
        return self.stop_test(test)

    def stop_test_run(self):
        """Called once after all tests are executed."""
        if self.watcher_thread:
            self.watcher_thread.join()

        if self.tkinter_thread:
            self.tkinter_thread.join()
