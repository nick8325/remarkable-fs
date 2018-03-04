import os
import sys
from errno import *
import stat
from fuse import FUSE, FuseOSError, Operations
from remarkable_fs.documents import Collection, Document, new_collection, new_document, known_extensions
from io import BytesIO

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
        """Allocate a new file descriptor and return it.

        The file must implement save()."""
        
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
        """Close a file descriptor.

        Calls the save() method of the underlying file."""

        file = self.file_handles[fd]
        file.save()
        del self.file_handles[fd]
        self.free_file_handles.append(fd)

    def get(self, fd):
        """Look up a file descriptor. The file descriptor must be valid."""
        return self.file_handles[fd]

class Remarkable(Operations):
    def __init__(self, documents):
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
        return self.fds.new(self.node(path))

    def create(self, path, flags):
        parent, name = self.parent(path)

        # Don't allow overwriting existing files, for paranoia
        if name in parent:
            raise FuseOSError(EEXIST)

        return self.fds.new(new_document(self.documents, name, parent))

    def release(self, path, fd):
        self.fds.close(fd)

    #
    # Reading and writing files
    #
    
    def read(self, path, size, offset, fh):
        node = self.fds.get(fh)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        return self.fds.get(fh).read(offset, size)

    def write(self, path, data, offset, fh):
        node = self.fds.get(fh)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)

        # Don't allow overwriting existing files
        # (changing this needs more code in documents.py)
        if hasattr(node, "write"):
            node.write(offset, data)
        else:
            raise FuseOSError(EBADF)
        
        return len(data)

    def truncate(self, path, length, fh=None):
        if fh is None:
            node = self.node(path)
        else:
            node = self.fds.get(fh)

        # Don't allow overwriting existing files
        # (changing this needs more code in documents.py)
        if hasattr(node, "truncate"):
            node.truncate(length)
        else:
            raise FuseOSError(EBADF)
        
    #
    # Creating directories, moving, deleting
    #
    
    def mkdir(self, path, mode):
        parent, name = self.parent(path)
        if name in parent:
            raise FuseOSError(EEXIST)
        new_collection(self.documents, name, parent)

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
        node = self.node(path)
        if isinstance(node, Collection):
            raise FuseOSError(EISDIR)
        node.delete()

    #
    # Reading directories and statting files
    #
    
    opendir = open
    releasedir = release

    def readdir(self, path, fh):
        node = self.fds.get(fh)
        if isinstance(node, Collection):
            yield "."
            yield ".."
            for file in node:
                yield file
        else:
            raise FuseOSError(ENOTDIR)

    def getattr(self, path, fh=None):
        if fh is None:
            node = self.node(path)
        else:
            node = self.fds.get(fh)

        mode = stat.S_IRUSR + stat.S_IRGRP + stat.S_IROTH + stat.S_IWUSR
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
            raise FuseOSError(ENOTSUP)

        node = self.node(path)
        if node.pinned:
            return "yes"
        else:
            return "no"

    def setxattr(self, path, name, value, options, position=0):
        if name != "user.bookmarked":
            raise FuseOSError(ENOTSUP)

        if value == "yes" or value == "true" or value == "1":
            pinned = True
        elif value == "no" or value == "false" or value == "0":
            pinned = False
        else:
            raise FuseOSError(ENOTSUP)

        node = self.node(path)
        node.pinned = pinned
        node.save()

def mount(mountpoint, documents):
    FUSE(Remarkable(documents), mountpoint, nothreads=True, foreground=True, big_writes=True, max_write=1048576)
