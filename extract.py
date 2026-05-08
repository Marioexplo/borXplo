def main() -> None:
    from utils import argparser, error, path, read
    from sys import exit
    import json
    from subprocess import run
    import shell_utils

    argparser.add_argument("--progress", action="store_true")
    argparser.add_argument("repo", required=True)
    args = argparser.parse_args()

    repo = args.repo
    if not path.exists(repo):
        error(repo + " doesn't seem to exist")
    if not path.isdir(repo):
        error("A reposiroty can't be a file!")

    try:
        gits = json.loads(read(path.join(repo, "git_directories")))
    except json.JSONDecodeError as e:
        error("JSON decoder exited with error while reading git_directories: " + e.msg)
    if not (type(gits) is list and all(type(i) is str for i in gits)):
        gits = False
        print("git_directories did not contain a list of strings")
        print("Git repositories will be ignored")

    print("Info about the repository that is about to be extracted:")
    borg_repo = path.join(repo, "repo")
    shell_utils.borg(["info", borg_repo])

    info = run(["borg", "info", borg_repo, "--last", "1", "--json"], capture_output=True, text=True, env=shell_utils.env)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    if args.progress:
        shell_utils.borg_cmd.append("--progress")
    shell_utils.borg(["extract", path.abspath(borg_repo) + "::" + archive], cwd="/")

    if gits:
        for git in gits:
            run(["git", "restore", "."], env=shell_utils.env, cwd=git)

    print("Extraction successfully completed")
