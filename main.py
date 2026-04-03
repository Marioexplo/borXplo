from sys import argv, exit
from sys import _MEIPASS as APP_FILES # pyright: ignore
import typing
from os import path, remove

def _error(text: str)->typing.Never:
    print(text)
    exit(1)
error: typing.Callable[[str], typing.Never] = _error

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

def gui() -> None:
    import backup
    import gui
    from threading import Thread

    global error
    def _error(text: str) -> typing.Never:
        gui.set_message(text)
        exit()
    error = _error

    Thread(target=backup.main, args=[True]).start()
    gui.main()
    exit()

HOME = path.expanduser("~")
CONFIG = path.join(HOME, ".config/borXplo")
if len(argv) == 1 or argv[1][:2] == "--":
    import backup
    def printer(text: str) -> None:
        print(text)
        print()
    if "--gui" in argv:
        gui()
    else:
        backup.main(False)
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
                with open(path.join(APP_FILES, "automatic.desktop")) as f:
                    write(AUTOSTART, f.read())
            write(path.join(CONFIG, "automatic"), n_str)
        elif path.exists(AUTOSTART):
            if path.isfile(AUTOSTART):
                remove(AUTOSTART)
            else:
                error(AUTOSTART + " was not expected to be a directory")
    case "check":
        import check
        check.main()
