"""Module for the TkinterHandler and its logic."""
# pylint: disable=protected-access, ungrouped-imports
from __future__ import absolute_import

import time
import tkinter
import threading
from itertools import count
from tkinter.ttk import Progressbar, Style

from tkscrolledframe import ScrolledFrame
from rotest.core.models.case_data import TestOutcome
from rotest.core.result.handlers.abstract_handler import AbstractResultHandler

from .utils import (get_test_outcome, wrap_settrace, go_over_tests,
                    StatisticManager)


# Map test result to HTML color code
OUTCOME_TO_STYLE = {None: 'white',
                    TestOutcome.SUCCESS: 'green',
                    TestOutcome.ERROR: 'maroon',
                    TestOutcome.EXPECTED_FAILURE: 'FUCHSIA',
                    TestOutcome.FAILED: 'red',
                    TestOutcome.SKIPPED: 'yellow',
                    TestOutcome.UNEXPECTED_SUCCESS: 'AQUA'}


class TkinterThread(threading.Thread):
    """Thread responsible for creating and running the Tkinter window."""
    CREATE_WINDOW_TIMEOUT = 5  # Seconds
    WINDOW_HEIGHT = 500  # Pixels
    BAR_WIDTH = 100  # Pixels

    def __init__(self, test):
        super(TkinterThread, self).__init__()
        self.test = test
        self.setDaemon(True)
        self.finish_preperation_event = threading.Event()
        self.frame = None
        self.inner_frame = None

    def iterate_over_tests(self, test, window, depth=0, row=count()):
        """Recursively populate the given frame with the tests' widgets."""
        self.create_tree_bar(test, window, depth, next(row))
        if test.IS_COMPLEX:
            for sub_test in test:
                self.iterate_over_tests(sub_test, window, depth + 1, row)

    def create_tree_bar(self, test, window, depth, row):
        """Create progress bar for a test in an hierarchical form."""
        name = test.data.name
        if test.IS_COMPLEX:
            total = test._expected_time

        else:
            avg_time = test._expected_time
            if avg_time:
                total = int(avg_time) * 10

            else:
                total = 10
                name += " (No statistics)"

        label = tkinter.Label(window, text=name, height=1)
        style = Style()
        style.theme_use('clam')
        style_name = "{}.Horizontal.TProgressbar".format(test.identifier)
        style.configure(style_name, foreground='red', background='red')
        progress = Progressbar(window, orient=tkinter.HORIZONTAL,
                               maximum=total, length=self.BAR_WIDTH,
                               mode='determinate', style=style_name)

        test.progress_bar = ProgressContainer(test, progress, style_name)

        label.grid(column=depth, row=row)
        progress.grid(column=depth + 1, row=row)

    def run(self):
        """Create a Tkinter window, populate it with widgets, and run it."""
        window = tkinter.Tk()
        window.resizable(False, False)
        self.frame = ScrolledFrame(window, scrollbars="vertical",
                                   height=self.WINDOW_HEIGHT)
        self.frame.pack()
        self.inner_frame = self.frame.display_widget(tkinter.Frame)
        self.iterate_over_tests(self.test, self.inner_frame)
        self.finish_preperation_event.set()
        window.mainloop()

    def start(self):
        """Create and run the window, sync until it's up ready."""
        super(TkinterThread, self).start()
        self.finish_preperation_event.wait(timeout=self.CREATE_WINDOW_TIMEOUT)
        # Adjust the window's width
        while self.inner_frame.winfo_width() <= 1:
            time.sleep(0.01)

        self.frame['width'] = self.inner_frame.winfo_width()


class ProgressContainer(object):
    """Manager for a test's progress bar."""
    def __init__(self, test, progress_bar, style_name):
        self.test = test
        self.progress_bar = progress_bar
        self.finish = False
        self.start = False
        self.total = self.progress_bar['maximum']
        self.style_name = style_name

    def update_color(self):
        """Update the progress bar's color according to the test result."""
        color = OUTCOME_TO_STYLE[get_test_outcome(self.test)]
        Style().configure(self.style_name, background=color)

    def __iter__(self):
        value = self.progress_bar['value']
        while value < self.total:

            if self.finish:
                self.progress_bar['value'] = self.total
                self.update_color()
                return

            self.update_color()
            yield value

            value += 1
            self.progress_bar['value'] = value

        self.update_color()


class TkinterProgressHandler(AbstractResultHandler):
    """TkinterProgressHandler interface."""
    NAME = 'tk_progress'
    watcher_thread = None
    tkinter_thread = None

    def start_test_run(self):
        """Called once before any tests are executed."""
        wrap_settrace()
        StatisticManager.calculate_expected_time(self.main_test)
        self.tkinter_thread = TkinterThread(self.main_test)
        self.tkinter_thread.start()

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
