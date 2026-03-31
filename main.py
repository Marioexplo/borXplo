from sys import argv, exit
from sys import _MEIPASS as APP_FILES # pyright: ignore
import typing
from os import path, remove

def error(message: str)->typing.Never:
    print(message)
    exit(1)

HOME = path.expanduser("~")
if len(argv) == 1:
    import backup
    backup.main()
    exit()

APP_FILES: str
match argv[1]:
    case "help" | "guide":
        with open(path.join(APP_FILES, "help.txt" if argv[1] == "help" else "config.guide.txt")) as help:
            print(help.read())
    case "automatic":
        if len(argv) == 2:
            error("An integer must be given with option 'automatic'")
        n_str = argv[2]
        try:
            n = int(n_str)
        except ValueError:
            error(n_str + " is not an integer")
        AUTOSTART = path.join(HOME, ".config/autostart/borxplo.desktop")
        if n > 0:
            if not path.exists(AUTOSTART):
                with (open(path.join(APP_FILES, "automatic.desktop")) as r,
                      open(AUTOSTART, "w") as w):
                    w.write(r.read())
            try:
                with open(path.join(HOME, ".config/borXplo/automatic"), "w") as f:
                    f.write(n_str)
            except OSError as e:
                error(f"While trying to write into .config/borXplo/automatic, this error was raised: {e}")
        elif path.exists(AUTOSTART):
            if path.isfile(AUTOSTART):
                remove(AUTOSTART)
            else:
                error(AUTOSTART + " was not expected to be a directory")
