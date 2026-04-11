from os import environ
from typing import Never
from subprocess import call
from sys import exit

# prepare environment
env = environ.copy()
env.pop("LD_LIBRARY_PATH", None) # Remove PyInstaller’s injected paths
env.pop("LD_PRELOAD", None)
env["PATH"] = "/usr/bin:/bin"

def borg(cmd: list[str]) -> None | Never:
    code = call(cmd, env=env)
    if code != 0:
        print("Borg exited with error")
        exit(code)
