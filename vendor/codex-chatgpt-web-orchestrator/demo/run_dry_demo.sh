#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

echo "DRY RUN ONLY - no browser access and no prompt submission"
python3 scripts/orchestrator_cli.py plan \
  --request tests/fixtures/requests/chat-pro.json \
  --capabilities tests/fixtures/capabilities/native-all.json
python3 scripts/orchestrator_cli.py plan \
  --request tests/fixtures/requests/deep-research.json \
  --capabilities tests/fixtures/capabilities/native-all.json
python3 scripts/orchestrator_cli.py plan \
  --request tests/fixtures/requests/work.json \
  --capabilities tests/fixtures/capabilities/native-all.json
python3 scripts/orchestrator_cli.py recover \
  --state tests/fixtures/recovery/disconnected-generating.json
