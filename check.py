def main() -> None:
    import datetime
    from utils import path, error, AUTOMATIC, read, argv
    from last_backup import LAST_BACKUP, DATE_FORMAT, update_last

    if "--no-gui" in argv:
        from backup import main
    else:
        from gui import main
        import utils
        from typing import Never
        from shell_utils import cmd_exists
        from subprocess import run
        from sys import exit
        def gui_error(text: str) -> Never:
            if cmd_exists("notify-send"):
                run(["notify-send", text, "-a", "borXplo", "-i", "drive-removable-media"])
            exit(1)
        utils.error = gui_error
        error = gui_error

    if not path.exists(LAST_BACKUP):
        main()
        return

    last_backup = read(LAST_BACKUP)
    try:
        last_backup = datetime.datetime.strptime(last_backup, DATE_FORMAT).date()
    except ValueError:
        update_last()
        error("It was not possible to parse the saved date of last backup\nThe file was overwritten with today's date")

    days_index = None
    for key in ("-d", "--days"):
        if key in argv:
            days_index = argv.index(key) + 1
            break
    if days_index is None:
        if not path.exists(AUTOMATIC):
            error("No amount of days given or set by 'automatic'")
        days = read(AUTOMATIC)
    elif len(argv) > days_index:
        days = (argv[days_index])
    else:
        error("The amount of days must be provided when using " + key)  # pyright: ignore[reportPossiblyUnboundVariable]
    try:
        days = int(days)
    except ValueError:
        error("""It was not possible to parse the amount of days for the automatic backup execution
Use 'borxplo automatic' to set it again""")
    if (datetime.date.today() - last_backup).days >= days:
        main()
