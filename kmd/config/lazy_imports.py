# TODO: Find a better way to delay importing of big packages.
# For now just doing background importing.
# Various options but none seem quite right?
# https://pypi.org/project/apipkg/
# https://scientific-python.org/specs/spec-0001/
# https://github.com/scientific-python/lazy-loader
# https://pypi.org/project/lazy-import/
# https://pypi.org/project/lazy-imports/

from lazyasd import load_module_in_background

# Non-essential but big packages.
load_module_in_background("wikipedia")
load_module_in_background("tenacity")
load_module_in_background("deepgram")
load_module_in_background("numpy")
load_module_in_background("pandas")
load_module_in_background("weasyprint")
