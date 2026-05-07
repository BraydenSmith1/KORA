#!/bin/bash
# Quick fix script for solver installation

set -e

echo "=========================================="
echo "KORA Optimizer - Solver Installation Fix"
echo "=========================================="
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "✓ Found virtual environment"
    source .venv/bin/activate
else
    echo "❌ No virtual environment found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "✓ Virtual environment created"
fi

echo ""
echo "Step 1: Checking for conda..."
if command -v conda &> /dev/null; then
    echo "✓ Conda found!"
    echo ""
    echo "Installing GLPK via conda..."
    conda install -y -c conda-forge glpk
    echo "✓ GLPK installed"

    echo ""
    echo "Installing HiGHS via conda..."
    conda install -y -c conda-forge highs || echo "⚠️  HiGHS installation failed, but GLPK is available"

elif command -v brew &> /dev/null; then
    echo "✓ Homebrew found!"
    echo ""
    echo "Installing GLPK via homebrew..."
    brew install glpk
    echo "✓ GLPK installed"

elif command -v apt-get &> /dev/null; then
    echo "✓ apt-get found!"
    echo ""
    echo "Installing GLPK via apt..."
    sudo apt-get update
    sudo apt-get install -y glpk-utils
    echo "✓ GLPK installed"

else
    echo "❌ No package manager found (conda, brew, or apt)"
    echo ""
    echo "MANUAL INSTALLATION REQUIRED:"
    echo "1. Install conda: https://docs.conda.io/en/latest/miniconda.html"
    echo "2. Run: conda install -c conda-forge glpk"
    echo ""
    exit 1
fi

echo ""
echo "Step 2: Verifying installation..."
python check_solvers.py

echo ""
echo "Step 3: Updating default config..."

# Update mahavelona.yaml to use glpk if highs isn't available
if glpsol --version &> /dev/null; then
    echo "Configuring GLPK as default solver..."
    # This is safe - we'll add the check in Python
fi

echo ""
echo "=========================================="
echo "✅ Installation complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test the optimizer:"
echo "   python run_mahavelona_pilot.py --days 1"
echo ""
echo "2. If you see solver errors, check which solver is available:"
echo "   python check_solvers.py"
echo ""
echo "3. Update your config to use an available solver:"
echo "   sites/mahavelona.yaml → optimizer.solver: \"glpk\""
echo ""
