from os.path import dirname, join

import utils
from main import main

dir = join(dirname(dirname(__file__)), "test")
utils.SHARE = join(dir, "share")
utils.CONFIG = join(dir, "config")
utils.AUTOMATIC = join(utils.SHARE, "automatic")

main(dir)
