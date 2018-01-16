import fnmatch
import json
import time
import os.path

def load_documents(dir):
    nodes = {}
    for path in fnmatch.filter(dir, '*.metadata'):
        id, ext = os.path.splitext(path)
        nodes[id] = load_node(dir, id)
    
    root = Root()
    nodes[root.id] = root

    for node in nodes.values():
        if node.parent is not None:
            nodes[node.parent].add_child(node)

    return root

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

class Node(object):
    def __init__(self, id, name, parent):
        self.id = id
        self.name = name
        self.parent = parent

    def __load__(self, dir, id, json):
        name = json["visibleName"]
        parent = json["parent"]
        self.__init__(id, name, parent)

    def save(self, dir):
        dir[self.id + ".metadata"] = json.dumps(self.tojson())

    def delete(self, dir):
        del dir[self.id + ".metadata"]

    def dump(self):
        return {
            "deleted": False,
            "lastModified": str(int(time.time()*1000)),
            "metadatamodified": True,
            "modified": True,
            "parent": self.parent,
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
        self.children = {}

    def add_child(self, child):
        self.children[child.name] = child

    def __repr__(self):
        return "%s(%s, %s, %s)" % \
            (type(self).__name__,
             self.id,
             self.name,
             self.children)

    def __getitem__(self, key):
        return self.children[key]

    def __iter__(self):
        return iter(self.children)

    def items(self):
        return self.children.items()

    @staticmethod
    def node_type():
        return "CollectionType"

class Root(Collection):
    def __init__(self):
        super(Root, self).__init__("", "ROOT", None)

    @staticmethod
    def node_type():
        raise TypeError, "root directory cannot be persisted"

class Document(Node):
    @staticmethod
    def node_type():
        return "DocumentType"
