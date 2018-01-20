import os
import sys
from errno import *
import stat
from fuse import FUSE, FuseOSError, Operations
from remarkable_fs.documents import Collection, Document, new_collection, new_document
from io import BytesIO

class Remarkable(Operations):
    def __init__(self, documents):
        self.documents = documents
        self.uid = os.getuid()
        self.gid = os.getgid()
        self.file_handles = {}
        self.free_file_handles = []
        self.next_file_handle = 1 # open returns 0
        self.writing_files = set()

    def free_file_handle(self, fd):
        if fd != 0:
            self.file_handles[fd].close()
            del self.file_handles[fd]
            self.free_file_handles.append(fd)

    def new_file_handle(self, value):
        if self.free_file_handles == []:
            fd = self.next_file_handle
            self.next_file_handle += 1
        else:
            fd = self.free_file_handles.pop()
        self.file_handles[fd] = value
        return fd

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

        return (self.navigate(dir), file)

    def check_not_writing(self, parent, name):
        if (parent, name) in self.writing_files:
            raise FuseOSError(EACCES)
        
    def access(self, path, mode):
        # write access
        if mode == os.W_OK:
            # parent directory should exist
            self.parent(path)
            # N.B. we can't open files for writing.
            # But rm issues its "are you sure you want to remove a
            # write-protected file?" warning if we return EACCES here.
            return

        # unknown access mode, or read+write access
        if mode != os.F_OK and (mode & ~os.R_OK & ~os.X_OK) != 0:
            raise FuseOSError(EACCES)

        node = self.navigate(path)
        if (mode & os.X_OK) and not isinstance(node, Collection):
            raise FuseOSError(EACCES)

    def getattr(self, path, fh=None):
        try:
            parent, name = self.parent(path)
            if (parent, name) in self.writing_files:
                return {"st_uid": self.uid, "st_gid": self.gid, "st_mode": stat.S_IFREG + stat.S_IWUSR}
        except FuseOSError:
            pass
        
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

    def chmod(self, path, mode):
        pass

    def chown(self, path, uid, gid):
        pass

    def readdir(self, path, fh):
        node = self.navigate(path)
        if isinstance(node, Collection):
            yield "."
            yield ".."
            for file in node:
                yield file
        else:
            raise FuseOSError(ENOTDIR)

    def rename(self, old, new):
        old_node = self.navigate(old)
        new_dir, new_file = self.parent(new)
        new_node = new_dir.get(new_file)

        self.check_not_writing(new_dir, new_file)

        if new_node is None:
            # It's a move with a filename
            old_node.rename(new_dir, new_file)
        elif isinstance(new_node, Collection):
            # It's a move into a directory
            old_node.rename(new_node, old_node.name)
        else:
            # It's overwriting a file
            new_node.delete()
            old_node.rename(new_dir, new_file)

    def unlink(self, path):
        node = self.navigate(path)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        node.delete()

    def create(self, path, flags):
        parent, name = self.parent(path)
        self.check_not_writing(parent, name)

        return self.new_file_handle(FileWriter(self, parent, name))

    def rmdir(self, path):
        node = self.navigate(path)
        if not isinstance(node, Collection):
            raise FuseOSError(ENOTDIR)
        if len(node.items()) > 0:
            raise FuseOSError(ENOTEMPTY)
        node.delete()

    def mkdir(self, path, mode):
        parent, name = self.parent(path)
        if name in parent:
            raise FuseOSError(EEXIST)
        new_collection(self.documents, name, parent)

    def read(self, path, size, offset, fh):
        node = self.navigate(path)
        if not isinstance(node, Document):
            raise FuseOSError(EISDIR)
        return node.read_chunk(offset, size)

    def write(self, path, data, offset, fh):
        buf = self.file_handles[fh].buf
        buf.seek(offset)
        buf.write(data)
        return len(data)

    def truncate(self, path, length):
        raise FuseOSError(EACCES)
        
    def release(self, path, fh):
        self.free_file_handle(fh)

class FileWriter(object):
    def __init__(self, fs, parent, name):
        self.fs = fs
        self.parent = parent
        self.name = name
        self.buf = BytesIO()
        self.fs.writing_files.add((parent, name))

    def close(self):
        # Compute a good name, stripping off directory components
        # and file extensions
        name, ext = os.path.splitext(self.name)
        if ext != ".pdf" and ext != ".epub":
            name = self.name
        name = os.path.basename(name)

        new_document(self.fs.documents, name, self.parent, self.buf.getvalue())
        self.fs.writing_files.remove((self.parent, self.name))
        
def mount(mountpoint, documents):
    FUSE(Remarkable(documents), mountpoint, nothreads=True, foreground=True, big_writes=True, max_write=1048576)
