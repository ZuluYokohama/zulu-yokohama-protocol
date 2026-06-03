#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  git_id_and_push.sh
#  Sets git identity, commits staged work, pushes branch.
#
#  BRANCH NAMING CONVENTION (ZuluYokohama Protocol):
#
#   FORMAT:  <PHASE>-<SCOPE>[-<DETAIL>]
#
#   PHASES
#     SETUP       → repo scaffolding, env, tooling
#     FEAT        → new capability or module
#     FIX         → bug / broken behaviour
#     REFACTOR    → restructure without behaviour change
#     DOCS        → documentation only
#     TEST        → tests / evidence runs
#     RELEASE     → tagged release prep
#
#   SCOPE         → short noun: e.g. ROUTER, TUI, TOPOLOGY, DDR
#   DETAIL        → optional ordinal or label: PHASE-0, v1, ALPHA
#
#   EXAMPLES:
#     SETUP-PHASE-0
#     FEAT-ROUTER-BIPARTITE
#     FIX-DDR-HARVESTER
#     DOCS-SUPERINTENDENT
#     TEST-TOPOLOGY-BASELINE
#     RELEASE-v0.1.0
#
#  RULES:
#   • ALL CAPS, hyphens only (no spaces, no slashes, no dots)
#   • Max 5 tokens, keep it scannable
#   • One concern per branch — do NOT mix FEAT + FIX
# ─────────────────────────────────────────────────────────────

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="SETUP-PHASE-0"
COMMIT_MSG="feat(setup-phase-0): add og-ep-superintendent module — DDR harvester, AFE Laplacian, topology, bipartite router, UI, evidence DDRs, full demo"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       ZuluYokohama — git identity setup          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Collect identity ──────────────────────────────────────
read -rp "  Git user.name  : " GIT_NAME
read -rp "  Git user.email : " GIT_EMAIL

if [[ -z "$GIT_NAME" || -z "$GIT_EMAIL" ]]; then
  echo "  ✗ Name and email cannot be empty. Aborting."
  exit 1
fi

git config --global user.name  "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
echo ""
echo "  ✓ Identity set → $GIT_NAME <$GIT_EMAIL>"

# ── 2. Confirm repo & branch ─────────────────────────────────
cd "$REPO_DIR"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "  ✗ Expected branch '$BRANCH', currently on '$CURRENT_BRANCH'."
  echo "    Run:  git checkout $BRANCH"
  exit 1
fi

echo "  ✓ Branch → $BRANCH"

# ── 3. Commit ────────────────────────────────────────────────
STAGED="$(git diff --cached --name-only | wc -l)"
if [[ "$STAGED" -eq 0 ]]; then
  echo "  ⚠  Nothing staged to commit — skipping commit step."
else
  git commit -m "$COMMIT_MSG"
  echo "  ✓ Committed $STAGED file(s)"
fi

# ── 4. Push ──────────────────────────────────────────────────
echo ""
echo "  Pushing to origin/$BRANCH …"
git push -u origin "$BRANCH"

echo ""
echo "  ✓ Done — branch live at:"
echo "    https://github.com/ZuluYokohama/zulu-yokohama-protocol/tree/$BRANCH"
echo ""
