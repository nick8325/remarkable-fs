import os.path
import stat
from lazy import lazy
from StringIO import StringIO

class SFTPNode(object):
    def __init__(self, sftp, path="."):
        self.sftp = sftp
        self.path = path

    def stat(self):
        return self.sftp.stat(self.path)

class SFTPDirectory(SFTPNode):
    @lazy
    def contents(self):
        def make_entry(attr):
            fullpath = os.path.join(self.path, attr.filename)
            if stat.S_ISDIR(attr.st_mode):
                return SFTPDirectory(self.sftp, fullpath)
            else:
                return SFTPFile(self.sftp, fullpath)

        return \
           {attr.filename: make_entry(attr)
            for attr in self.sftp.listdir_attr(self.path)}

    def __getitem__(self, key):
        return self.contents[key]

    def __iter__(self):
        return iter(self.contents)

    def __contains__(self, item):
        return item in self.contents

    def items(self):
        return self.contents.items()

class SFTPFile(SFTPNode):
    def open(self):
        return self.sftp.open(self.path)

    @lazy
    def contents(self):
        return self.open().read()
