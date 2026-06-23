def main(repo: str, progress: bool, yes: bool) -> None:
    from utils import path, HOME
    from sys import exit
    import json
    from subprocess import run
    import backup_utils

    config = backup_utils.load_config(path.join(repo, "borXplo"), backup_utils.RepoInfo)

    print("Info about the repository that is about to be extracted:")
    backup_utils.borg(["info", repo])
    print("borXplo configuration:")
    print(json.dumps(config.__dict__, indent=2))
    if not (yes or input("Is this ok? [Y/n] ").lower() == "y"):
        return

    info = run(["borg", "info", repo, "--last", "1", "--json"], capture_output=True, text=True, env=backup_utils.env)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    print("Extracting...")
    cwd = "/" if config.root else HOME
    if progress:
        backup_utils.borg_cmd.append("--progress")
    if config.root:
        backup_utils.borg_cmd.insert(0, "sudo")
        print("The root_extract option was used with this repository\nYou may be asked to insert your password")
    backup_utils.borg(["extract", path.abspath(repo) + "::" + archive], cwd=cwd)

    print("Restoring git repositories")
    for git in config.gits:
        run(["git", "restore", "."], env=backup_utils.env, cwd=git)

    print("Executing custom commands:")
    def exec(cmd: str, dir: str) -> None:
        print(f"Executing '{cmd}'")
        run(cmd, shell=True, env=backup_utils.env, cwd=dir)
    for cmd in config.cmd:
        exec(cmd, cwd)
    for dir, cmd in config.cmds.items():
        exec(";".join(cmd), dir)
    print("Extraction successfully completed")
