from sys import exit
import typing
from argparse import ArgumentParser as _ArgParser, Namespace
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
    unavailable: typing.Literal["global.json", ".borXplo"],
    directory: str,
    action: str,
    args: Namespace
) -> None:
    if args.profile:
        if args.profile in ("global", ".borXplo"):
            error("A profile cannot be named " + args.profile)
        main(args.profile)
    else:
        from os import listdir
        configs = listdir(directory)
        if unavailable in configs:
            configs.remove(unavailable)
        if unavailable == "global.json":
            for i in range(len(configs)):
                if configs[i].endswith(".json"):
                    configs[i] = configs[i][:-5]
                else:
                    error("Each configuration file must have the '.json' extension")
        msg = action + " profile: "
        for profile in configs:
            print(msg + profile)
            main(profile)
            print()
