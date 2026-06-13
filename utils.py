from sys import exit
import typing
from argparse import ArgumentParser as _ArgParser, Namespace
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

HOME = path.expanduser("~")
CONFIG = path.join(HOME, ".config/borxplo")
PROFILES = path.join(CONFIG, "profiles")
SHARE = path.join(HOME, ".local/share/borXplo")
AUTOMATIC = path.join(SHARE, "automatic")

def call_main(main: typing.Callable[[str]], directory: str, action: str, args: Namespace) -> None:
    def _main(profile: str) -> None:
        if profile in ("global", ".borXplo"):
            error("A profile cannot be named " + profile)
        main(profile)
    if args.profile:
        _main(args.profile)
    else:
        from os import listdir
        msg = action + " profile: "
        for profile in listdir(directory):
            print(msg + profile)
            _main(profile)
            print()
