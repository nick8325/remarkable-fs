from paramiko.client import SSHClient, WarningPolicy
from paramiko.sftp_client import SFTPClient
import fnmatch
import json
import os.path
import time

def read_metadata(sftp, path):
    with sftp.open(path) as file:
        return json.loads(file.read())

def strip_ext(path):
    base, ext = os.path.splitext(path)
    return base

def slurp(sftp):
    nodes = {}
    for path in fnmatch.filter(sftp.listdir(), '*.metadata'):
        id = strip_ext(path)
        nodes[id] = create_node(id, read_metadata(sftp, path))
    
    directory = []
    for node in nodes.values():
        if node.parent is None:
            directory.append(node)
        else:
            nodes[node.parent].add_child(node)

    print directory
    print json.dumps(directory[0].to_json())

class Node(object):
    def __init__(self, id, json):
        self.children = []
        self.id = id
        self.name = json["visibleName"]
        self.parent = json["parent"]
        if self.parent == '':
            self.parent = None

    def add_child(self, child):
        self.children.append(child)

    def __repr__(self):
        return "%s(%s, %s, %s)" % \
            (type(self).__name__,
             self.id,
             self.name,
             self.children)

    def to_json(self):
        parent = self.parent
        if parent is None:
            parent = ""
        return {"deleted": False,
                "lastModified": str(int(time.time()*1000)),
                "metadatamodified": True,
                "modified": True,
                "parent": parent,
                "pinned": False,
                "synced": False,
                "type": self.node_type(),
                "version": 0,
                "visibleName": self.name}

class Document(Node):
    @staticmethod
    def node_type():
        return "DocumentType"

class Collection(Node):
    @staticmethod
    def node_type():
        return "CollectionType"

def create_node(id, json):
    classes = [Document, Collection]
    classes_dict = {cls.node_type(): cls for cls in classes}

    try:
        cls = classes_dict[json["type"]]
    except KeyError:
        cls = Node

    return cls(id, json)

def main():
    with SSHClient() as client:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(WarningPolicy)
        client.connect('localhost')
        with client.open_sftp() as sftp:
            sftp.chdir("/home/nick/remarkable-fs/data")
            slurp(sftp)
