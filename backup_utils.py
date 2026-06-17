from os import environ
from shutil import which
import subprocess
from sys import exit
from utils import typing, read, error
from dataclasses import dataclass

# prepare environment
env = environ.copy()
env.pop("LD_LIBRARY_PATH", None) # Remove PyInstaller’s injected paths
env["PATH"] = "/usr/bin"

def cmd_exists(cmd: str) -> bool:
    return bool(which(cmd, path=env["PATH"]))

borg_cmd = ["borg"]
def borg(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    proc = subprocess.run(borg_cmd + cmd, env=env, **kwargs)
    if proc.returncode != 0:
        print("Borg exited with error")
        exit(proc.returncode)
    return proc

_T = typing.TypeVar("_T")
def load_config(path: str, cls: typing.Type[_T]) -> _T:
    import json
    from beartype.roar import BeartypeException
    try:
        d = json.loads(read(path))
        if type(d) is not dict:
            error(path + "was not a json object")
        return cls(**d)  # pyright: ignore[reportCallIssue]
    except (json.JSONDecodeError, BeartypeException) as e:
        error("JSON decoder exited with error: " + str(e))

@dataclass
class RepoInfo():
    quota: float | None
    gits: list[str]
    root: bool
    cmd: list[str]
    cmds: dict[str, list[str]]

SIGN = "this is a borXplo repo!"
def is_backup_repo(dir: str) -> bool:
    from utils import path
    borxplo = path.join(dir, "borXplo")
    return path.isfile(borxplo) and read(borxplo) == SIGN

def backup_repo_error(dir: str) -> None:
    from sys import stderr
    msg = dir + " does not seem to be a borXplo backup repository"
    if stderr.isatty():
        print(msg, file=stderr)
        print("Proceed anyway? [Y/n] ", file=stderr, end="")
        if input().lower() != "y":
            error("Backup aborted")
    else:
        error(msg)
