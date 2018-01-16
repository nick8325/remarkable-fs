import os
import sys
from errno import *
import stat
from fuse import FUSE, FuseOSError, Operations
from documents import Collection

class Remarkable(Operations):
    def __init__(self, documents):
        self.documents = documents
        self.uid = os.getuid()
        self.gid = os.getgid()

    def navigate(self, path):
        if path == '/' or path == '':
            return self.documents
        else:
            dir, file = os.path.split(path)
            node = self.navigate(dir)
            try:
                return node[file]
            except KeyError:
                raise FuseOSError(ENOENT)

    def parent(self, path):
        dir, file = os.path.split(path)

        if file == '': # e.g., moving root directory
            raise FuseOSError(EBUSY)

        return (self.navigate[path], file)

    def access(self, path, mode):
        # write access
        if mode == os.W_OK:
            # parent directory should exist
            dir, file = self.parent(path)

            # No overwriting of existing data yet
            if file in dir:
                raise FuseOSError(EACCES)

        # unknown access mode, or read+write access
        if mode != os.F_OK and (mode & ~os.R_OK & ~os.X_OK) != 0:
            raise FuseOSError(EACCES)

        node = self.navigate(path)
        if (mode & os.X_OK) and not isinstance(node, Collection):
            raise FuseOSError(EACCES)

    def getattr(self, path, fh=None):
        node = self.navigate(path)
        mode = stat.S_IRUSR + stat.S_IRGRP + stat.S_IROTH
        if isinstance(node, Collection):
            mode += stat.S_IFDIR + stat.S_IXUSR + stat.S_IXGRP + stat.S_IXOTH
        else:
            mode += stat.S_IFREG

        attrs = {"st_mode": mode, "st_uid": self.uid, "st_gid": self.gid}
        try:
            attrs["st_size"] = node.size
        except AttributeError:
            pass
        try:
            attrs["st_atime"] = node.atime
        except AttributeError:
            pass
        try:
            attrs["st_mtime"] = node.mtime
            attrs["st_ctime"] = node.mtime
        except AttributeError:
            pass
        return attrs

    def readdir(self, path, fh):
        node = self.navigate(path)
        yield "."
        yield ".."
        if isinstance(node, Collection):
            for file in node:
                yield file

def mount(mountpoint, documents):
    FUSE(Remarkable(documents), mountpoint, nothreads=True, foreground=True)
