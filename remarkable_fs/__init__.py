from paramiko.client import SSHClient, WarningPolicy
from paramiko.sftp_client import SFTPClient
import fnmatch
import json
import os.path
import stat
import time
from lazy import lazy
from StringIO import StringIO

class SFTPDirectory(object):
    def __init__(self, sftp, path="."):
        self.sftp = sftp
        self.path = path

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

    def items(self):
        return self.contents.items()

class SFTPFile(object):
    def __init__(self, sftp, path):
        self.sftp = sftp
        self.path = path

    @lazy
    def contents(self):
        stringio = StringIO()
        self.sftp.getfo(self.path, stringio)
        return stringio.getvalue()

def strip_ext(path):
    base, ext = os.path.splitext(path)
    return base

def slurp(dir):
    nodes = {}
    for path in fnmatch.filter(dir, '*.metadata'):
        id = strip_ext(path)
        nodes[id] = load_node(dir, id)
    
    directory = []
    for node in nodes.values():
        if node.parent is None:
            directory.append(node)
        else:
            nodes[node.parent].add_child(node)

    print directory
    print json.dumps(directory[0].to_json())

class Node(object):
    def __init__(self, id, name, parent):
        self.id = id
        self.name = name
        self.parent = parent

    def __load__(self, dir, id, json):
        name = json["visibleName"]
        parent = json["parent"]
        if parent == "":
            parent = None
        self.__init__(id, name, parent)

    def save(self, dir):
        dir[self.id + ".metadata"] = json.dumps(self.tojson())

    def delte(self, dir):
        del dir[self.id + ".metadata"]

    def to_json(self):
        parent = self.parent
        if parent is None:
            parent = ""
        return {
            "deleted": False,
            "lastModified": str(int(time.time()*1000)),
            "metadatamodified": True,
            "modified": True,
            "parent": parent,
            "pinned": False,
            "synced": False,
            "type": self.node_type(),
            "version": 0,
            "visibleName": self.name
        }

    def __repr__(self):
        return "%s(%s, %s)" % \
            (type(self).__name__,
             self.id,
             self.name)

class Collection(Node):
    def __init__(self, id, name, parent):
        super(Collection, self).__init__(id, name, parent)
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __repr__(self):
        return "%s(%s, %s, %s)" % \
            (type(self).__name__,
             self.id,
             self.name,
             self.children)

    @staticmethod
    def node_type():
        return "CollectionType"

class Document(Node):
    @staticmethod
    def node_type():
        return "DocumentType"

def load_node(dir, id):
    classes = [Document, Collection]
    classes_dict = {cls.node_type(): cls for cls in classes}

    data = json.loads(dir[id + ".metadata"].contents)
    try:
        cls = classes_dict[data["type"]]
    except KeyError:
        cls = Node

    node = cls.__new__(cls)
    node.__load__(dir, id, data)
    return node

def main():
    with SSHClient() as client:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(WarningPolicy)
        client.connect('localhost')
        with client.open_sftp() as sftp:
            dir = SFTPDirectory(sftp, "/home/nick/remarkable-fs/data")
            slurp(dir)
