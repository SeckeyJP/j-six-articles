#!/usr/bin/env bash
# Replace Zenn article links with Qiita article links in qiita/public/*.md
# Reads slug -> Qiita ID mapping from qiita/public/ frontmatter

QIITA_DIR="qiita/public"
QIITA_USER="SeckeyJP"

changed=0

# First pass: collect all slug -> id mappings into a temp file
MAPFILE=$(mktemp)
for f in "$QIITA_DIR"/j-six-*.md; do
  [ -f "$f" ] || continue
  slug=$(basename "$f" .md)
  id=$(grep "^id:" "$f" | awk '{print $2}')
  if [ -n "$id" ] && [ "$id" != "null" ]; then
    echo "$slug $id" >> "$MAPFILE"
  fi
done

# Second pass: replace in each file
for f in "$QIITA_DIR"/j-six-*.md; do
  [ -f "$f" ] || continue
  while read -r slug id; do
    zenn_url="https://zenn.dev/seckeyjp/articles/$slug"
    qiita_url="https://qiita.com/$QIITA_USER/items/$id"
    if grep -q "$zenn_url" "$f"; then
      sed -i'' -e "s|$zenn_url|$qiita_url|g" "$f"
      changed=1
    fi
  done < "$MAPFILE"
done

rm -f "$MAPFILE"

if [ "$changed" -eq 1 ]; then
  echo "Replaced Zenn links with Qiita links in $QIITA_DIR"
else
  echo "No Zenn links found to replace"
fi
