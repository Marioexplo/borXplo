def main() -> None:
    import datetime
    from main import path, error, CONFIG, read
    from last_backup import LAST_BACKUP, DATE_FORMAT, update_last
    import gui

    last_backup = read(LAST_BACKUP)
    try:
        last_backup = datetime.datetime.strptime(last_backup, DATE_FORMAT).date()
    except ValueError:
        update_last()
        error("It was not possible to parse the saved date of last backup\nThe file was overwritten with today's date")
    else:
        try:
            delta = int(read(path.join(CONFIG, "automatic")))
        except ValueError:
            error("""It was not possible to parse the amount of days for the automatic backup execution
Use 'borxplo automatic' to set it again""")
        if delta >= (datetime.date.today() - last_backup).days:
            gui.main()
