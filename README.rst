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

``remarkable-fs`` works on both Linux and macOS. To install it, you
will need:

- FUSE. If on macOS, get this from the `Fuse for macOS`_ project. If
  on Linux, your package manager should have it.
- ``pip``, the Python package installer. You can install this by running
  ``sudo easy_install pip``.

.. _Fuse for macOS: https://osxfuse.github.io/

Then, to install ``remarkable-fs``, just run:

  sudo pip install remarkable-fs

Running
-------

Make an empty directory on your computer. This directory is where your
documents will appear. Then run ``remarkable-fs``. You will be
prompted for the path to this directory; type it in. (On macOS, you
can instead drag the directory to the terminal window at this point.)

You will then be prompted for the root password of your reMarkable.
You can find this by opening the settings menu of the reMarkable,
choosing "About", scrolling to the very bottom, and finding the
paragraph beginning: "To do so, this device acts as a USB ethernet
device..." If you don't want to have to type in the root password
every time you run ``remarkable-fs``, follow the instructions on
passwordless login from the ``reMarkable wiki``_.

.. _reMarkable wiki: http://remarkablewiki.com/index.php?title=Methods_of_access#Setting_up_ssh-keys

If all goes well, your files will be available in the directory you
chose. Go wild!

When you are finished, you can stop ``remarkable-fs`` by pressing ctrl-C.

Note that your reMarkable will be unresponsive for the time you have
``remarkable-fs`` running. It should start responding as soon as you close
``remarkable-fs`` or unplug the USB cable. If for some reason it doesn't, you
can force your reMarkable to restart by holding down the power button for five
seconds, letting go, and then pressing the power button for another second.
