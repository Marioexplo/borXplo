from sys import exit
import typing
from argparse import ArgumentParser as _ArgParser
from os import path

def error(text: str)->typing.Never:
    from sys import stderr
    print(text, file=stderr)
    exit(1)

argparser = _ArgParser("borXplo", add_help=False, usage="See 'borxplo help' for usage details")

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
SHARE = path.join(HOME, ".local/share/borXplo")
AUTOMATIC = path.join(SHARE, "automatic")

def call_main(
    main: typing.Callable[[str], None],
    handle_unavailable: typing.Callable[[list[str]], None],
    directory: str,
    action: str,
    profile: str | None
) -> None:
    if profile:
        if profile in ("global", "borXplo", "device"):
            error("A profile cannot be named " + profile)
        main(profile)
    else:
        from os import listdir
        profiles = listdir(directory)
        handle_unavailable(profiles)
        msg = action + " profile: "
        for profile in profiles:
            print(msg + profile)
            main(profile)
            print()
