from sys import exit
import typing
from argparse import ArgumentParser as _ArgParser
from os import path

def error(text: str)->typing.Never:
    print(text)
    exit(1)

argparser = _ArgParser("borXplo", add_help=False)

def read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError as e:
        error(f"It was not possible to read into {path}: {e}")
def write(path: str, text: str) -> None:
    try:
        with open(path, "w") as f:
            f.write(text)
    except OSError as e:
        error(f"It was not possible to write into {path}: {e}")

def load_options(path: str) -> typing.Any:
    import json
    try:
        return json.loads(read(path))
    except json.JSONDecodeError as e:
        error("JSON decoder exited with error: " + e.msg)

HOME = path.expanduser("~")
CONFIG = path.join(HOME, ".config/borXplo")
PROFILES = path.join(CONFIG, "profiles")
AUTOMATIC = path.join(CONFIG, "automatic")
