"""Defining the progress result handler."""
# pylint: disable=too-many-arguments
from __future__ import absolute_import

import threading

import colorama
from rotest.core.result.handlers.abstract_handler import AbstractResultHandler

from .utils import wrap_settrace, get_statistics, go_over_tests, set_color, create_bar


class ProgressHandler(AbstractResultHandler):
    """ProgressHandler interface."""
    NAME = 'progress'
    watcher_thread = None

    def _create_bars(self, test):
        """."""
        test.progress_bar = create_bar(test)
        if test.IS_COMPLEX:

            for sub_test in test:
                self._create_bars(sub_test)

    def start_test_run(self):
        """Called once before any tests are executed."""
        self._create_bars(self.main_test)
        wrap_settrace()
        # go_over_tests(self.main_test)
        self.watcher_thread = threading.Thread(target=go_over_tests, args=(self.main_test,))
        self.watcher_thread.setDaemon(True)
        self.watcher_thread.start()

    def start_test(self, test):
        """Called when the given test is about to be run.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """

    def should_skip(self, test):
        """Check if the test should be skipped.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.

        Returns:
            str: skip reason if the test should be skipped, None otherwise.
        """
        return None

    def update_resources(self, test):
        """Called once after locking the tests resources.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """

    def setup_finished(self, test):
        """Called when the given test finished setting up.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """

    def start_teardown(self, test):
        """Called when the given test is starting its teardown.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """

    def stop_test(self, test):
        """Called when the given test has been run.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """
        if test.progress_bar:
            test.progress_bar.finish = True

    def start_composite(self, test):
        """Called when the given TestSuite is about to be run.

        Args:
            test (rotest.core.suite.TestSuite): test item instance.
        """

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

        print("\n" * 5)

    def add_success(self, test):
        """Called when a test has completed successfully.
        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """
        if test.progress_bar:
            set_color(test, colorama.Fore.GREEN)

    def add_info(self, test, msg):
        """Called when a test registers a success message.
        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
            msg (str): success message.
        """

    def add_skip(self, test, reason):
        """Called when a test is skipped.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
            reason (str): reason for skipping the test.
        """
        if test.progress_bar:
            set_color(test, colorama.Fore.YELLOW)

    def add_failure(self, test, exception_string):
        """Called when an error has occurred.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
            exception_string (str): exception description.
        """
        if test.progress_bar:
            set_color(test, colorama.Fore.LIGHTRED_EX)

    def add_error(self, test, exception_string):
        """Called when an error has occurred.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
            exception_string (str): exception description.
        """
        if test.progress_bar:
            set_color(test, colorama.Fore.RED)

    def add_expected_failure(self, test, exception_string):
        """Called when an expected failure/error occurred.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
            exception_string (str): exception description.
        """

    def add_unexpected_success(self, test):
        """Called when a test was expected to fail, but succeed.

        Args:
            test (rotest.core.abstract_test.AbstractTest): test item instance.
        """

    def print_errors(self, tests_run, errors, skipped, failures,
                     expected_failures, unexpected_successes):
        """Called by TestRunner after test run.

        Args:
            tests_run (number): count of tests that has been run.
            errors (list): error tests details list.
            skipped (list): skipped tests details list.
            failures (list): failed tests details list.
            expected_failures (list): expected-to-fail tests details list.
            unexpected_successes (list): unexpected successes tests details
                list.
        """
