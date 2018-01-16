from sftp import SFTPDirectory, SFTPFile
from connection import connect
from documents import load_documents

def main():
    with connect() as conn:
        dir = SFTPDirectory(conn.sftp, "/home/nick/remarkable-fs/data")
        print load_documents(dir).children
