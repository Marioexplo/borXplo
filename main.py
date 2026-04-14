from shell_utils import cmd_exists
from utils import argv, path, error, HOME, exit
from sys import _MEIPASS as APP_FILES  # pyright: ignore[reportAttributeAccessIssue]
import os

if not cmd_exists("borg"):
    error("Borg was not found. Install it before using borXplo")

if len(argv) == 1 or argv[1][:2] == "--":
    if "--gui" in argv:
        import gui
        gui.main()
    else:
        import backup
        backup.main()
    exit()

APP_FILES: str
match argv[1]:
    case "help" | "guide":
        with open(path.join(APP_FILES, "help.txt" if argv[1] == "help" else "config.guide.txt")) as help:
            print(help.read())

    case "automatic":
        from utils import AUTOMATIC, write
        if len(argv) == 2:
            error("The number of days must be given")

        n_str = argv[2]
        try:
            n = int(n_str)
        except ValueError:
            error(n_str + " is not an integer")

        autostart = path.join(HOME, ".config/autostart")
        if not path.isdir(autostart):
            if path.exists(autostart):
                error(autostart + " should not be a file!\nMove it away to allow procecesses to automatically start when you log in")
            else:
                from os import mkdir
                mkdir(autostart)

        autostart = path.join(autostart, "borxplo.desktop")
        autostart_exists = path.exists(autostart)
        if n > 0:
            if autostart_exists:
                with open(path.join(APP_FILES, "automatic.desktop")) as f:
                    write(autostart, f.read())
            write(AUTOMATIC, n_str)
        elif autostart_exists:
            if path.isfile(autostart):
                os.remove(autostart)
            else:
                error(autostart + " was not expected to be a directory")

    case "check":
        import check
        check.main()

    case "extract":
        import extract
        extract.main()

    case _:
        error("Invalid command\nRun 'borxplo help' for a list of available commands")
