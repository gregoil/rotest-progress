rotest-progress
---------------

Adds a progress bar based on remote statistics where it can (meant to be used on Linux machines).

This plugin is automatically enabled after installing it with pip,
just add either 'progress' or 'full_progress' to your list of output handlers
(using --outputs or in the json config file).

full_progress
=============

Shows a tree of the tests and blocks that are about to run, each  hierarchy with a progress bar.


progress
========

Shows a single progress bar for the currently running component. Can be used with other printing output handlers.
