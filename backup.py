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
    from backup_utils import get_device, borg, env, load_config, RepoInfo, dataclass, is_backup_repo
    from dataclasses import field, InitVar
    from beartype import beartype
    import backup_utils
    import subprocess
    import os
    from datetime import datetime
    import locale
    from typing import Literal
    from glob import glob
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
            patterns: list[str] | None = None
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
    target_path = (
        get_device(config.target_label, config.target_node, config.only_usb, config.directory)
        if target_path is None else
        path.abspath(target_path)
    )

    def path_in_target(relative: str)->str:
        return path.join(target_path, relative)  # pyright: ignore[reportCallIssue, reportArgumentType]

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

    includes: list[str] = []
    excludes: list[str] = []
    default_pattern = config.default_pattern if config.default_pattern else "sh"
    os.chdir("/" if config.root else HOME)
    def realpath(pat: str) -> str:
        return path.relpath(path.realpath(pat))
    def backup(repo: Config.Repo)->None:
        nonlocal backup_cmd

        def add_pattern(prefix: Literal["+", "-"], typ: str, pat: str) -> None:
            pattern = ["--pattern", f"{prefix} {typ}:{pat}"]
            if prefix == "+":
                nonlocal includes
                includes += pattern
            else:
                nonlocal excludes
                excludes += pattern
        def add_patterns(pats: list[str], prefix: Literal["+", "-"]) -> None:
            for pat in pats:
                pattern = default_pattern
                if ":" in pat:
                    pattern, _, pat = pat.partition(":")
                pat = path.join(repo_path, pat)
                add_pattern(prefix, pattern, pat)

        # get path
        repo_path = realpath(repo.path)

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
            for glob_path in repo.include:
                backup_cmd += [realpath(p) for p in glob(path.join(repo_path, glob_path), include_hidden=True)]
        else:
            backup_cmd.append(repo_path)
        if repo.exclude:
            add_patterns(repo.exclude, "-")
        if repo.patterns:
            add_patterns(repo.patterns, "+")
        if repo.git:
            if repo.include:
                error("'git' cannot be used with 'include'")
            add_pattern("+", "sh", path.join(repo_path, ".git"))
            add_pattern("-", "sh", path.join(repo_path, "*"))
            gits.append(repo_path)
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
    borg(backup_cmd + includes + excludes)

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
