def main(app_files: str) -> None:
    import os
    from sys import argv

    import backup
    from backup_utils import cmd_exists
    from utils import HOME, SHARE, argparser, call_main, error, path

    if not cmd_exists("borg"):
        error("Borg was not found. Install it before using borXplo")

    if not path.exists(SHARE):
        os.mkdir(SHARE)

    if len(argv) == 1:
        error(
            "No command was given\nUse 'borxplo help' to get the list of commands and options"
        )

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
                days = int(args.days)
            except ValueError:
                error(args.days + " is not an integer")

            autostart = path.join(HOME, ".config/autostart")
            if not path.isdir(autostart):
                if path.exists(autostart):
                    error(
                        autostart
                        + " should not be a file!\nMove it away to allow procecesses to automatically start when you log in"
                    )
                else:
                    os.mkdir(autostart)

            autostart = path.join(autostart, "borxplo.desktop")
            autostart_exists = path.exists(autostart)
            if days > 0:
                if not autostart_exists:
                    write(
                        autostart,
                        open(path.join(app_files, "automatic.desktop")).read(),  # noqa: SIM115
                    )
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
            from backup_utils import backup_repo_error, get_device, is_backup_repo

            argparser.add_argument("--progress", action="store_true")
            argparser.add_argument("-y", "--yes", action="store_true")
            argparser.add_argument("arg")
            argparser.add_argument("-p", "--profile")
            argparser.add_argument(
                "-m", "--mode", choices=["label", "node", "path"], default="label"
            )
            argparser.add_argument("--only-usb", action="store_true")
            argparser.add_argument("-d", "--directory")
            args = argparser.parse_args()

            if args.mode != "path":
                label, node = (
                    (args.arg, None) if args.mode == "label" else (None, args.arg)
                )
                _, args.arg = get_device(label, node, args.only_usb, args.directory)
            if not path.exists(args.arg):
                error(args.path + " doesn't seem to exist")
            if not path.isdir(args.arg):
                error("A repository can't be a file!")
            if not is_backup_repo(args.arg):
                backup_repo_error(args.arg)

            def handle_unavailable(repos: list[str]) -> None:
                if "borXplo" in repos:
                    repos.remove("borXplo")

            call_main(
                lambda profile: extract.main(
                    path.join(args.arg, profile), args.progress, args.yes
                ),
                handle_unavailable,
                args.arg,
                "Extracting",
                args.profile,
            )

        case "-h" | "--help" | "help":
            with open(path.join(app_files, "help.txt")) as help:
                print(help.read())

        case "version" | "--version":
            with open(path.join(app_files, "version.txt")) as v:
                print(v.read())

        case _:
            error(
                "Invalid command\nRun 'borxplo help' for a list of available commands"
            )


if __name__ == "__main__":
    from sys import _MEIPASS  # pyright: ignore[reportAttributeAccessIssue]

    main(_MEIPASS)
