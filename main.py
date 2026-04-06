from utils import argv, path, error, HOME
from sys import _MEIPASS as APP_FILES  # pyright: ignore[reportAttributeAccessIssue]
import os

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
        if len(argv) > 4:
            error("Too many arguments")

        terminal = 0
        if len(argv) == 4:
            if argv[2] == "-t" or argv[2] == "--terminal":
                terminal = 1
            else:
                error('Invalid input to enable the terminal option. Only "terminal", "true" and "0" are accepted')

        n_str = argv[2 + terminal]
        try:
            n = int(n_str)
        except ValueError:
            error(n_str + " is not an integer")

        AUTOSTART = path.join(HOME, ".config/autostart/borxplo.desktop")
        if n > 0:
            if not path.exists(AUTOSTART):
                with open(path.join(APP_FILES, "automatic.desktop")) as f:
                    write(AUTOSTART, f.read() + ("true" if terminal else "false"))
            write(AUTOMATIC, n_str)
        elif path.exists(AUTOSTART):
            if path.isfile(AUTOSTART):
                os.remove(AUTOSTART)
            else:
                error(AUTOSTART + " was not expected to be a directory")

    case "check":
        import check
        check.main()

    case _:
        error("Invalid command")
