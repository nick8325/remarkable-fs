"""Handles maintaining a connection to the reMarkable."""

from contextlib import contextmanager
from collections import namedtuple
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.sftp_client import SFTPClient
from paramiko.ssh_exception import SSHException, AuthenticationException
from getpass import getpass
from signal import signal, SIGTERM, SIGHUP

Connection = namedtuple('Connection', 'ssh sftp')

@contextmanager
def connect(addr=None):
    """Connect to the remarkable. Yields a Connection object.

    The sftp field of the connection object has as its working directory the
    data directory of xochitl."""

    default_addr = "10.11.99.1"
    with SSHClient() as ssh:
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy)
        try:
            ssh.connect(addr or default_addr, username="root")
        except (SSHException, AuthenticationException):
            print("Please enter the root password of your reMarkable.")
            print("To find out the password, follow the instructions at:")
            print("http://remarkablewiki.com/index.php?title=Methods_of_access#Connecting_via_ssh")
            password = getpass()
            ssh.connect(addr or default_addr, username="root", password=password, look_for_keys=False)

        # Stop xochitl but restart it again if the connection drops
        on_start = "systemctl stop xochitl"
        on_finish = "systemctl restart xochitl"
        # We know USB was disconnected when the power supply drops.
        # We also kill the SSH connection so that the information
        # in FUSE is not out of date.
        ssh.exec_command(on_start)
        if addr is None:
            # Only do this if we are plugged in to the device
            ssh.exec_command("while /sbin/ip a s usb0 | grep -q 10.11.99; do sleep 1; done; %s; kill $PPID" % on_finish)
        try:
            def raise_exception(*args):
                raise RuntimeError("Process terminated")
            signal(SIGTERM, raise_exception)
            signal(SIGHUP, raise_exception)
            with ssh.open_sftp() as sftp:
                sftp.chdir("/home/root/.local/share/remarkable/xochitl")
                yield Connection(ssh, sftp)

        finally:
            # Closing stdin triggers on_finish to run, so only do it now
            try:
                ssh.exec_command(on_finish)
            except:
                pass
