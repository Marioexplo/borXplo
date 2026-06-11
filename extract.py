def main(repo: str, progress: bool | None) -> None:
    from utils import error, path
    from sys import exit
    import json
    from subprocess import run
    import backup_utils

    if not path.exists(repo):
        error(repo + " doesn't seem to exist")
    if not path.isdir(repo):
        error("A repository can't be a file!")

    config = backup_utils.load_config(path.join(repo, "borXplo.json"), backup_utils.RepoInfo)

    print("Info about the repository that is about to be extracted:")
    backup_utils.borg(["info", repo])

    info = run(["borg", "info", repo, "--last", "1", "--json"], capture_output=True, text=True, env=backup_utils.env)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    if progress:
        backup_utils.borg_cmd.append("--progress")
    if config.root:
        backup_utils.borg_cmd.insert(0, "sudo")
        print("The root_extract option was used with this repository\nYou may be asked to insert your password")
    backup_utils.borg(["extract", path.abspath(repo) + "::" + archive], cwd="/")

    if config.gits:
        for git in config.gits:
            run(["git", "restore", "."], env=backup_utils.env, cwd=git)

    print("Extraction successfully completed")
