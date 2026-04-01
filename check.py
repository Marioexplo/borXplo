def main() -> None:
    import datetime
    from main import path, error, gui, CONFIG
    from last_backup import LAST_BACKUP, DATE_FORMAT, update_last

    with open(LAST_BACKUP) as f:
        last_backup = f.read()
    try:
        last_backup = datetime.datetime.strptime(last_backup, DATE_FORMAT).date()
    except ValueError:
        update_last()
        error("It was not possible to parse the saved date of last backup\nThe file was overwritten with today's date")
    else:
        try:
            with open(path.join(CONFIG, "automatic")) as f:
                delta = int(f.read())
        except ValueError:
            error("""It was not possible to parse the amount of days for the automatic backup execution
Use 'borxplo automatic' to set it again""")
        if delta >= (datetime.date.today() - last_backup).days:
            gui()
