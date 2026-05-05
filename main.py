from shell_utils import cmd_exists
from utils import argparser, path, error, HOME, exit
from sys import argv, _MEIPASS as APP_FILES  # pyright: ignore[reportAttributeAccessIssue]
import os

if not cmd_exists("borg"):
    error("Borg was not found. Install it before using borXplo")

del argv[0]
if len(argv) == 1 or argv[0][:2] == "--" and argv[0] != "--help":
    argparser.add_argument("--path")
    argparser.add_argument("--config")
    argparser.add_argument("--gui", action="store_true")
    args = argparser.parse_args()

    if args.gui:
        import gui
        gui.main()
    else:
        import backup
        backup.main(args.path, args.config)
    exit()

APP_FILES: str
match argv.pop(0):
    case "auto":
        from utils import AUTOMATIC, write

        argparser.add_argument("days", required=True)
        days_str: str = argparser.parse_args().days

        try:
            days = int(days_str)
        except ValueError:
            error(days_str + " is not an integer")

        autostart = path.join(HOME, ".config/autostart")
        if not path.isdir(autostart):
            if path.exists(autostart):
                error(autostart + " should not be a file!\nMove it away to allow procecesses to automatically start when you log in")
            else:
                from os import mkdir
                mkdir(autostart)

        autostart = path.join(autostart, "borxplo.desktop")
        autostart_exists = path.exists(autostart)
        if days > 0:
            if not autostart_exists:
                write(autostart, open(path.join(APP_FILES, "automatic.desktop")).read())
            write(AUTOMATIC, days_str)
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

    case "-h" | "--help" | "help":
        with open(path.join(APP_FILES, "help.txt")) as help:
            print(help.read())

    case "guide":
        with open(path.join(APP_FILES, "config.guide.txt")) as guide:
            print(guide.read())

    case _:
        error("Invalid command\nRun 'borxplo help' for a list of available commands")
