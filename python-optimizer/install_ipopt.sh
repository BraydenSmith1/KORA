#!/bin/bash
# IPOPT Installation Script

echo "=================================="
echo "Installing IPOPT for KORA"
echo "=================================="
echo ""

# Fix conda solver backend
echo "Step 1: Fixing conda configuration..."
conda config --set solver classic

# Install IPOPT
echo ""
echo "Step 2: Installing IPOPT..."
conda install -y -c conda-forge ipopt

# Verify installation
echo ""
echo "Step 3: Verifying IPOPT installation..."
ipopt --version

echo ""
echo "=================================="
echo "✅ Installation complete!"
echo "=================================="
echo ""
echo "Now update your config to use IPOPT:"
echo "  sed -i '' 's/solver: glpk/solver: ipopt/' sites/mahavelona.yaml"
echo ""
echo "Then test it:"
echo "  python run_mahavelona_pilot.py --days 1"
