from remarkable_fs.connection import connect
from remarkable_fs.documents import DocumentRoot
from remarkable_fs.fs import mount
import sys
import fuse

try:
    import __builtin__
    raw_input = __builtin__.raw_input
except:
    raw_input = input

def main(argv = sys.argv):
    if len(argv) >= 2:
        mount_point = argv[1]
    else:
        mount_point = raw_input("Directory: ")

    print("Connecting to reMarkable...")
    with connect(*argv[2:]) as conn:
        connect_to(DocumentRoot, conn, mount_point)

def connect_to(connection_object, parameter, mount_point):
    root = connection_object(parameter)
    print("Now serving documents at " + mount_point)
    kwargs={}
    if fuse.system() == "Darwin":
        kwargs["volname"] = "reMarkable"
    mount(mount_point, root, **kwargs)
