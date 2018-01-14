from paramiko.client import SSHClient, WarningPolicy
from paramiko.sftp_client import SFTPClient
import fnmatch
import json
import os.path

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
        nodes[id] = Node(id, read_metadata(sftp, path))
    
    directory = []
    for node in nodes.values():
        if node.parent is None:
            directory.append(node)
        else:
            nodes[node.parent].add_child(node)

    print directory

class Node(object):
    def __init__(self, id, json):
        self.children = []
        self.id = id
        self.name = json["visibleName"]
        self.type = json["type"]
        self.parent = json["parent"]
        if self.parent == '':
            self.parent = None

    def add_child(self, child):
        self.children.append(child)

    def to_dict(self):
        return {"id": self.id,
                "name": self.name,
                "type": self.type,
                "children": self.children}
        
    def __str__(self):
        return str(self.to_dict())
        
    def __repr__(self):
        return repr(self.to_dict())

def main():
    with SSHClient() as client:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(WarningPolicy)
        client.connect('localhost')
        with client.open_sftp() as sftp:
            sftp.chdir("/home/nick/remarkable-fs/data")
            slurp(sftp)
