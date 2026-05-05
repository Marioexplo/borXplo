from sys import exit
import typing
from argparse import ArgumentParser as _ArgParser
from os import path

def error(text: str)->typing.Never:
    print(text)
    exit(1)

argparser = _ArgParser("borXplo", add_help=False)

def read(path: str) -> str | typing.Never:
    try:
        with open(path) as f:
            return f.read()
    except OSError as e:
        error(f"It was not possible to read into {path}: {e}")
def write(path: str, text: str) -> None | typing.Never:
    try:
        with open(path, "w") as f:
            f.write(text)
    except OSError as e:
        error(f"It was not possible to write into {path}: {e}")

HOME = path.expanduser("~")
CONFIG = path.join(HOME, ".config/borXplo")
AUTOMATIC = path.join(CONFIG, "automatic")
