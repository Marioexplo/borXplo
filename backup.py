import typing

can_exit = True
def main(gui: bool) -> None:
    global can_exit
    from main import argv, path, HOME, CONFIG, error, read, write
    import json
    import pyudev
    import pydbus
    import os
    import subprocess
    import sys
    from datetime import datetime
    import locale
    from pathspec import PathSpec
    from last_backup import update_last

    # backupper-gui/cli communications functions
    if gui:
        import gui as _gui
        phase = _gui.set_action
        message = _gui.set_message
        borg_msg = _gui.set_borg

        def shall_exit() -> None | typing.Never:
            """Shall I exit? If not, I can_exit"""
            global can_exit
            if can_exit:
                exit()
            can_exit = True
        def read(path: str) -> str | typing.Never:
            global can_exit
            from main import read
            can_exit = False
            ret = read(path)
            shall_exit()
            return ret
        def write(path: str, text: str) -> None | typing.Never:
            global can_exit
            from main import write
            can_exit = False
            write(path, text)
            shall_exit()
    else:
        def printer(text: str) -> None:
            print(text, end="\n\n")
        phase = printer
        message = printer
        borg_msg = printer

        from main import read, write

    # get config_path
    phase("Retrievieng configuration file")
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
    def get_key(key: str, typ: typing.Type[T], d: dict = config) -> T | None | typing.Never:
        if key not in d:
            return None
        if type(d[key]) is typ:
            return d[key]
        error(f"{key} must be of  type '{typ}'")

    # get storage device
    phase("Searching for target device")
    if "--path" in argv:
        index = argv.index("--path")
        if len(argv) < index:
            error("No path was given after '--path'!")
        target_path = argv[index + 1]
    else:
        device_database = pyudev.Context()
        target_dir = get_key("target_path", str)
        if target_dir is not None:
            if path.exists(target_dir):
                error("target_path doesn't seem to be a real path")
            try:
                device = pyudev.Devices.from_device_file(device_database, target_dir)
            except pyudev.DeviceNotFoundError:
                error("No device was found at " + target_dir)
        else:
            target_label = get_key("target_label", str)
            if target_label is None:
                error("target_label or target_path must be set to find your device")
            devices: list[pyudev.Device] = list()
            key = "ID_FS_LABEL"
            storages = device_database.list_devices(subsystem="block")
            if get_key("only_usb", bool):
                storages = [i for i in storages if i.find_parent(subsystem="usb")]
            for device in storages:
                if key in device.properties and device.properties[key] == target_dir:
                    devices.append(device)
            if len(devices) == 1:
                device = devices[0]
            else:
                error(f"No device starting with '{target_dir}' was found"
                      if len(devices) == 0 else
                      f"More than one device labelled '{target_dir}' was found\nDisconnect one or change its label")

        # get device path to write
        bus = pydbus.SystemBus()
        try:
            target_path = (bus.get("org.freedesktop.UDisks2", "/org/freedesktop/UDisks2/block_devices/"
                                  + device.sys_name.replace("/", "_"))
                           .Filesistem.Mount({}))
        except Exception as e:
            error("There was an error while trying to mount the target device:\n" + str(e))
    message("Target device configured")

    def path_in_target(relative: str)->str:
        return path.join(target_path, relative)

    phase("Preparing for the backup process")
    target_directory = get_key("directory", str)
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
    progress = get_key("progress", bool)
    if progress:
        borg_command.append("--progress")
    def check_exit(returncode: int) -> None | typing.Never:
        if returncode != 0:
            message("\nBorg exited with error")
            sys.exit(returncode)
    if gui:
        def borg(args: list[str])->None|typing.Never:
            global can_exit
            can_exit = False
            process = subprocess.Popen(
                borg_command + args,
                env=env,
                stderr=subprocess.PIPE,
                text=True)
            for current_output in process.stderr: # pyright: ignore
                borg_msg(current_output)
            check_exit(process.wait())
            shall_exit()
    else:
        def borg(args: list[str])->None|typing.Never:
            process = subprocess.run(borg_command + args, env=env)
            check_exit(process.returncode)

    # configure repo
    repo_path = path_in_target("repo")
    quota = get_key("quota", float)
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
        if quota_exists:
            if not repo_quota or quota != repo_quota:
                change_quota(quota)
                set_repo_quota()
        elif repo_quota:
            change_quota(0)
            os.remove(quota_config)
    else:
        initializer = ["init", "-e", "none", repo_path]
        if quota_exists:
            initializer += ["--storage-quota", f"{quota}G"]
            set_repo_quota()
        borg(initializer)

    borg_backup = list()
    compression = get_key("compression", str)
    borg_backup += ["create", "-C", "lz4" if compression is None else compression]
    if get_key("stats", bool):
        borg_backup.append("-s")
    locale.setlocale(locale.LC_TIME, "")
    now = datetime.now()
    archive_name = f"{repo_path}::{now.strftime("%x").replace("/", ".")}-{now.strftime("%H.%M.%S")}-"
    backup_n = 0
    gits: list[str] = list()
    """The number of repos already backupped"""
    def backup(repo: dict[str,typing.Any])->None|typing.Never:
        nonlocal backup_n
        def get_repo_key(key: str, typ: type)->typing.Any|None|typing.Never:
            return get_key(key, typ, repo)
        def check_list(key: str)->list|None|typing.Never:
            lis = get_repo_key(key, list)
            if lis is None:
                return None
            if all(type(i) is str for i in lis):
               return lis
            error(f"An item in a '{key}' list was not of type str")

        # get path
        if not get_repo_key("path", str):
            error("A 'path' value must be defined for each archive")
        repo_path = path.join(HOME, repo["path"])

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

        def include(lines: list[str]) -> None:
            spec = PathSpec.from_lines("gitwildmatch", lines)
            for root, _, files in os.walk(repo_path):
                for name in files:
                    full_path = path.join(root, name)
                    rel_path = path.relpath(full_path, repo_path)
                    if spec.match_file(rel_path):
                        args.append(full_path)

        args = [archive_name + str(backup_n)]
        included = check_list("include")
        if included is None:
            args.append(repo_path)
        else:
            include(included)
        if get_repo_key("git", bool):
            args.append(path.join(repo_path, ".git"))
            gits.append(repo_path)
        excluded = check_list("exclude")
        if excluded is not None:
            for pattern in excluded:
                args += ["-e", pattern]

        borg(borg_backup + args)
        message(f"Backup number {backup_n} completed")
        backup_n += 1

    repos = get_key("repos", list)
    if repos:
        phase("Backing up...")
        for repo in repos:
            if type(repo) is not dict:
                error(f"Repo number {repos.index(repo) + 1} is not a dictionary")
        for repo in repos:
            backup(repo)
    else:
        error("'repos' must be set to backup your repositories")
    # git directories
    write(path_in_target("git_directories"), str(gits),)
    message("Backup completed")

    # compact repo
    max_archives = get_key("max_archives", int)
    if max_archives is not None:
        archives_number = subprocess.run(["borg", "list", "--short", repo_path],
                                         capture_output=True, text=True, env=env
                                         ).stdout.count("\n")
        if archives_number > max_archives:
            phase("Compacting repository")
            borg(["delete", repo_path, "--first", str(archives_number - max_archives)])
            borg(["compact", repo_path])

    update_last()
    phase("")
    message("Your files have been successfully backed up")
