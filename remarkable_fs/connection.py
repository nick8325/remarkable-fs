from contextlib import contextmanager
from collections import namedtuple
from paramiko.client import SSHClient, WarningPolicy
from paramiko.sftp_client import SFTPClient

Connection = namedtuple('Connection', 'ssh sftp')

@contextmanager
def connect():
    with SSHClient() as ssh:
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(WarningPolicy)
        ssh.connect('localhost')

        # Stop xochitl but restart it again if the connection drops
        on_start = "systemctl stop xochitl"
        on_finish = "systemctl start xochitl"
        ssh.exec_command("""bash -c "trap '%s' EXIT; %s; cat" """ % (on_start, on_finish))

        with ssh.open_sftp() as sftp:
            yield Connection(ssh, sftp)
