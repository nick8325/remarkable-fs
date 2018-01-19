from remarkable_fs.sftp import SFTPDirectory, SFTPFile
from remarkable_fs.connection import connect
from remarkable_fs.documents import load_documents
from remarkable_fs.fs import mount

def main():
    with connect() as conn:
        dir = SFTPDirectory(conn.sftp, "/home/root/.local/share/remarkable/xochitl")
        mount("/home/nick/prog/remarkable-fs/mount", load_documents(dir))
