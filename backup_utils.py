from os import environ
from shutil import which
import subprocess
from sys import exit
from utils import typing, read, error
from dataclasses import dataclass
from beartype import beartype

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

@beartype
@dataclass
class RepoInfo():
    gits: list[str]
    root: bool
    cmds: dict[str, list[str]]
    quota: float | None = None
