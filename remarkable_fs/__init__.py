from remarkable_fs.connection import connect
from remarkable_fs.documents import DocumentRoot
from remarkable_fs.fs import mount
import sys
import __builtin__

try:
    raw_input = __builtin__.raw_input
except AttributeError:
    raw_input = __builtin__.input

def main(argv = sys.argv):
    if len(argv) == 1:
        mount_point = argv[0]
    else:
        mount_point = raw_input("Mount point: ")

    with connect() as conn:
        mount(mount_point, DocumentRoot(conn.sftp))
