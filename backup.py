from utils import Namespace
from backup_utils import cmd_exists

def backup_args() -> None:
    """Add the arguments for backup"""
    from utils import argparser
    argparser.add_argument("--path")
    argparser.add_argument("--config")
    argparser.add_argument("profile", required=False)

def main(args: Namespace) -> None:
    from utils import call_main, PROFILES
    call_main(lambda profile: _main(args.path, args.config, profile), PROFILES, "Backing up", args)

notifier_exists = cmd_exists("notify-send")
NOTIFY_FLAGS = ["-a", "borXplo", "-i", "drive-removable-media"]
def notify(args: Namespace) -> None:
    from subprocess import run
    if (
        run(["notify-send", "It's time to back up your data!", "-A", "Back up"] + NOTIFY_FLAGS).stdout
        if args.gui and notifier_exists else
        input("It's time to back up your data!\nBack up now? [Y/n] ").lower() == "y"
    ):
        main(args)

def _main(target_path: str | None, config_path: str | None, profile: str) -> None:
    from utils import path, HOME, CONFIG, PROFILES, SHARE, error, read, write
    from backup_utils import borg, env, load_config, RepoInfo, dataclass, beartype
    import pyudev
    import backup_utils
    import subprocess
    import os
    from datetime import datetime
    import locale
    from glob import glob
    import json
    from last_backup import update_last

    # get config
    print("Retrievieng configuration file")
    @beartype
    @dataclass
    class Config():
        @beartype
        @dataclass
        class Repo():
            path: str
            include: list[str] | None = None
            exclude: list[str] | None = None
            patterns: list[str] | None = None
            git: bool = False
            directories: list[str] | None = None
            base: str | None = None
            cmd: list[str] | None = None

        repos: list[Repo]
        target_label: str | None = None
        only_usb: bool = False
        target_node: str | None = None
        directory: str | None = None
        quota: float | None = None
        check: bool = True
        full_check: int | None = None
        progress: bool = False
        stats: bool = False
        compression: str | None = None
        max_archives: int | None = None
        root: bool = False
        unmount: bool = False
        bases: dict[str, Repo] = {}

    def merge(a: dict, b: dict) -> dict:
        for key, value in b.items():
            if type(a[key]) is not None:
                value_type = type(value)
                if value_type is None:
                    continue
                if value_type is list:
                    a[key] = a[key] + value
                    continue
                elif value_type is dict:
                    merge(a[key], value)
                    continue
            a[key] = value
        return a

    GLOBAL = path.join(CONFIG, "global.json")
    config = load_config(path.join(PROFILES, profile + ".json") if config_path is None else config_path, Config)
    if path.exists(GLOBAL):
        global_opts = load_config(GLOBAL, Config)
        config = Config(**merge(global_opts.__dict__, config.__dict__))

    # get storage device
    print("Searching for target device")
    device_node: str | None = None
    if target_path is None:
        device_database = pyudev.Context()
        if config.target_node is None:
            if config.target_label is None:
                error("target_label or target_node must be set to find your device")
            devices: list[pyudev.Device] = list()
            key = "ID_FS_LABEL"
            storages = device_database.list_devices(subsystem="block")
            if config.only_usb:
                storages = [i for i in storages if i.find_parent(subsystem="usb")]
            for storage in storages:
                if key in storage.properties and storage.properties[key] == config.target_label:
                    devices.append(storage)
            if len(devices) == 1:
                device_node = devices[0].device_node
            else:
                error(f"No device named '{config.target_label}' was found"
                      if len(devices) == 0 else
                      f"More than one device labelled '{config.target_label}' was found\nDisconnect one or change its label")
        else:
            try:
                device_node = pyudev.Devices.from_device_file(device_database, config.target_node).device_node
            except pyudev.DeviceNotFoundError:
                error("No device was found at " + config.target_node)

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
                f"'{config.target_label}' points to"
                if config.target_node is None else
                f"'{config.target_node}' is"
                } a valid device")
    print("Target device configured")

    def path_in_target(relative: str)->str:
        return path.join(target_path, relative)  # pyright: ignore[reportCallIssue, reportArgumentType]

    print("Preparing for the backup process")
    if config.directory is not None:
        target_path = path_in_target(config.directory)
        if not path.isdir(target_path):
            error(config.directory + " was not a directory inside the target")

    target_path = path_in_target(profile)
    if not path.exists(target_path):
        os.mkdir(target_path)

    # configure repo
    print("Configuring backup repository")
    if config.progress:
        backup_utils.borg_cmd.append("--progress")
    REPO_CONFIG_PATH = path_in_target("borXplo")
    quota_exists = config.quota is not None
    def set_repo_quota() -> None:
        repo_config.quota = config.quota
    if path.exists(target_path):
        # integrity checks
        full_checked = False
        if config.full_check:
            FULL_COUNT = path.join(SHARE, "check_counts", profile)
            if path.exists(FULL_COUNT) and int(read(FULL_COUNT)) >= config.full_check:
                borg(["check", "--verify-data", target_path])
                write(FULL_COUNT, "0")
                full_checked = True
            else:
                write(FULL_COUNT, str(config.full_check + 1))
        if config.check and not full_checked:
            borg(["check", target_path])

        repo_config = load_config(REPO_CONFIG_PATH, RepoInfo)

        def change_quota(quota)->None:
            borg(["config", target_path, "storage_quota", f"{quota}G"])
            print("New repository quota set")
        if quota_exists:
            if not repo_config.quota or config.quota != repo_config.quota:
                change_quota(config.quota)
                set_repo_quota()
        elif repo_config.quota:
            change_quota(0)
            repo_config.quota = None

        if config.root != repo_config.root:
            error("""You should not mix backups read from ~ and /
If you need to back up some files from root, either delete this repo first or create another profile for those files""")
        os.chdir("/" if config.root else HOME)

        print("Repository configured")
    else:
        initializer = ["init", "-e", "none", target_path]
        if quota_exists:
            initializer += ["--storage-quota", f"{config.quota}G"]
            set_repo_quota()
        borg(initializer)
        repo_config = RepoInfo([], config.root, {})
        print("Repository initialized")

    # read repos
    print("Reading repos")
    locale.setlocale(locale.LC_TIME, "")
    now = datetime.now()
    backup_cmd = ["create", "-C", "lz4" if config.compression is None else config.compression]
    if config.stats:
        backup_cmd.append("-s")
    backup_cmd.append(f"{target_path}::{now.strftime("%x").replace("/", ".")}-{now.strftime("%H.%M.%S")}")
    gits: list[str] = []
    cmds: dict[str, list[str]] = {}

    pattern_args: list[str] = []
    def backup(repo: Config.Repo)->None:
        nonlocal backup_cmd, pattern_args

        # get path
        repo_path = path.realpath(repo.path)

        # .borxplo feature
        dot_config = path.join(repo_path, ".borxplo.json")
        if path.isfile(dot_config):
            repo = Config.Repo(**merge(repo.__dict__, load_config(dot_config, Config.Repo).__dict__))

        # base feature
        if repo.base:
            if repo.base in config.bases:
                base = config.bases[repo.base]
                repo = Config.Repo(**merge(base.__dict__, repo.__dict__))
            else:
                error(f"Base '{repo.base}' doesn't exist")

        # cmd feature
        if repo.cmd:
            cmds[repo_path] = repo.cmd

        # directories feature
        if repo.directories:
            dirs = repo.directories
            repo.directories = None
            for dir in dirs:
                repo.path = path.join(repo_path, dir)
                backup(repo)
            return

        if repo.include:
            for glob_path in repo.include:
                backup_cmd += [path.realpath(p) for p in glob(path.join(repo_path, glob_path))]
        elif repo.exclude or repo.patterns or not repo.git:
            backup_cmd.append(repo_path)
        if repo.git:
            backup_cmd.append(path.join(repo_path, ".git"))
            gits.append(repo_path)
        if repo.exclude:
            for pattern in repo.exclude:
                pattern_args += ["-e", path.join(repo_path, pattern)]
        if repo.patterns:
            for pattern in repo.patterns:
                action, dd, pattern = pattern.partition(":")
                if not dd:
                    error("':' wasn't found in the pattern of the repo with path " + repo_path)
                pattern_args += ["--pattern", action + dd + path.join(repo_path, pattern)]
    for repo in config.repos:
        backup(repo)
    print("Backing up...")
    borg(backup_cmd + pattern_args)

    # repo config
    repo_config.gits = gits
    repo_config.cmds = cmds
    write(REPO_CONFIG_PATH, json.dumps(repo_config))
    print("Backup completed")

    # compact repo
    if config.max_archives is not None:
        archives_number = borg(["list", "--short", target_path],
                               capture_output=True, text=True
                               ).stdout.count("\n")
        if archives_number > config.max_archives:
            print("Compacting repository")
            borg(["delete", target_path, "--first", str(archives_number - config.max_archives)])
            borg(["compact", target_path])

    update_last()
    print("Your files have been successfully backed up")

    # automatic unmounting and notifying
    if device_node:
        def unmount() -> None:
            subprocess.run(["udisksctl", "unmount", "-b", device_node], stdout=subprocess.DEVNULL, env=env)
            print(f"Device {device_node if config.target_node else config.target_label} unmounted")
        if notifier_exists:
            notify_cmd = ["notify-send", "Backup completed", "borXplo has completed the backup process."] + NOTIFY_FLAGS
            if config.unmount:
                unmount()
                notify_cmd[2] += "\nThe media can now be removed."
                subprocess.run(notify_cmd, env=env)
            else:
                notify_cmd += ["-A", "Unmount media", "-t", "7000"]
                if subprocess.run(notify_cmd, capture_output=True, text=True, env=env).stdout:
                    unmount()
        elif config.unmount:
            unmount()
