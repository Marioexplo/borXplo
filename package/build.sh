#!/bin/bash

cd "$(dirname "$(realpath "$0")")"

build() {
    podman run --rm -v "..:/build" localhost/borxplo  # add :Z to the mount option (-v) if you use SELinux (e.g. on Fedora)
}

pack() {
    man() {
        f=borxplo.$1.gz
        echo mans/$f=/usr/share/man/man$1/$f
    }

    fpm \
        -f \
        -n borxplo \
        -s dir \
        -t $1 \
        -v "$(cat version.txt)" \
        -d borgbackup \
        -d udisks2 \
        --description 'borXplo makes it easy to back up your data with BorgBackup, a deduplicating backup program.' \
        --license MIT \
        --url https://github.com/Marioexplo/borXplo \
        --vendor Marioexplo \
        $([[ $1 == deb ]] && echo '--deb-recommends libnotify' || [[ $1 == rpm ]] && echo '--rpm-tag Recommends:libnotify') \
        ../dist/borxplo=/opt \
        bin_link=/usr/bin/borxplo \
        $(man 1) \
        $(man 5)
}

man() {
    archiver() {
        f=../mans/borxplo.$1
        tar -czf $f.gz $f
    }
    archiver 1
    archiver 5
}

act() {
    func=$1
    shift
    for v in "$@"; do
        if [[ $arg == "$v" ]]; then
            $func $v || exit $?
            return 0
        fi
    done
    return 1
}

for arg in "$@"; do
    act pack deb rpm tar || act '' build man || (echo invalid command && exit 1)
done
