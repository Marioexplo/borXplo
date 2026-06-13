from utils import SHARE, path, write

LAST_BACKUP = path.join(SHARE, "last_backup")
DATE_FORMAT = "%Y.%m.%d"

def update_last() -> None:
    from datetime import date
    write(LAST_BACKUP, date.today().strftime(DATE_FORMAT))
