def main() -> None:
    from backup import backup_args, notify, notifier_exists, NOTIFY_FLAGS
    import datetime
    from utils import argparser, path, error, AUTOMATIC, read
    from last_backup import LAST_BACKUP, DATE_FORMAT, update_last

    argparser.add_argument("-d", "--days")
    argparser.add_argument("--no-notify", action="store_false", default=True, dest="notify")
    backup_args()
    args = argparser.parse_args()

    if args.notify and notifier_exists:
        import utils
        from typing import Never
        from subprocess import run
        from sys import exit
        def gui_error(text: str) -> Never:
            run(["notify-send", text] + NOTIFY_FLAGS)
            exit(1)
        utils.error = gui_error
    def main() -> None:
        notify(args)

    if not path.exists(LAST_BACKUP):
        main()
        return

    last_backup = read(LAST_BACKUP)
    try:
        last_backup = datetime.datetime.strptime(last_backup, DATE_FORMAT).date()
    except ValueError:
        update_last()
        error("It was not possible to parse the saved date of last backup\nThe file was overwritten with today's date")

    if args.days is None:
        if not path.exists(AUTOMATIC):
            error("No amount of days given or set by 'automatic'")
        days = read(AUTOMATIC)
    else:
        days = args.days
    try:
        days = int(days)
    except ValueError:
        error("""It was not possible to parse the amount of days for the automatic backup execution
Use 'borxplo automatic' to set it again""")
    if (datetime.date.today() - last_backup).days >= days:
        main()
