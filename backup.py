import importlib.util as py_read
from os import path
import sys
import typing
import pyudev
import subprocess
from datetime import datetime
import locale
from glob import glob

def error(message: str)->typing.Never:
    print(message)
    sys.exit(1)

# get config_path
HOME = path.expanduser("~")
config_path = HOME + ".config/borXplo.config"
if "--config" in sys.argv:
    index = sys.argv.index("--config")
    if len(sys.argv) < index:
        error("No config file path was given after '--config'!")
    config_path = sys.argv[index - 1]

# get config
spec = py_read.spec_from_file_location("config", config_path)
if not spec:
    error("No config file was found.\nUse \"borxplo guide\" to get help creating a config file")
config = py_read.module_from_spec(spec)
spec.loader.exec_module(config) # pyright: ignore

MISTYPE = object()
def check_option(name: str, typ: type)->bool|typing.Never:
    """Checks that an option of name 'name' and type 'typ' exists in config."""
    value = getattr(config, name, MISTYPE)
    if value is MISTYPE:
        return False
    if isinstance(value, typ):
        return True
    error(f"{name} must be of  type '{type}'")

# get storage device
if "--path" in sys.argv:
    index = sys.argv.index("--path")
    if len(sys.argv) < index:
        error("No path was given after '--path'!")
    target_path = sys.argv[index - 1]
else:
    device_database = pyudev.Context()
    if check_option("target_path", str):
        if path.exists(config.target_path):
            error("target_path doesn't seem to be a real path")
        try:
            device = pyudev.Devices.from_device_file(device_database, config.target_path)
        except pyudev.DeviceNotFoundError:
            error("No device was found at " + config.target_path)
    elif check_option("target_label", str):
        subsystem = "block" if getattr(config, "only_usb", True) else "usb"
        devices: list[pyudev.Device] = list()
        key = "ID_FS_LABEL"
        for device in device_database.list_devices(subsystem=subsystem):
            if key in device.properties and device.properties[key] == config.target_label:
                devices.append(device)
        match len(devices):
            case 0:
                error(f"No device starting with '{config.target_label}' was found")
            case 1:
                device = devices[0]
            case _:
                print(f"More than one device labelled '{config.target_label}' was found.\nChoose one:")
                while True:
                    for i in range(len(devices)):
                        print(f"{i}) {devices[i].properties[key]}")
                        option = input("Choose an option: ")
                        if option.isdigit() and 0 <= int(option) <= len(devices) - 1:
                            device = devices[int(option)]
                            print("Backupping to " + devices[int(option)].properties[key])
                            break
                        else:
                            print("Invalid option")
    else:
        error("target_label or target_path must be given to find your device")

    # get device path to write
    if not isinstance(device.device_node, str):
        error("The device directory couldn't be found")
    mounter = subprocess.run("udisksctl mount -b " + device.device_node, capture_output=True, text=True)
    # output is "mounted /dev/... in /path/to/device" if it got mounted, otherwise "...already mounted in `/path/to/device'."
    target_path = (mounter.stdout[mounter.stdout.find(" at ") + 4:]
                  if mounter.returncode == 0 else
                  mounter.stderr[mounter.stderr.find("`") + 1 : -2])

def path_in_target(relative: str)->str:
    return path.join(target_path, relative)

if check_option("directory", str):
    target_path = path_in_target(config.directory)

# borg helper
borg_command = ["borg"]
if check_option("progress", bool):
    borg_command.append(config.progress)
def borg(args: list[str])->subprocess.CompletedProcess|typing.Never:
    process = subprocess.run(borg_command + args)
    if process.returncode != 0:
        print("Borg exited with error")
        sys.exit(process.returncode)
    return process

# configure repo
repo_path = path_in_target("repo")
quota_exists = check_option("quota", float)
if path.exists(repo_path):
    borg(["check", repo_path])

    quota_config = path_in_target("quota")
    repo_quota = None
    if path.exists(quota_config):
        try:
            repo_quota = float(open(quota_config).read())
        except ValueError:
            print("The repo's quota file held a value that could not be parsed")
            print("Please do not modify the repo's files manually")
    def change_quota(quota)->None:
        borg(["config", repo_path, "storage_quota", str(quota)])
    if quota_exists:
        if not repo_quota or config.quota != repo_quota:
            change_quota(config.quota)
    elif quota_exists:
        change_quota(0)
else:
    initializer = ["init", "-e", "none", repo_path]
    if quota_exists:
        initializer += ["--storage-quota", config.quota]
    borg(initializer)

borg_backup = list(borg_command)
if check_option("stats", bool):
    borg_backup += ["-s"]
borg_backup += ["create", "-C", config.compression if check_option("compression", str) else "lz4"]
locale.setlocale(locale.LC_TIME, "")
archive_name = f"{repo_path}::{datetime.now().strftime("%x-%X")}"
backup_n = 0
gits: list[str] = list()
"""The number of repos already backupped"""
def backup(repo: dict[str,typing.Any])->None|typing.Never:
    global backup_n
    def check_key(key: str, typ: type)->bool|typing.Never:
        if key in repo:
            if isinstance(repo[key], typ):
                return True
            error(f"'{key}' in Repo must be of type '{typ}'")
        return False
    def check_list(key: str)->bool|typing.Never:
        if check_key(key, list):
            if len({type(i) for i in repo[key]}) == 1:
               return True
            error(f"An item in a '{key}' list was not of type str")
        return False

    # get path
    if not check_key("path", str):
        error("A 'path' value must be defined for each archive")
    repo_path = path.join(repo["path"])

    # directories feature
    if check_list("directories"):
        dirs = repo["directories"]
        del repo["directories"]
        for dir in dirs:
            dir = path.join(repo_path, dir)
            if not path.isdir(dir):
                error("A path in 'directories' was not a directory")
            new_repo = dict(repo)
            new_repo["path"] = dir
            backup(new_repo)
        return

    args = [f"{archive_name}-{backup_n}"]
    if check_list("include"):
        for glob_path in repo["include"]:
            args += [*glob(path.join(repo_path, glob_path))]
    else:
        args.append(repo_path)
    if check_key("git", bool) and repo["git"]:
        args.append(path.join(repo_path, ".git"))
        gits.append(repo_path)
    if check_list("exclude"):
        for pattern in repo["exclude"]:
            args += ["-e", pattern]

    borg(borg_backup + args)
    backup_n += 1
if check_option("repos", list):
    for repo in config.repos:
        backup(repo)
else:
    error("'repos' must be set to backup your repositories")
# git directories
with open(path_in_target("git_directories"), "w") as f:
    f.write(str(gits))

# compact repo
if check_option("max_archives", int):
    archives_number = subprocess.run(["borg", "list", "--short", repo_path],
                                     capture_output=True, text=True
                                     ).stdout.count("\n") + 1
    if archives_number > config.max_archives:
        borg(["delete", repo_path, "--first", str(archives_number - config.max_archives)])
        borg(["compact"])
