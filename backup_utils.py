from os import environ
from shutil import which
import subprocess
from sys import exit
from utils import typing, read
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
    from beartype.roar import BeartypeCallHintViolation
    from utils import error
    try:
        d = json.loads(read(path))
        if type(d) is not dict:
            error(path + "was not a json object")
        return cls(**d)  # pyright: ignore[reportCallIssue]
    except (json.JSONDecodeError, TypeError, BeartypeCallHintViolation) as e:
        error(f"{
            "JSON decoder exited with error while trying to parse"
            if e is json.JSONDecodeError else
            "An error was found in"
        } {path}:\n{e}")

@dataclass
class RepoInfo():
    quota: float | None
    gits: list[str]
    root: bool
    cmd: list[str]
    cmds: dict[str, list[str]]

def get_device(label: str | None, node: str | None, only_usb: bool | None, directory: str | None) -> tuple[str, str]:
    """Returns device_node and target_path"""
    import pyudev
    from utils import path
    from utils import error

    device_database = pyudev.Context()
    if node is None:
        if label is None:
            error("label or node of your device must be given to find it")
        devices: list[pyudev.Device] = list()
        key = "ID_FS_LABEL"
        storages = device_database.list_devices(subsystem="block")
        if only_usb:
            storages = [i for i in storages if i.find_parent(subsystem="usb")]
        for storage in storages:
            if key in storage.properties and storage.properties[key] == label:
                devices.append(storage)
        if len(devices) == 1:
            device_node = devices[0].device_node
        else:
            error(f"No device named '{label}' was found"
                  if len(devices) == 0 else
                  f"More than one device labelled '{label}' was found\nDisconnect one or change its label")
    else:
        try:
            device_node = pyudev.Devices.from_device_file(device_database, node).device_node
        except pyudev.DeviceNotFoundError:
            error("No device was found at " + node)

    # get device path to write
    if type(device_node) is not str:
        error("The device directory couldn't be found")
    subprocess.run(["udisksctl", "mount", "-b", device_node], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    target_path = ""
    for line in read("/proc/self/mounts").split("\n"):
        if not line:
            continue
        parts = line.split()
        if parts[0] == device_node:
            target_path = parts[1]
            break
    if not target_path:
        error(f"It was not possible to mount {device_node}\nMake sure that {
            f"'{label}' points to"
            if node is None else
            f"'{node}' is"
            } a valid device")
    if directory is not None:
        target_path = path.join(target_path, directory)
        if not path.isdir(target_path):
            error(directory + " was not a directory inside the target")

    return (device_node, target_path)

SIGN = "this is a borXplo repo!"
def is_backup_repo(dir: str) -> bool:
    from utils import path
    borxplo = path.join(dir, "borXplo")
    return path.isfile(borxplo) and read(borxplo) == SIGN

def backup_repo_error(dir: str) -> None:
    from sys import stderr
    from utils import error
    msg = dir + " does not seem to be a borXplo backup repository"
    if stderr.isatty():
        print(msg, file=stderr)
        print("Proceed anyway? [Y/n] ", file=stderr, end="")
        if input().lower() != "y":
            error("Backup aborted")
    else:
        error(msg)
