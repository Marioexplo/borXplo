# borXplo
Marioexplo's implementation of [BorgBackup, a deduplicating backup program](https://www.borgbackup.org/).
## Why?
Because I needed a software to back up my data and just setting up Borg would have been too easy.
## The purpose
borXplo is a wrapper for Borg that makes it easier to automatically back up your data on Linux.  
When using Borg alone, you would usually make a Shell script to automate the backup process; borXplo's purpose is to already include all the logic that you would usually need, so that you can easily set up your backup routine.  
Here is what borXplo aims to do:
* set up **automatic backups**.
* manage **flash drives**: you will just have to insert them, borXplo will handle the mounting (and optionally unmounting).
* easily backup your repositories by using **patterns** or just backing up the ***.git*** directory.
* lets you configure the most important Borg options.
* automatically **compact** the backup repository.

## How to use
The first thing you want to do is to make the file that will tell borXplo what to back up, and put it in `~/.config/borXplo/config.json`. You can find the instructions on how to write this file in the [guide](config.guide.txt), which is also accessible by running `borxplo guide`.
Then, run `borxplo automatic DAYS`, by putting the number of days between backups in place of DAYS.  
Now, whenever you log in, borXplo will check wether it is time to back up; if it is, it will ask you if want to back up.
## Install
Get the latest executable from [GitHub](https://github.com/Marioexplo/borXplo/releases/latest)!  
Put it in `/usr/bin` to keep borXplo easily accessible from your terminal and follow the [guide](#how-to-use) to set up automatic backups.
## Requirements
* BorgBackup.
* udisksctl: it usually comes preinstalled; it is needed unless you **always** give the path to the backup repository.
* glibc version 2.36 at least. This means that any system about or less old than Debian 12 should be okay.

## Build
If you would rather build this yourself, clone this repository and inside it do:
```
# create the virtual environment for python
python3.13 -m venv .venv

# install pyudev in the venv
source .venv/bin/activate
pip install pyudev
```
Then you can create a shell script that executes the starting script
```
.venv/bin/python main.py # remember to 'cd' or add the path to this repository
```
and put it in `/usr/local/bin`.  
___
If you would like to recreate the executable I provide (which is more portable), you can use the [Dockerfile](package/Dockerfile) and the [spec](borXplo.spec) I use
```
# create the container image that will be used to compile python against a fixed glibc
podman build -t borxplo package

# run PyInstaller
podman run --rm -v ".:/build" localhost/borxplo # add ':Z' to the mounted path if you use SELinux
```
(Docker instead of Podman will work, too). You will find the executable in `dist`.
## How borXplo was achieved
borXplo is entirely written in Python.  
Apart from using Borg (which should be clear at this point) through its CLI, borXplo also uses: [pyudev](https://github.com/pyudev/pyudev), a library that provides an interface to devices (like USB drives); [PyInstaller](https://github.com/pyinstaller/pyinstaller), used to bundle borXplo; and udisksctl, a CLI to mount and unmount devices.
