from backup_utils import cmd_exists
from utils import argparser, path, error, HOME, call_main, SHARE
from sys import argv, _MEIPASS as APP_FILES  # pyright: ignore[reportAttributeAccessIssue]
import backup
import os

if not cmd_exists("borg"):
    error("Borg was not found. Install it before using borXplo")

if not path.exists(SHARE):
    os.mkdir(SHARE)

if len(argv) == 1:
    error("No command was given\nUse 'borxplo help' to get the list of commands and options")

APP_FILES: str
match argv.pop(1):
    case "backup":
        argparser.add_argument("--notify", action="store_true")
        backup.backup_args()
        args = argparser.parse_args()
        (backup.notify if args.notify else backup.main)(args)

    case "automatic":
        from utils import AUTOMATIC, write

        argparser.add_argument("days")
        args = argparser.parse_args()
        try:
            n = int(args.days)
        except ValueError:
            error(args.days + " is not an integer")

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
            if not autostart_exists:
                write(autostart, open(path.join(APP_FILES, "automatic.desktop")).read())
            write(AUTOMATIC, args.days)
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
        from backup_utils import is_backup_repo, backup_repo_error
        argparser.add_argument("--progress", action="store_true")
        argparser.add_argument("-y", "--yes", action="store_true")
        argparser.add_argument("repo")
        argparser.add_argument("profile", nargs="?")
        args = argparser.parse_args()

        if not path.exists(args.repo):
            error(args.repo + " doesn't seem to exist")
        if not path.isdir(args.repo):
            error("A repository can't be a file!")
        if not is_backup_repo(args.repo):
            backup_repo_error(args.repo)

        call_main(
            lambda profile: extract.main(path.join(args.repo, profile), args.progress, args.yes),
            ".borXplo",
            args.repo,
            "Extracting",
            args
        )

    case "-h" | "--help" | "help":
        with open(path.join(APP_FILES, "help.txt")) as help:
            print(help.read())

    case _:
        error("Invalid command\nRun 'borxplo help' for a list of available commands")
