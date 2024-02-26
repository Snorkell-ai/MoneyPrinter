import os

from termcolor import colored


def clean_dir(path: str) -> None:
    """    Removes every file in a directory.

    Args:
        path (str): Path to directory.

    Raises:
        OSError: If the directory does not exist or cannot be accessed.
            The function removes every file in the specified directory. If the directory does not exist, it raises an OSError.
    """
    if not os.path.exists(path):
        os.mkdir(path)

    for file in os.listdir(path):
        os.remove(os.path.join(path, file))

    print(colored(f"[+] Cleaned {path} directory", "green"))
