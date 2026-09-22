#!/bin/sh
# Every check, with each suite's full output kept.
#
# The batch used to print only the summary line, so when a suite came back one
# short the detail was already gone -- and a flake you cannot name is a flake
# you cannot tell from a regression. Logs land in /tmp/claude-0/suite-<name>.log.
set -u
cd "$(dirname "$0")/.."
LOGS=/tmp/claude-0
mkdir -p "$LOGS"

python3 scripts/check-schemas.py 2>&1 | tail -2
python3 scripts/check-overflow.py 2>&1 | tail -2

fails=0
for f in scripts/test-*.py; do
  n=$(basename "$f" .py)
  timeout 900 python3 "$f" > "$LOGS/suite-$n.log" 2>&1
  code=$?
  line=$(grep -E "passed" "$LOGS/suite-$n.log" | tail -1)
  printf "%-26s %s\n" "$n" "${line:-NO RESULT}"
  if [ "$code" -ne 0 ]; then
    fails=$((fails + 1))
    grep -A1 "^FAIL" "$LOGS/suite-$n.log" | sed 's/^/    /'
  fi
done
echo "DONE ($fails suite(s) failing)"
