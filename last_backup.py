from main import CONFIG, path

LAST_BACKUP = path.join(CONFIG, "last_backup")
DATE_FORMAT = "%Y.%m.%d"

def update_last() -> None:
    from datetime import date
    with open(path.join(CONFIG, "last_backup"), "w") as f:
        f.write(date.today().strftime(DATE_FORMAT))
