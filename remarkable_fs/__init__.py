from sftp import SFTPDirectory, SFTPFile
from connection import connect
from documents import load_documents
from fs import mount

def main():
    with connect() as conn:
        dir = SFTPDirectory(conn.sftp, "/home/nick/remarkable-fs/data")
        mount("/home/nick/remarkable-fs/mount", load_documents(dir))
