#!/usr/bin/env bash
#
# run.sh — Run the full JSSP experiment pipeline
#
# Steps:
#   1. Install Python dependencies from requirements.txt
#   2. Verify the dataset (Data/starjob_1k.json) exists
#   3. Run Branch & Bound   (JSSP-Exact)
#   4. Run Simulated Annealing (JSSP-SA)
#   5. Run MWkR             (JSSP-MWkR)
#   6. Generate comparison plots (plot.py)
#
# The script stops immediately on any error.

set -e   # exit on first error

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# ── colours for terminal output ──
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'   # no colour

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

# ─────────────────────────────────────────────────────────────
# Step 1: Install requirements
# ─────────────────────────────────────────────────────────────
info "Step 1/6 — Installing Python dependencies ..."
if pip install -r requirements.txt; then
    ok "All dependencies installed successfully."
else
    fail "pip install failed. Check your Python / pip setup."
fi
echo ""

# ─────────────────────────────────────────────────────────────
# Step 2: Verify dataset exists
# ─────────────────────────────────────────────────────────────
info "Step 2/6 — Checking for dataset (Data/starjob_1k.json) ..."
if [ ! -f "Data/starjob_1k.json" ]; then
    fail "Dataset not found at Data/starjob_1k.json. Please place the file there before running."
fi
ok "Dataset found."
echo ""

# ─────────────────────────────────────────────────────────────
# Step 3: Run Branch & Bound (Exact)
# ─────────────────────────────────────────────────────────────
info "Step 3/6 — Running Branch & Bound solver (JSSP-Exact) ..."
cd "$ROOT_DIR/JSSP-Exact"
if python branch_and_bound.py; then
    ok "Branch & Bound completed. Results → JSSP-Exact/results.csv"
else
    fail "Branch & Bound solver failed."
fi
echo ""

# ─────────────────────────────────────────────────────────────
# Step 4: Run Simulated Annealing
# ─────────────────────────────────────────────────────────────
info "Step 4/6 — Running Simulated Annealing solver (JSSP-SA) ..."
cd "$ROOT_DIR/JSSP-SA"
if python sa.py; then
    ok "Simulated Annealing completed. Results → JSSP-SA/results.csv"
else
    fail "Simulated Annealing solver failed."
fi
echo ""

# ─────────────────────────────────────────────────────────────
# Step 5: Run MWkR
# ─────────────────────────────────────────────────────────────
info "Step 5/6 — Running MWkR dispatcher (JSSP-MWkR) ..."
cd "$ROOT_DIR/JSSP-MWkR"
if python mwkr.py; then
    ok "MWkR completed. Results → JSSP-MWkR/results.csv"
else
    fail "MWkR dispatcher failed."
fi
echo ""

# ─────────────────────────────────────────────────────────────
# Step 6: Generate comparison plots
# ─────────────────────────────────────────────────────────────
info "Step 6/6 — Generating comparison plots (plot.py) ..."
cd "$ROOT_DIR"
if python plot.py; then
    ok "All plots saved to ./Plots/"
else
    fail "plot.py failed."
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Pipeline completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
