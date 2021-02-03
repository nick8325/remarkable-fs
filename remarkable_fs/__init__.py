from remarkable_fs.connection import connect
from remarkable_fs.documents import DocumentRoot, DocumentRootDir
from remarkable_fs.fs import mount
import sys
import fuse
import os

try:
    import __builtin__
    raw_input = __builtin__.raw_input
except:
    raw_input = input

def main(argv = sys.argv):
    if len(argv) == 2:
        mount_point = argv[1]
        remarkable_mount_point = None
    elif len(argv) >= 3:
        mount_point = argv[1]
        remarkable_mount_point = argv[2]
    else:
        mount_point = raw_input("User Directory: ")
        remarkable_mount_point = raw_input("ReMarkable Directory (press enter for automatic ssh connection): ")

    print("Connecting to reMarkable...")
    if remarkable_mount_point == None:
        with connect(*argv[2:]) as conn:
            root = DocumentRoot(conn)
            connect_to(root, mount_point)
    else:
        mount_point = os.path.abspath(mount_point)
        os.chdir( remarkable_mount_point )
        root = DocumentRootDir()
        connect_to(root, mount_point)

def connect_to(root, mount_point):
    print("Now serving documents at " + mount_point)
    kwargs={}
    if fuse.system() == "Darwin":
        kwargs["volname"] = "reMarkable"
    mount(mount_point, root, **kwargs)
