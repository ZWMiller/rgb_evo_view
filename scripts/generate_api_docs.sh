#!/usr/bin/env bash
# Regenerate docs/api/*.md from source docstrings.
# Run from the repo root:  bash scripts/generate_api_docs.sh
# Or via poetry:           poetry run bash scripts/generate_api_docs.sh

set -euo pipefail

OUTDIR="docs/api"
mkdir -p "$OUTDIR"

# Add one entry per module you want documented. The module path is the
# dotted import path; the filename is the output basename under docs/api/.
modules=(
    # "rgb_evo_view.example"
)

filenames=(
    # "example"
)

for i in "${!modules[@]}"; do
    mod="${modules[$i]}"
    fname="${filenames[$i]}"
    outfile="$OUTDIR/${fname}.md"
    echo "Generating $outfile ..."
    pydoc-markdown -m "$mod" > "$outfile"
done

echo "Done. Files written to $OUTDIR/"
