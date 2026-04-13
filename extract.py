def main() -> None:
    from utils import error, path, read
    from sys import argv, exit
    import json
    from subprocess import run
    import shell_utils

    if len(argv) == 2:
        error("The path to the repo must be given!")

    cmd = ["borg"]
    progress = 0
    if len(argv) == 4 and argv[2] == "--progress":
        cmd.append(argv[2])
        progress = 1

    repo = argv[2 + progress]
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

    borg_repo = path.join(repo, "repo")
    info = shell_utils.borg(["info", borg_repo, "--last", "1", "--json"], capture_output=True, text=True)
    if info.returncode != 0:
        print(info.stderr)
        print("Borg exited with error")
        exit(info.returncode)
    archive: str = json.loads(info.stdout)["archives"][0]["name"]

    if progress == 1:
        shell_utils.borg_cmd.append("--progress")
    shell_utils.borg(["extract", path.abspath(borg_repo) + "::" + archive], cwd="/")

    if gits:
        for git in gits:
            run(["git", "restore", "."], env=shell_utils.env, cwd=git)

    print("Extraction successfully completed")
