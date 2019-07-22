"""Defining the progress result handler."""
# pylint: disable=too-many-arguments
from __future__ import absolute_import, print_function

import threading

from rotest.core.result.handlers.abstract_handler import AbstractResultHandler

from .utils import wrap_settrace, go_over_tests, create_tree_bar


class FullProgressHandler(AbstractResultHandler):
    """FullProgressHandler interface."""
    NAME = 'full_progress'
    watcher_thread = None

    def __init__(self, *args, **kwargs):
        super(FullProgressHandler, self).__init__(*args, **kwargs)
        self.max_identifier = 1

    def _create_bars(self, test):
        """Return progress bar."""
        test.progress_bar = create_tree_bar(test)
        max_index = test.identifier
        if test.IS_COMPLEX:
            for sub_test in test:
                max_index = max(max_index, self._create_bars(sub_test))

        return max_index

    def start_test_run(self):
        """Called once before any tests are executed."""
        wrap_settrace()
        self.max_identifier = self._create_bars(self.main_test)

        self.watcher_thread = threading.Thread(target=go_over_tests,
                                               kwargs={"test": self.main_test,
                                                       "use_color": True})
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

        print("\n" * self.max_identifier)
