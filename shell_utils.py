from os import environ
from shutil import which
import subprocess
from sys import exit

# prepare environment
env = environ.copy()
env.pop("LD_LIBRARY_PATH", None) # Remove PyInstaller’s injected paths
env["PATH"] = "/usr/bin"

def cmd_exists(cmd: str) -> bool:
    return bool(which(cmd, path=env["PATH"]))

borg_cmd = ["borg"]
def borg(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    proc = subprocess.run(borg_cmd + cmd, env=env, **kwargs)
    if proc.returncode != 0:
        print("Borg exited with error")
        exit(proc.returncode)
    return proc
