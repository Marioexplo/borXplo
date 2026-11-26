# borXplo

Marioexplo's implementation of [BorgBackup, a deduplicating backup program](https://www.borgbackup.org/).

## The purpose

When using Borg alone, you would usually have to make a Shell script to automate the backup process; borXplo's purpose is to make you easily set up your backup routine in a more _declarative_ way, which is writing a JSON file.

## Features

With borXplo, you can easily:

- set up **automatic backups**.
- manage **flash drives**: you will just have to insert them, borXplo will handle the _mounting_ (and optionally _unmounting_).
- save space with:
  - **maximum quota** for the size of the repository
  - **compression**
  - **compaction**, so that older archives with data you don't need are removed.
- back up just what you need by using **patterns** or only your **git repository** which, of course, will be automatically restored upon extraction.
- set **custom commands** to be runned after an extraction.

## How to use

The first thing you want to do is create the configuration directory for borXplo, which will be `~/.config/borxplo`. Then, you are going to put two files in there: `device.json` and `whatever-name-comes-to-your-mind.json`. The fist one defines how borXplo will search for your external storage device, and the other will be a _profile_ for your first backup repository, for both you will find documentation in `man 5 borxplo`; you can also write other _profiles_, the important thing is that they are respect the JSON format and end in `.json`.
After giving the informations to borXplo about what you want to be backed up, you can use `borxplo automatic` to make borXplo check if it's time to back up every time you log into your system.

## Install

Get the latest package from [GitHub](https://github.com/Marioexplo/borXplo/releases/latest)!

If you prefer installing from source, you can clone this repository, and install the dependencies in a virtual environment for python; this is what you should run:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Other versions of Python might work, but it would be best if you used the supported one.

## Requirements

- BorgBackup.
- glibc version 2.35 at least. This means that any system about or newer than Ubuntu 22.04 should be okay.
- udisksctl: it usually comes preinstalled; it is needed unless you **always** give the path to the backup repository.
- libnotify (optional): this is required only if you want to receive notifications (through `notify-send`). However it's probable that you have it installed.

## How borXplo was achieved

borXplo is entirely written in Python.  
Apart from evidently using Borg, borXplo also uses: [beartype](https://github.com/beartype/beartype) to type-check your configuration files, and [PyInstaller](https://github.com/pyinstaller/pyinstaller) to bundle borXplo.
