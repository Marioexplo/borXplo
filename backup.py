from utils import Namespace
from backup_utils import cmd_exists

def backup_args() -> None:
    """Add the arguments for backup"""
    from utils import argparser
    argparser.add_argument("--repo")
    argparser.add_argument("--config")
    argparser.add_argument("profile", nargs="?")

def main(args: Namespace) -> None:
    from utils import call_main, CONFIG
    if args.config:
        from utils import error, path
        if args.profile:
            error("Reading a passed configuration file does not allow the use of a profile, too")
        name: str = path.basename(args.config)
        if not name.endswith(".json"):
            error("Any configuration file must have the '.json' extension")
        args.profile = name[:-5]
    call_main(lambda profile: _main(args.repo, args.config, profile), "global.json", CONFIG, "Backing up", args)

notifier_exists = cmd_exists("notify-send")
NOTIFY_FLAGS = ["-a", "borXplo", "-i", "drive-removable-media"]
def notify(args: Namespace) -> None:
    from subprocess import run
    if (
        run(["notify-send", "It's time to back up your data!", "-A", "Back up"] + NOTIFY_FLAGS, capture_output=True).stdout
        if args.notify and notifier_exists else
        input("It's time to back up your data!\nBack up now? [Y/n] ").lower() == "y"
    ):
        main(args)

def _main(target_path: str | None, config_path: str | None, profile: str) -> None:
    from utils import path, HOME, CONFIG, SHARE, error, read, write
    from backup_utils import borg, env, load_config, RepoInfo, dataclass, is_backup_repo
    from dataclasses import field, InitVar
    from beartype import beartype
    import pyudev
    import backup_utils
    import subprocess
    import os
    from datetime import datetime
    import locale
    from typing import Literal
    import json
    from last_backup import update_last

    # get config
    print("Retrievieng configuration file")
    @dataclass
    class Config():
        @dataclass
        class Repo():
            path: str
            include: list[str] | None = None
            exclude: list[str] | None = None
            git: bool | None = None
            directories: list[str] | None = None
            base: str | None = None
            cmd: list[str] | None = None

        @dataclass
        class Base(Repo):
            path: str = field(init=False)

        class Bases(dict[str, Base]):
            from typing import Any
            def to_dict(self) -> dict[str, Any]:
                from typing import Any
                d: dict[str, Any] = self.copy()
                for key in d.keys():
                    d[key] = d[key].__dict__
                return d

        repositories: list[Repo]
        repo_bases: Bases
        target_label: str | None = None
        only_usb: bool | None = None
        target_node: str | None = None
        directory: str | None = None
        quota: float | None = None
        check: bool | None = True
        full_check: int | None = None
        progress: bool | None = None
        stats: bool | None = None
        compression: str | None = None
        max_archives: int | None = None
        default_pattern: str | None = None
        root: bool | None = None
        unmount: bool | None = None
        cmd: list[str] | None = None
    @beartype
    @dataclass
    class BearConfig(Config):
        @beartype
        class Repo(Config.Repo):
            pass

        @beartype
        class Base(Config.Base):
            pass

        repos: InitVar[list[dict] | None] = None
        repositories: list[Config.Repo] = field(init=False)
        bases: InitVar[dict[str, dict] | None] = None
        repo_bases: Config.Bases = field(init=False)

        def __post_init__(self, repos: list[dict] | None, bases: dict[str, dict] | None) -> None:
            self.repositories = [BearConfig.Repo(**repo) for repo in repos] if repos else []
            self.repo_bases = Config.Bases()
            if bases:
                for key in bases.keys():
                    self.repo_bases[key] = BearConfig.Base(**bases[key])

    def merge(a: dict, b: dict) -> dict:
        for key, value in b.items():
            if value is None:
                continue
            if a[key] is not None:
                if type(value) is list:
                    a[key] += value
                    continue
                elif type(value) is Config.Bases and a[key]:
                    a[key] = merge(a[key].to_dict(), value.to_dict())
                    continue
            a[key] = value
        return a

    if config_path:
        config = load_config(config_path, BearConfig)
    else:
        GLOBAL = path.join(CONFIG, "global.json")
        config = load_config(path.join(CONFIG, profile + ".json"), BearConfig)
        if path.exists(GLOBAL):
            global_opts = load_config(GLOBAL, BearConfig)
            config = Config(**merge(global_opts.__dict__, config.__dict__))
    if not config.repositories:
        error("""The 'repos' field was found missing or empty\nPlease fill it, otherwise, how would I know what to back up?""")

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
    else:
        target_path = path.abspath(target_path)

    def path_in_target(relative: str)->str:
        return path.join(target_path, relative)  # pyright: ignore[reportCallIssue, reportArgumentType]

    # get backup repository
    if config.directory is not None:
        target_path = path_in_target(config.directory)
        if not path.isdir(target_path):
            error(config.directory + " was not a directory inside the target")

    if not is_backup_repo(target_path):
        if os.listdir(target_path):
            from backup_utils import backup_repo_error
            backup_repo_error(target_path)
        else:
            from backup_utils import SIGN
            write(path.join(target_path, "borXplo"), SIGN)

    target_path = path_in_target(profile)
    print("Target device configured")

    # configure repo
    print("Configuring backup repository")
    if config.progress:
        backup_utils.borg_cmd.append("--progress")
    REPO_CONFIG_PATH = path_in_target("borXplo")
    quota_exists = config.quota is not None
    if path.exists(target_path):
        # integrity checks
        full_checked = False
        if config.full_check is not None:
            CHECK_COUNTS = path.join(SHARE, "check_counts")
            if not path.exists(CHECK_COUNTS):
                os.mkdir(CHECK_COUNTS)
            CHECK_COUNTS = path.join(CHECK_COUNTS, profile)
            checks = int(read(CHECK_COUNTS)) if path.exists(CHECK_COUNTS) else 0
            if checks >= config.full_check:
                borg(["check", "--verify-data", target_path])
                write(CHECK_COUNTS, "0")
                full_checked = True
                print("Full repository check completed")
            else:
                write(CHECK_COUNTS, str(checks + 1))
        if (config.check is None or config.check) and not full_checked:
            borg(["check", target_path])
            print("Repository check completed")

        repo_config = load_config(REPO_CONFIG_PATH, RepoInfo)

        def change_quota(arg)->None:
            borg(["config", target_path, "storage_quota", arg])
            print("New repository quota set")
        if quota_exists:
            if not repo_config.quota or config.quota != repo_config.quota:
                change_quota(str(config.quota) + "G")
                repo_config.quota = config.quota
        elif repo_config.quota:
            change_quota("--delete")
            repo_config.quota = None

        if repo_config.root if config.root is None else (config.root != repo_config.root):
            error("""You should not mix backups read from ~ and /
If you need to back up some files from root, either delete this repo first or create another profile for those files""")

        print("Repository configured")
    else:
        repo_config = RepoInfo(config.quota, [], False if config.root is None else config.root, [], {})
        initializer = ["init", "-e", "none", target_path]
        if quota_exists:
            initializer += ["--storage-quota", f"{config.quota}G"]
        borg(initializer)
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
    default_pattern = config.default_pattern if config.default_pattern else "sh"
    os.chdir("/" if config.root else HOME)
    def backup(repo: Config.Repo)->None:
        nonlocal backup_cmd, pattern_args

        def add_pattern(prefix: Literal["+", "-"], pattern: str, pat: str) -> None:
            nonlocal backup_cmd
            backup_cmd += ["--pattern", f"{prefix} {pattern}:{pat}"]

        def add_patterns(pats: list[str], prefix: Literal["+", "-"]) -> None:
            for pat in pats:
                pattern = default_pattern
                if ":" in pat:
                    pattern, _, pat = pat.partition(":")
                pat = path.join(repo_path, pat)
                add_pattern(prefix, pattern, pat)

        # get path
        repo_path = path.relpath(path.realpath(repo.path))

        # .borxplo feature
        dot_config = path.join(repo_path, ".borxplo.json")
        if path.isfile(dot_config):
            repo = Config.Repo(**merge(repo.__dict__, load_config(dot_config, BearConfig.Repo).__dict__))

        # directories feature
        if repo.directories:
            dirs = repo.directories
            repo.directories = None
            for dir in dirs:
                repo.path = path.join(repo_path, dir)
                backup(repo)
            return

        # cmd feature
        if repo.cmd:
            cmds[repo_path] = repo.cmd

        if repo.include:
            add_patterns(repo.include, "+")
        elif not repo.git:
            backup_cmd.append(repo_path)
        if repo.git:
            add_pattern("+", "sh", path.join(repo_path, ".git"))
            gits.append(repo_path)
        if repo.exclude:
            add_patterns(repo.exclude, "-")
    for repo in config.repositories:
        # base feature
        if repo.base:
            if repo.base in config.repo_bases:
                base = config.repo_bases[repo.base]
                if base.base:
                    error("A base can't be based on another base.\nPlese remove the 'base' field from any object in 'bases'")
                repo_dict = repo.__dict__
                repo = Config.Repo(repo_dict.pop("path"), **merge(base.__dict__, repo_dict))
            else:
                error(f"Base '{repo.base}' doesn't exist")

        backup(repo)
    print("Backing up...")
    borg(backup_cmd + pattern_args)

    # repo config
    repo_config.gits = gits
    repo_config.cmd = repo_config.cmd if repo_config.cmd else []
    repo_config.cmds = cmds
    write(REPO_CONFIG_PATH, json.dumps(repo_config.__dict__))
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
                notify_cmd += ["-A", "Unmount media"]
                if subprocess.run(notify_cmd, capture_output=True, text=True, env=env).stdout:
                    unmount()
        elif config.unmount:
            unmount()
