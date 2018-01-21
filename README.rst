A FUSE filesystem driver for reMarkable
=======================================

``remarkable-fs`` allows you to see the contents of your reMarkable as a normal
folder on your computer. All your documents and folders are visible; you can
copy documents to and from the reMarkable, create folders, and move and delete
folders and files.

Currently, only PDF and EPUB files are supported. In particular, there is no
support for handwritten notes yet!

*This software is in an early stage of development. I take no responsibility if
it deletes your files or bricks your reMarkable! Do not use it if you are
unwilling to lose all your documents. Use at your own risk!*

Installation
------------

``remarkable-fs`` works on Linux. It has not been tested on macOS, but in
principle it ought to work with some coaxing. It currently requires some
terminal knowhow to run it.

To install it, make sure you have Python and FUSE. Then run:

  python setup.py install --user

This will take a while. Eventually, it will install the ``remarkable-fs``
program in ``~/.local/bin``.

Running
-------

Make sure you have:

- The root password of your reMarkable (can be found by opening the reMarkable
  menu, choosing "About", scrolling to the very bottom, and finding the
  paragraph beginning: "To do so, this device acts as a USB ethernet device..."
- An empty directory (the "mount point") where you want your files to appear.

Then run:

  ~/.local/bin/remarkable-fs MOUNT_POINT

where ``MOUNT_POINT`` should be replaced with the directory you chose above.

You will be prompted for the reMarkable password, and afterwards your files will
be available in the mount point. Go wild!

When you are finished, you can either unmount the directory or press ctrl-C to
stop ``remarkable-fs``.

Note that your reMarkable will be unresponsive for the time you have
``remarkable-fs`` running. It should start responding as soon as you close
``remarkable-fs`` or unplug the USB cable. If for some reason it doesn't, you
can force your reMarkable to restart by holding down the power button for five
seconds, letting go, and then pressing the power button again.
