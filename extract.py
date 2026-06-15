def main(repo: str, progress: bool | None) -> None:
    from utils import error, path, HOME
    from sys import exit
    import json
    from subprocess import run
    import backup_utils

    if not path.exists(repo):
        error(repo + " doesn't seem to exist")
    if not path.isdir(repo):
        error("A repository can't be a file!")
    if not backup_utils.is_backup_repo(repo):
        backup_utils.backup_repo_error(repo)

    config = backup_utils.load_config(path.join(repo, "borXplo"), backup_utils.RepoInfo)

    print("Info about the repository that is about to be extracted:")
    backup_utils.borg(["info", repo])

    info = run(["borg", "info", repo, "--last", "1", "--json"], capture_output=True, text=True, env=backup_utils.env)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    print("Extracting...")
    if progress:
        backup_utils.borg_cmd.append("--progress")
    if config.root:
        backup_utils.borg_cmd.insert(0, "sudo")
        print("The root_extract option was used with this repository\nYou may be asked to insert your password")
    backup_utils.borg(["extract", path.abspath(repo) + "::" + archive], cwd="/" if config.root else HOME)

    print("Restoring git repositories")
    for git in config.gits:
        run(["git", "restore", "."], env=backup_utils.env, cwd=git)

    print("Executing custom commands")
    for dir, cmd in config.cmds.items():
        run(";".join(cmd), shell=True, env=backup_utils.env, cwd=dir)

    print("Extraction successfully completed")
