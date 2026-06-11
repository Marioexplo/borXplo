def main(repo: str, progress: bool | None, profile: str) -> None:
    from utils import error, path
    from sys import exit
    import json
    from subprocess import run
    import backup_utils

    if not path.exists(repo):
        error(repo + " doesn't seem to exist")
    if not path.isdir(repo):
        error("A repository can't be a file!")

    config = backup_utils.load_config(path.join(repo, "config.json"), backup_utils.RepoInfo)

    print("Info about the repository that is about to be extracted:")
    borg_repo = path.join(repo, "repo")
    backup_utils.borg(["info", borg_repo])

    info = run(["borg", "info", borg_repo, "--last", "1", "--json"], capture_output=True, text=True, env=backup_utils.env)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    if progress:
        backup_utils.borg_cmd.append("--progress")
    backup_utils.borg(["extract", path.abspath(borg_repo) + "::" + archive], cwd="/")

    if config.gits:
        for git in config.gits:
            run(["git", "restore", "."], env=backup_utils.env, cwd=git)

    print("Extraction successfully completed")
