#!/bin/bash
# Gurobi Installation Script for KORA

echo "========================================================================"
echo "Installing Gurobi - World's Best Optimizer"
echo "========================================================================"
echo ""

# Install Gurobi via conda
echo "Step 1: Installing Gurobi package..."
conda install -y -c gurobi gurobi

# Check if installation succeeded
if [ $? -eq 0 ]; then
    echo "✅ Gurobi package installed successfully!"
else
    echo "❌ Failed to install Gurobi package"
    exit 1
fi

echo ""
echo "========================================================================"
echo "✅ Installation Complete!"
echo "========================================================================"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Get a FREE academic license:"
echo "   → Visit: https://www.gurobi.com/academia/academic-program-and-licenses/"
echo "   → Register with your university email"
echo "   → Get your license key (looks like: 12345678-1234-1234-1234-123456789abc)"
echo ""
echo "2. Activate the license:"
echo "   → Run: grbgetkey YOUR-LICENSE-KEY"
echo ""
echo "3. Test KORA:"
echo "   → Run: python run_mahavelona_pilot.py --days 1"
echo ""
echo "If you don't have a university email, use the free trial license instead:"
echo "   → Visit: https://www.gurobi.com/downloads/"
echo "   → Get a free trial license (works for 30 days)"
echo ""
