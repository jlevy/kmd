# Generate README.md from the doc files.

format_markdown_template \
  kmd/docs/markdown/topics/a1_what_is_kmd.md \
  kmd/docs/markdown/topics/a2_philosophy_of_kmd.md \
  kmd/docs/markdown/topics/a3_getting_started.md \
  kmd/docs/markdown/topics/a4_tips_for_use_with_other_tools.md \
  kmd/docs/markdown/topics/a5_development.md \
  --md_template=kmd/docs/markdown/readme_template.md


save --no_frontmatter --to=README.md