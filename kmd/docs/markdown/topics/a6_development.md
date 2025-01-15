## Development

Developer setup:

```shell
# Developers should install poetry plugins to help with dev builds and updates:
poetry self update
poetry self add "poetry-dynamic-versioning[plugin]"

# Run pytests:
poetry run test
# Or within the poetry shell:
pytest   # all tests
pytest -s kmd/text_docs/text_doc.py  # one test, with outputs

# Build wheel:
poetry build

# Before committing, be sure to check formatting/linting issues:
poetry run lint

# Udate key packages:
source devtools/update_common_deps.xs

# Update this README:
source devtools/generate_readme.xsh
```

A few debugging tips when finding issues:

```shell
# To see tracebacks if xonsh does not show them:
$XONSH_SHOW_TRACEBACK=1

# To dump Python stack traces of all threads (from another terminal):
pkill -USR1 kmd
```
