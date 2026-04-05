import typing

def main() -> None:
    from main import argv, path, HOME, CONFIG, error, read, write
    import json
    import pyudev
    import os
    import subprocess
    import sys
    from datetime import datetime
    import locale
    from pathspec import PathSpec
    from last_backup import update_last

    # get config_path
    print("Retrievieng configuration file")
    if "--config" in argv:
        index = argv.index("--config")
        if len(argv) < index:
            error("No config file path was given after '--config'!")
        config_path = argv[index - 1]
    else:
        config_path = path.join(CONFIG, "config.json")

    # get config
    SEEK_HELP = "\nUse \"borxplo guide\" to get help creating a config file"
    try:
        config = json.loads(read(config_path))
    except json.JSONDecodeError as e:
        error("JSON decoder exited with error: " + e.msg + SEEK_HELP)
    if type(config) is not dict:
        error("borXplo.json was not a json object!" + SEEK_HELP)

    T = typing.TypeVar("T")
    def option(key: str, typ: typing.Type[T], d: dict = config) -> T | None | typing.Never:
        if key not in d:
            return None
        if type(d[key]) is typ:
            return d[key]
        error(f"{key} must be of  type '{typ}'")

    # get storage device
    print("Searching for target device")
    device_node: str | None = None
    if "--path" in argv:
        index = argv.index("--path")
        if len(argv) < index:
            error("No path was given after '--path'!")
        target_path = argv[index + 1]
    else:
        device_database = pyudev.Context()
        target_dir = option("target_path", str)
        if target_dir is not None:
            if path.exists(target_dir):
                error("target_path doesn't seem to be a real path")
            try:
                device_node = pyudev.Devices.from_device_file(device_database, target_dir).device_node
            except pyudev.DeviceNotFoundError:
                error("No device was found at " + target_dir)
        else:
            target_label = option("target_label", str)
            if target_label is None:
                error("target_label or target_path must be set to find your device")
            devices: list[pyudev.Device] = list()
            key = "ID_FS_LABEL"
            storages = device_database.list_devices(subsystem="block")
            if option("only_usb", bool):
                storages = [i for i in storages if i.find_parent(subsystem="usb")]
            for storage in storages:
                if key in storage.properties and storage.properties[key] == target_dir:
                    devices.append(storage)
            if len(devices) == 1:
                device_node = devices[0].device_node
            else:
                error(f"No device starting with '{target_dir}' was found"
                      if len(devices) == 0 else
                      f"More than one device labelled '{target_dir}' was found\nDisconnect one or change its label")

        # get device path to write
        if type(device_node) is not str:
            error("The device directory couldn't be found")
        subprocess.run(["udisksctl", "mount", "-b", device_node], capture_output=True)
        for line in read("/proc/self/mounts"):
            parts = line.split()
            if parts[0] == device_node:
                target_path = parts[1]
                break
    print("Target device configured")

    def path_in_target(relative: str)->str:
        return path.join(target_path, relative)

    print("Preparing for the backup process")
    target_directory = option("directory", str)
    if target_directory is not None:
        target_path = path_in_target(target_directory)
        if not path.isdir(target_path):
            error(target_directory + " was not a directory inside the target")

    # prepare environment
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None) # Remove PyInstaller’s injected paths
    env.pop("LD_PRELOAD", None)
    env["PATH"] = "/usr/bin:/bin"

    # borg helper
    borg_command = ["borg"]
    progress = option("progress", bool)
    if progress:
        borg_command.append("--progress")
    def borg(args: list[str])->None|typing.Never:
        returncode = subprocess.run(borg_command + args, env=env).returncode
        if returncode != 0:
            print("Borg exited with error")
            sys.exit(returncode)

    # configure repo
    print("Configuring backup repository")
    repo_path = path_in_target("repo")
    quota = option("quota", float)
    quota_exists = quota is not None
    quota_config = path_in_target("quota")
    def set_repo_quota() -> None | typing.Never:
        write(quota_config, str( quota))
    if path.exists(repo_path):
        borg(["check", repo_path])

        repo_quota = None
        if path.exists(quota_config):
            try:
                repo_quota = float(read(quota_config))
            except ValueError:
                print("The repo's quota file held a value that could not be parsed")
        def change_quota(quota)->None:
            borg(["config", repo_path, "storage_quota", f"{quota}G"])
            print("New repository quota set")
        if quota_exists:
            if not repo_quota or quota != repo_quota:
                change_quota(quota)
                set_repo_quota()
        elif repo_quota:
            change_quota(0)
            os.remove(quota_config)
        print("Repository configured")
    else:
        initializer = ["init", "-e", "none", repo_path]
        if quota_exists:
            initializer += ["--storage-quota", f"{quota}G"]
            set_repo_quota()
        borg(initializer)
        print("Repository initialized")

    # read repos
    print("Reading repos")
    compression = option("compression", str)
    locale.setlocale(locale.LC_TIME, "")
    now = datetime.now()
    backup_cmd = ["create", "-C", "lz4" if compression is None else compression]
    if option("stats", bool):
        backup_cmd.append("-s")
    backup_cmd.append(f"{repo_path}::{now.strftime("%x").replace("/", ".")}-{now.strftime("%H.%M.%S")}")
    gits: list[str] = list()

    repos = option("repos", list)
    if not repos:
        error("'repos' must be set to backup your repositories")
    def backup(repo)->None|typing.Never:
        nonlocal backup_cmd
        if type(repo) is not dict:
            error(f"Repo number {repos.index(repo) + 1} is not a dictionary")

        def repo_option(key: str, typ: typing.Type[T])->T|None|typing.Never:
            return option(key, typ, repo)
        def get_list(key: str)->list[str]|None|typing.Never:
            lis = repo_option(key, list)
            if lis is None:
                return None
            if all(type(i) is str for i in lis):
                return lis
            error(f"An item in a '{key}' list was not of type str")

        # get path
        repo_path = repo_option("path", str)
        if not repo_path:
            error("A 'path' value must be defined for each archive")
        repo_path = path.join(HOME, repo_path)

        # directories feature
        directories = get_list("directories")
        if directories:
            del repo["directories"]
            for dir in directories:
                dir = path.join(repo_path, dir)
                if not path.isdir(dir):
                    error("A path in 'directories' was not a directory")
                new_repo = dict(repo)
                new_repo["path"] = dir
                backup(new_repo)
            return

        include = get_list("include")
        if include is None:
            backup_cmd.append(repo_path)
        else:
            # resolve patterns like git
            spec = PathSpec.from_lines("gitwildmatch", include)
            for root, _, files in os.walk(repo_path):
                for name in files:
                    full_path = path.join(root, name)
                    rel_path = path.relpath(full_path, repo_path)
                    if spec.match_file(rel_path):
                        backup_cmd.append(full_path)
        if repo_option("git", bool):
            backup_cmd.append(path.join(repo_path, ".git"))
            gits.append(repo_path)
        excluded = get_list("exclude")
        if excluded is not None:
            for pattern in excluded:
                backup_cmd += ["-e", path.join(repo_path, pattern)]
    for repo in repos:
        backup(repo)
    borg(backup_cmd)
    # git directories
    write(path_in_target("git_directories"), str(gits))
    print("Backup completed")

    # compact repo
    max_archives = option("max_archives", int)
    if max_archives is not None:
        archives_number = subprocess.run(["borg", "list", "--short", repo_path],
                                         capture_output=True, text=True, env=env
                                         ).stdout.count("\n")
        if archives_number > max_archives:
            print("Compacting repository")
            borg(["delete", repo_path, "--first", str(archives_number - max_archives)])
            borg(["compact", repo_path])

    update_last()
    print("Your files have been successfully backed up")

    # automatic unmounting and notifying
    if device_node:
        def unmount() -> None:
            subprocess.run(["udisksctl", "unmount", "-b", device_node], capture_output=True)
        notify_cmd = ["notify-send",
            "Backup completed", "borXplo has completed the backup process.",
            "-a", "borXplo",
            "-i", "removable-media",
            "-n", "media-flash"
        ]
        if option("unmount", bool):
            unmount()
            notify_cmd[2] += "\nThe media can now be removed."
            subprocess.run(notify_cmd)
        else:
            notify_cmd += ["-A", "Unmount media", "-t", "7000"]
            notify_action = False
            try:
                notify_action = subprocess.run(notify_cmd, capture_output=True, text=True).stdout
            except subprocess.TimeoutExpired:
                pass
            if notify_action:
                unmount()
