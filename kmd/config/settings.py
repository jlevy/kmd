from os.path import dirname, abspath


APP_NAME = "kmd"

# Presume this file is in the main Python source folder, and use the parent folder as the root.
ROOT = dirname(dirname(dirname(abspath(__file__))))

MEDIA_CACHE_DIR = f"{ROOT}/cache/media"
