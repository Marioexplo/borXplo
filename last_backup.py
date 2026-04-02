from main import CONFIG, path, write

LAST_BACKUP = path.join(CONFIG, "last_backup")
DATE_FORMAT = "%Y.%m.%d"

def update_last() -> None:
    from datetime import date
    write(path.join(CONFIG, "last_backup"), date.today().strftime(DATE_FORMAT))
