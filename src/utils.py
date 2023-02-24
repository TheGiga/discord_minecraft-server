import os


def ensure_directory_exists(path: str) -> str:
    if not os.path.exists(path):
        os.mkdir(path)

    return path
