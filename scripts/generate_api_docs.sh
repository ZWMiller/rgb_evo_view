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
    "rgb_evo_view.config"
    "rgb_evo_view.genome"
    "rgb_evo_view.creature"
    "rgb_evo_view.world"
    "rgb_evo_view.food"
    "rgb_evo_view.seeding"
    "rgb_evo_view.locomotion"
    "rgb_evo_view.energy"
    "rgb_evo_view.mating"
    "rgb_evo_view.simulation"
    "rgb_evo_view.recording"
    "visualizer.animate"
    "visualizer.stats"
)

filenames=(
    "config"
    "genome"
    "creature"
    "world"
    "food"
    "seeding"
    "locomotion"
    "energy"
    "mating"
    "simulation"
    "recording"
    "animate"
    "stats"
)

for i in "${!modules[@]}"; do
    mod="${modules[$i]}"
    fname="${filenames[$i]}"
    outfile="$OUTDIR/${fname}.md"
    echo "Generating $outfile ..."
    pydoc-markdown -m "$mod" > "$outfile"
done

echo "Done. Files written to $OUTDIR/"
