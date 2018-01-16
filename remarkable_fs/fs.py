import os
import sys
import errno
import stat
from fuse import FUSE, FuseOSError, Operations
from documents import Collection

class Remarkable(Operations):
    def __init__(self, documents):
        self.documents = documents

    def navigate(self, path):
        if path == '/' or path == '':
            return self.documents
        else:
            dir, file = os.path.split(path)
            node = self.navigate(dir)
            try:
                return node[file]
            except KeyError:
                raise FuseOSError(errno.ENOENT)

    def getattr(self, path, fh=None):
        node = self.navigate(path)
        mode = stat.S_IRUSR + stat.S_IRGRP
        if isinstance(node, Collection):
            mode += stat.S_IFDIR
        else:
            mode += stat.S_IFREG
        return {"st_mode": mode}

    def readdir(self, path, fh):
        node = self.navigate(path)
        yield "."
        yield ".."
        if isinstance(node, Collection):
            for file in node:
                yield file

def mount(mountpoint, documents):
    FUSE(Remarkable(documents), mountpoint, nothreads=True, foreground=True)
