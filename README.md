# borXplo
Marioexplo's implementation of [BorgBackup, a deduplicating backup program](https://www.borgbackup.org/).

## The purpose
When using Borg alone, you would usually have to make a Shell script to automate the backup process; borXplo's purpose is to make you easily set up your backup routine in a more *declarative* way, which is writing a JSON file.  

## Features
With borXplo, you can easily:
* set up **automatic backups**.
* manage **flash drives**: you will just have to insert them, borXplo will handle the *mounting* (and optionally *unmounting*).
* save space by deciding a **maximum quota** for the size of the repository, **compression** type and **compacting**, so that older archives with data you don't need are removed.
* back up just what you need by using **patterns** or only your **git repository** which, of course, will be automatically restored upon extraction.
* set **custom commands** to be runned after an extraction.

## How to use
The first thing you want to do is create the configuration directory for borXplo, which will be `~/.config/borxplo`. Then, you are going to put two files in there: `device.json` and `whatever-name-comes-to-your-mind-first.json`. The fist one defines how borXplo will search for your exteranl storage device, and the other be a *profile* for your first backup repository, for both you will find documentation in `man 5 borxplo`; you can also write other *profiles*, the important thing is that they are respect the JSON format and end in `.json`.
After giving the informations to borXplo about what you want to be backed up, you can use `borxplo automatic` to make borXplo check if it's time to back up every time you log into your system.

## Install
Get the latest package from [GitHub](https://github.com/Marioexplo/borXplo/releases/latest)!

If you prefer installing from source, you can clone this repository, and install the dependencies in a virtual environment for python; this is what you should run:
```sh
python3.13 -m venv .venv
source .venv/bin/activate
pip install pyudev beartype
```
Other versions of Python might work, but it would be best if you used the same interpreter I use in this project.

If you would like to replicate one of the packages or you would just like to know how I build them, you can look at the [script](package/build.sh) I use.

## Requirements
* BorgBackup.
* glibc version 2.36 at least. This means that any system about or less old than Debian 12 should be okay.
* udisksctl: it usually comes preinstalled; it is needed unless you **always** give the path to the backup repository.
* libnotify: this is required only if you want to receive notifications (through `notify-send`). However it's probable that you have it installed.

## How borXplo was achieved
borXplo is entirely written in Python.  
Apart from using Borg (which should be clear at this point) through its CLI, borXplo also uses: [pyudev](https://github.com/pyudev/pyudev), a library that provides an interface to devices (like USB drives); [beartype](https://github.com/beartype/beartype), to type-check your configuration files; [PyInstaller](https://github.com/pyinstaller/pyinstaller), used to bundle borXplo.
