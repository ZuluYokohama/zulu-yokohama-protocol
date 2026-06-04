#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# cr_local_review.sh — LOCAL CODERABBIT AAA STUDIO REVIEW LOOP
# ZuluYokohama Protocol · Global Max Optimization · Transposed & Operational
# ──────────────────────────────────────────────────────────────────────────────
# Runs full gate stack locally before push:
#   1. ruff        — Python lint + style
#   2. shellcheck  — shell script safety
#   3. ast-grep    — structural semantic rules (ZYP math invariants)
#   4. K(S) gate   — topological coherence check
#   5. JSON/JSONL  — evidence file integrity
#   6. Summary     — CR-format verdict with shape pair harvest count
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

export PATH="$PATH:$HOME/.cargo/bin"

REPO_ROOT="$(git -C "${1:-.}" rev-parse --show-toplevel 2>/dev/null || echo "${1:-.}")"
cd "$REPO_ROOT"

RULES_DIR=".coderabbit/ast-grep/rules"
EVIDENCE_DIR="evidence/e2e"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPORT_FILE="$EVIDENCE_DIR/LOCAL_REVIEW_$(date +%Y%m%d_%H%M%S).json"
mkdir -p "$EVIDENCE_DIR"

HALT=0; TMPDIR_CR=$(mktemp -d); HALT_F="$TMPDIR_CR/halt"; WARN_F="$TMPDIR_CR/warn"; echo 0>"$HALT_F"; echo 0>"$WARN_F"
WARN=0
INFO=0
declare -a FINDINGS=()

log_finding() {
  local sev="$1" file="$2" msg="$3"
  local json_obj
  json_obj=$(jq -n --arg sev "$sev" --arg file "$file" --arg msg "$msg" '{sev:$sev,file:$file,msg:$msg}')
  FINDINGS+=("$json_obj")
  case "$sev" in
    HALT) HALT=$((HALT+1)); echo $HALT>"$HALT_F"; echo "  🔴 HALT  $file — $msg" ;;
    WARN) WARN=$((WARN+1)); echo $WARN>"$WARN_F"; echo "  ⚠️  WARN  $file — $msg" ;;
    INFO) INFO=$((INFO+1)); echo "  ℹ️  INFO  $file — $msg" ;;
  esac
}

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo " CR LOCAL REVIEW LOOP — AAA STUDIO GRADE"
echo " Repo: $REPO_ROOT"
echo " Time: $TIMESTAMP"
echo "══════════════════════════════════════════════════════════════════"

# ── GATE 1: RUFF ─────────────────────────────────────────────────────────────
echo ""
echo "── GATE 1: ruff (Python lint) ──────────────────────────────────────"
if command -v ruff &>/dev/null; then
  RUFF_OUT=$(ruff check . --output-format=json 2>/dev/null || true)
  if [ -n "$RUFF_OUT" ]; then
    while IFS='|' read -r sev loc msg; do
      log_finding "$sev" "$loc" "$msg"
    done < <(echo "$RUFF_OUT" | python3 -c "
import json,sys
items = json.load(sys.stdin)
for i in items:
    sev = 'HALT' if i.get('code','').startswith(('E9','F8','F9','W6')) else 'WARN'
    print(f\"{sev}|{i.get('filename','')}:{i.get('location',{}).get('row','?')}|{i.get('code','')} {i.get('message','')}\")
")
    RUFF_COUNT=$(echo "$RUFF_OUT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    echo "  ruff: $RUFF_COUNT findings"
  else
    echo "  ✅ ruff: clean"
  fi
else
  log_finding "WARN" "toolchain" "ruff not installed — skipping Python lint"
fi

# ── GATE 2: SHELLCHECK ───────────────────────────────────────────────────────
echo ""
echo "── GATE 2: shellcheck ──────────────────────────────────────────────"
if ! command -v shellcheck &>/dev/null; then
  log_finding "WARN" "toolchain" "shellcheck not installed — skipping shell script safety check"
  echo "  ⚠️  shellcheck: not available, skipped"
else
  SC_HITS=0
  while IFS= read -r -d '' f; do
    SC_OUT=$(shellcheck -f json "$f" 2>/dev/null || true)
    if [ -n "$SC_OUT" ]; then
      while IFS='|' read -r sev loc msg; do
        log_finding "$sev" "$loc" "$msg"
        SC_HITS=$((SC_HITS+1))
      done < <(echo "$SC_OUT" | python3 -c "
import json,sys
items = json.load(sys.stdin)
for i in items:
    sev = 'HALT' if i.get('level','') == 'error' else 'WARN'
    print(f\"{sev}|{i.get('file','')}:{i.get('line','?')}|SC{i.get('code','')} {i.get('message','')}\")
")
    fi
  done < <(find . -name "*.sh" -not -path "./.git/*" -print0)
  [ "$SC_HITS" -eq 0 ] && echo "  ✅ shellcheck: clean" || echo "  shellcheck: $SC_HITS findings"
fi

# ── GATE 3: AST-GREP SEMANTIC RULES ─────────────────────────────────────────
echo ""
echo "── GATE 3: ast-grep (ZYP semantic rules) ───────────────────────────"
if command -v sg &>/dev/null && [ -d "$RULES_DIR" ]; then
  AST_HITS=0
  for rule_file in "$RULES_DIR"/*.yml; do
    rule_id=$(grep '^id:' "$rule_file" | awk '{print $2}')
    sev_raw=$(grep 'severity:' "$rule_file" | awk '{print $2}')
    sev="WARN"
    [[ "$sev_raw" == "error" ]] && sev="HALT"
    SG_OUT=$(sg scan --rule "$rule_file" --json 2>/dev/null || true)
    if [ -n "$SG_OUT" ] && echo "$SG_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('matches',[])))" 2>/dev/null | grep -qv '^0$'; then
      while IFS='|' read -r s l g; do
        log_finding "$s" "$l" "$g"
        AST_HITS=$((AST_HITS+1))
      done < <(echo "$SG_OUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for m in d.get('matches',[]):
    loc=m.get('file','?')+':'+str(m.get('range',{}).get('start',{}).get('line','?'))
    print(f\"$sev|{loc}|[$rule_id] {m.get('message','match')}\")
")
    fi
  done
  [ "$AST_HITS" -eq 0 ] && echo "  ✅ ast-grep: all ZYP rules pass" || echo "  ast-grep: $AST_HITS semantic findings"
else
  log_finding "WARN" "toolchain" "sg (ast-grep) not in PATH or no rules dir — skipping"
fi

# ── GATE 4: K(S) TOPOLOGICAL COHERENCE ──────────────────────────────────────
echo ""
echo "── GATE 4: K(S) topological coherence ─────────────────────────────"
set +e
python3 - <<'PYGATE' 2>&1 | grep -E "✅|⚠️|🔴|PASS|WARN|HALT|lambda|holonomy"
import sys, json, glob
from pathlib import Path

REPO = Path(".")
sys.path.insert(0, str(REPO))

evidence_files = sorted(glob.glob("evidence/**/*.json", recursive=True))
ks_ok = True

for ef in evidence_files[-6:]:  # check last 6
    try:
        with open(ef) as f:
            d = json.load(f)
        lam = d.get("lambda_1", d.get("lambda1", d.get("Final_lambda_1")))
        hol = d.get("holonomy_signature", d.get("holonomy", "trivial"))
        if lam is not None:
            lam = float(lam)
            sym = "✅" if lam >= 0 else "🔴"
            print(f"  {sym} {ef}: λ₁={lam:.6f}  holonomy={hol}")
            if lam < 0:
                ks_ok = False
    except Exception as e:
        print(f"  ⚠️  {ef}: parse error — {e}")

try:
    sys.path.insert(0, str(REPO))
    from tui_layer.adapter.prime_topological_space import PrimeTopologicalSpace
    print("  ✅ tui_layer.PrimeTopologicalSpace importable")
except Exception as e:
    print(f"  ⚠️  tui_layer import: {e}")

if ks_ok:
    print("  ✅ K(S) GATE PASS — all evidence λ₁ ≥ 0")
else:
    print("  🔴 K(S) GATE HALT — negative λ₁ in evidence")
    sys.exit(1)
PYGATE
KS_EXIT=$?
set -e
if [ "$KS_EXIT" -ne 0 ]; then
  HALT=$((HALT+1))
  echo $HALT>"$HALT_F"
fi

# ── GATE 5: JSON/JSONL INTEGRITY ─────────────────────────────────────────────
echo ""
echo "── GATE 5: JSON/JSONL integrity ────────────────────────────────────"
JSON_FAILS=0
while IFS= read -r -d '' f; do
  if ! python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
    log_finding "HALT" "$f" "invalid JSON"
    JSON_FAILS=$((JSON_FAILS+1))
  fi
done < <(find . -name "*.json" -not -path "./.git/*" -not -path "*/node_modules/*" -print0)

while IFS= read -r -d '' f; do
  BAD=$(python3 -c "
import json
bad=[]
for i,l in enumerate(open('$f'),1):
    l=l.strip()
    if not l: continue
    try: json.loads(l)
    except: bad.append(i)
print(len(bad))
" 2>/dev/null || echo "0")
  if [ "$BAD" != "0" ]; then
    log_finding "HALT" "$f" "$BAD invalid JSONL lines"
    JSON_FAILS=$((JSON_FAILS+1))
  fi
done < <(find . -name "*.jsonl" -not -path "./.git/*" -print0)
[ "$JSON_FAILS" -eq 0 ] && echo "  ✅ JSON/JSONL: all valid"

# ── VERDICT ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════"

HALT=$(cat "$HALT_F" 2>/dev/null || echo 0)
WARN=$(cat "$WARN_F" 2>/dev/null || echo 0)
VERDICT="PASS"
QUALITY="quality:high"
[ "$WARN" -gt 0 ] && VERDICT="WARN" && QUALITY="quality:warn"
[ "$HALT" -gt 0 ] && VERDICT="HALT" && QUALITY="quality:halt"

echo " VERDICT: $VERDICT  ($HALT HALT · $WARN WARN · $INFO INFO)"
echo " Label:   $QUALITY"
echo "══════════════════════════════════════════════════════════════════"

# Write evidence bundle
FINDINGS_JSON=$(printf '%s\n' "${FINDINGS[@]:-}" | paste -sd,)
if ! python3 -c "
import json
from datetime import datetime, timezone
report = {
    'timestamp': '$TIMESTAMP',
    'repo': '$REPO_ROOT',
    'verdict': '$VERDICT',
    'quality_label': '$QUALITY',
    'counts': {'HALT': $HALT, 'WARN': $WARN, 'INFO': $INFO},
    'findings': json.loads('[${FINDINGS_JSON:-}]') if '${FINDINGS_JSON:-}' else []
}
with open('$REPORT_FILE','w') as f:
    json.dump(report, f, indent=2)
print(f'  Evidence: $REPORT_FILE')
"; then
  echo "ERROR: Failed to write report file $REPORT_FILE" >&2
  exit 1
fi

echo ""
[ "$HALT" -gt 0 ] && exit 1 || exit 0
