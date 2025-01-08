### Modern Shell Tool Recommendations

Many of us (myself included) have long believed in sticking with tried-and-true bash and
the classic command-line tools.
While it's still wise to know these tools, we've in recent years seen many new tools
emerge that are more powerful, modern, and cross-platform.

When using Kmd it makes sense to use these.

My strong recommendations:

- Use `bat` for formatting and viewing files (this is subsumed by `show` in Kmd)

- Use `eza` instead of `ls` (this is auto-aliased in Kmd)

- Use `fd` instead of `find`

- Use `fzf` (or `sk`, the Rust equivalent) for fuzzy filename searching

- Use `procs` instead of `ps`

- Use `btm` (bottom) instead of `top`

- Use `rg` (ripgrep) instead of `grep` (this is wrapped by `search` in Kmd)

- Use `z` (zoxide) instead of `cd`

- Use `delta` instead of `diff`

- Use `jq` to process JSON

- Use `tldr` as a more modern version of `man`

- Use `duf` instead of `df`

- Use `dust` instead of `du`

Kmd uses or supports several of these for better functionality, they are installed.
Use `check_tools` to check which Kmd-supported tools are already installed.

Additional recommendations:

- Consider `ranger` for file browsing

- Consider using `xh` or `httpie` instead of `curl` for using HTTP APIs, fetching JSON,
  etc.

A few examples of using modern tools in place of traditional ones:

```bash
# Use z in place of cd: switch directories (first time):
z ~/some/long/path/to/foo
# Thereafter it's faster:
z foo

# Find files by fuzzy search:
fzf

# Print all files in the current directory, recursively (and skipping
# .gitignored files):
fd 

# Find all Python files:
fd -g '*.py'

# Find all node processes except ones with Cursor on the command line:
procs | rg node | rg -v Cursor

# Show mounted disks and usage. A much prettier alternative to `df`:
duf

# Show recursive file usage, along with a visual overview. Prettier and more
# powerful than `du`:
dust
```
