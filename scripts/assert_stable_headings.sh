#!/usr/bin/env bash
# ENG-009: run the CLI twice on the same fixture and assert all 6 H2 headings exist.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

FIXTURE="$ROOT/examples/sample-input.md"
if [[ ! -f "$FIXTURE" ]]; then
  echo "FAIL: fixture missing: $FIXTURE"
  exit 1
fi

TOPIC="$(awk '
  /^# topic[[:space:]]*$/ { flag = 1; next }
  /^# / { if (flag) exit }
  flag && $0 ~ /[^[:space:]]/ { print; exit }
' "$FIXTURE")"

MATERIALS="$(awk '
  /^# materials[[:space:]]*$/ { flag = 1; next }
  /^# / { if (flag) exit }
  flag { print }
' "$FIXTURE" | sed -e 's/[[:space:]]*$//' | awk 'NF{p=1} p')"

if [[ -z "${TOPIC}" ]]; then
  echo "FAIL: could not parse topic from $FIXTURE"
  exit 1
fi
if [[ -z "${MATERIALS}" ]]; then
  echo "FAIL: could not parse materials from $FIXTURE"
  exit 1
fi

OUT1="$(mktemp "${TMPDIR:-/tmp}/one-pager-1-XXXXXX.md")"
OUT2="$(mktemp "${TMPDIR:-/tmp}/one-pager-2-XXXXXX.md")"
cleanup() { rm -f "$OUT1" "$OUT2"; }
trap cleanup EXIT

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "FAIL: python3 not found"
  exit 1
fi

run_cli() {
  local out="$1"
  "$PY" -m decision_one_pager --topic "$TOPIC" --materials "$MATERIALS" --out "$out"
}

if ! run_cli "$OUT1"; then
  echo "FAIL: first CLI run failed"
  exit 1
fi
if ! run_cli "$OUT2"; then
  echo "FAIL: second CLI run failed"
  exit 1
fi

HEADINGS=(
  "## 问题陈述"
  "## 选项对比"
  "## 推荐"
  "## 否决或缓做"
  "## 待核实事实"
  "## 明确不做"
)

fail=0
for f in "$OUT1" "$OUT2"; do
  if [[ ! -s "$f" ]]; then
    echo "FAIL: empty output: $f" >&2
    fail=1
    continue
  fi
  for h in "${HEADINGS[@]}"; do
    if ! grep -qF "$h" "$f"; then
      echo "FAIL: missing heading in $f: $h" >&2
      fail=1
    fi
  done
done

if [[ "$fail" -ne 0 ]]; then
  echo "FAIL"
  exit 1
fi

echo "PASS"
exit 0
