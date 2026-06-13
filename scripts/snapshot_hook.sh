#!/usr/bin/env bash
# PostToolUse(Write|Edit) hook — event-driven pipeline snapshot.
# Fires ONLY when the pipeline source files are edited (series_roadmap.yaml / extracted_chapter_outlines*),
# so there's no per-turn cost on unrelated edits. Snapshot is idempotent (skips if unchanged) and runs the
# drop-off guard; on a coverage DECREASE it surfaces a loud systemMessage to the user. Never blocks the turn.
f=$(jq -r '(.tool_input.file_path // .tool_response.filePath) // empty' 2>/dev/null)
echo "$f" | grep -qE 'series_roadmap\.yaml|extracted_chapter_outlines' || exit 0
cd /home/kmangum/work-repos/sovereign-agent-starter || exit 0
SERIES_ROADMAP="$PWD/artifacts/series_roadmap.yaml" python3 scripts/pipeline_snapshot.py >/tmp/pipeline_snapshot.log 2>&1
rc=$?
if [ "$rc" = "2" ]; then
  python3 -c 'import json; print(json.dumps({"systemMessage": "⚠ PIPELINE DROP-OFF GUARD tripped — a coverage count decreased vs the prior snapshot. See /tmp/pipeline_snapshot.log"}))'
fi
exit 0
