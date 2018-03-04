"""A FUSE filesystem wrapper for the reMarkable."""

import os
import sys
from errno import *
from posix import O_WRONLY, O_RDWR
import stat
from fuse import FUSE, FuseOSError, Operations
from remarkable_fs.documents import Collection, Document, NewDocument
from io import BytesIO
import traceback

class FileHandles(object):
    """Keeps track of the mapping between file handles and files."""
    def __init__(self):
        # All open files
        self.file_handles = {}
        # File handles which have been closed and can be re-used
        self.free_file_handles = []
        # The next unused (never allocated) file handle
        self.next_file_handle = 0

    def new(self, file):
        """Allocate a new file descriptor and return it."""
        
        # Find a free file handle
        if self.free_file_handles:
            fd = self.free_file_handles.pop()
        else:
            fd = self.next_file_handle
            self.next_file_handle += 1

        # Record that the file is open
        self.file_handles[fd] = file
        return fd

    def close(self, fd):
        """Close a file descriptor."""

        del self.file_handles[fd]
        self.free_file_handles.append(fd)

    def get(self, fd):
        """Look up a file descriptor. The file descriptor must be valid."""
        return self.file_handles[fd]

class Remarkable(Operations):
    """The main filesystem implementation."""

    def __init__(self, documents):
        """documents - a remarkable_fs.documents.DocumentRoot object."""

        self.documents = documents
        self.fds = FileHandles()

    def node(self, path):
        """Find a node in the filesystem.

        Raises ENOENT if the file does not exist."""
        
        path = os.path.normpath(path)
        if path == '/' or path == '.':
            return self.documents
        else:
            dir, file = os.path.split(path)
            node = self.node(dir)
            try:
                return node[file]
            except KeyError:
                raise FuseOSError(ENOENT)

    def parent(self, path):
        """Find the parent node of a path in the filesystem. The path does not
        have to exist but its parent directory should. Generally used when
        creating a new file.

        Returns (parent node, basename). Raises ENOENT if the parent directory
        does not exist and EBUSY if the path is the root directory."""
        
        path = os.path.normpath(path)
        dir, file = os.path.split(path)

        if file == '':
            # Root directory - cannot be moved/created/deleted
            raise FuseOSError(EBUSY)

        return (self.node(dir), file)

    #
    # Opening and closing files
    #
    
    def open(self, path, flags):
        node = self.node(path)

        # Don't allow overwriting existing files
        # (changing this needs more code in documents.py)
        if flags & O_WRONLY or flags & O_RDWR and not isinstance(node, NewDocument):
            raise FuseOSError(EPERM)

        return self.fds.new(self.node(path))

    def create(self, path, flags):
        parent, name = self.parent(path)

        # Don't allow overwriting existing files, for paranoia
        if name in parent:
            raise FuseOSError(EEXIST)

        return self.fds.new(parent.new_document(name))

    def flush(self, path, fd):
        try:
            self.fds.get(fd).save()
        except IOError:
            # File conversion error
            traceback.print_exc()
            raise FuseOSError(EIO)

    def release(self, path, fd):
        self.fds.close(fd)

    #
    # Reading and writing files
    #
    
    def read(self, path, size, offset, fd):
        node = self.fds.get(fd)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        return self.fds.get(fd).read(offset, size)

    def write(self, path, data, offset, fd):
        node = self.fds.get(fd)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        node.write(offset, data)
        
        return len(data)

    def truncate(self, path, length, fd=None):
        if fd is None:
            node = self.node(path)
        else:
            node = self.fds.get(fd)

        # Don't allow overwriting existing files
        # (changing this needs more code in documents.py)
        if hasattr(node, "truncate"):
            node.truncate(length)
        else:
            raise FuseOSError(EPERM)
        
    #
    # Creating directories, moving, deleting
    #
    
    def mkdir(self, path, mode):
        parent, name = self.parent(path)
        if name in parent:
            raise FuseOSError(EEXIST)
        parent.new_collection(name)

    def rmdir(self, path):
        node = self.node(path)
        if not isinstance(node, Collection):
            raise FuseOSError(ENOTDIR)
        if len(node.items()) > 0:
            raise FuseOSError(ENOTEMPTY)
        node.delete()

    def rename(self, old, new):
        old_node = self.node(old)
        new_dir, new_file = self.parent(new)
        new_node = new_dir.get(new_file)

        try:
            if new_node is None:
                # It's a move with a filename
                old_node.rename(new_dir, new_file)
            elif isinstance(new_node, Collection):
                # It's a move into a directory
                old_node.rename(new_node, old_node.name)
            else:
                # It's overwriting a file.
                # Don't allow this because it might be an editor doing
                # a rename to overwrite the file with a new version.
                # This would lose all handwritten notes associated with the file.
                raise FuseOSError(EEXIST)
        except IOError:
            # File conversion error
            traceback.print_exc()
            raise FuseOSError(EIO)

    def unlink(self, path):
        node = self.node(path)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        node.delete()

    #
    # Reading directories and statting files
    #
    
    def opendir(self, path):
        return self.fds.new(self.node(path))

    def releasedir(self, path, fd):
        self.fds.close(fd)

    def readdir(self, path, fd):
        node = self.fds.get(fd)
        if isinstance(node, Collection):
            yield "."
            yield ".."
            for file in node:
                yield file
        else:
            raise FuseOSError(ENOTDIR)

    def getattr(self, path, fd=None):
        if fd is None:
            node = self.node(path)
        else:
            node = self.fds.get(fd)

        mode = stat.S_IRUSR + stat.S_IRGRP + stat.S_IROTH
        if isinstance(node, Collection):
            mode += stat.S_IFDIR + stat.S_IXUSR + stat.S_IXGRP + stat.S_IXOTH
        else:
            mode += stat.S_IFREG
        mtime = node.mtime

        return {
            "st_mode": mode, "st_uid": os.getuid(), "st_gid": os.getgid(),
            "st_atime": mtime, "st_mtime": mtime, "st_ctime": mtime,
            "st_size": node.size }

    def statfs(self, path):
        # Just invent free space info (macOS finder seems to want them)
        bsize=512
        total=int(8192*1024*1024/bsize)
        return {"f_bsize": bsize, "f_blocks": total, "f_bavail": total, "f_bfree": total}

    #
    # chmod and chown - ignored (the default implementation raises an error -
    # this makes programs like cp complain)
    #
    
    def chmod(self, path, mode):
        pass

    def chown(self, path, uid, gid):
        pass

    #
    # Extended attributes: only 'bookmarked' supported, which sets whether the
    # document appears in the reMarkable bookmarks list
    #
    
    def listxattr(self, path):
        return ["user.bookmarked"]

    def getxattr(self, path, name, position=0):
        if name != "user.bookmarked":
            return b""

        node = self.node(path)
        if node.pinned:
            return b"yes"
        else:
            return b"no"

    def setxattr(self, path, name, value, options, position=0):
        if name != "user.bookmarked":
            return

        if value == "yes" or value == "true" or value == "1":
            pinned = True
        elif value == "no" or value == "false" or value == "0":
            pinned = False
        else:
            raise FuseOSError(ENOTSUP)

        node = self.node(path)
        node.pinned = pinned
        node.save()

def mount(mountpoint, documents, **kwargs):
    """Mount the FUSE filesystem.

    mountpoint - directory name of mount point
    documents - remarkable_fs.documents.DocumentRoot object"""

    FUSE(Remarkable(documents), mountpoint, nothreads=True, foreground=True, big_writes=True, max_write=1048576, **kwargs)
