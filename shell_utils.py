from os import environ
from typing import Never
import subprocess
from sys import exit

# prepare environment
env = environ.copy()
env.pop("LD_LIBRARY_PATH", None) # Remove PyInstaller’s injected paths
env.pop("LD_PRELOAD", None)
env["PATH"] = "/usr/bin:/bin"

borg_cmd = ["borg"]
def borg(cmd: list[str], **kwargs) -> subprocess.CompletedProcess | Never:
    proc = subprocess.run(borg_cmd + cmd, env=env, **kwargs)
    if proc.returncode != 0:
        print("Borg exited with error")
        exit(proc.returncode)
    return proc
