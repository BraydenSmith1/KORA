# Solver Installation Guide

## The Problem

You're seeing this error:
```
RuntimeError: Attempting to use an unavailable solver.
The SolverFactory was unable to create the solver "highs"
```

This happens because Pyomo needs **solver binaries** (executables), not just Python packages.

---

## Quick Fix: Install GLPK (Easiest Option)

### Option 1: Using Conda (Recommended)

```bash
# Install conda if you don't have it
# Then install GLPK:
conda install -c conda-forge glpk

# Verify installation
glpsol --version
```

### Option 2: Using Homebrew (macOS)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install GLPK
brew install glpk

# Verify installation
glpsol --version
```

### Option 3: Using apt (Linux/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install glpk-utils

# Verify installation
glpsol --version
```

---

## Alternative: Install HiGHS Binary

### Option 1: Using Conda

```bash
conda install -c conda-forge highs
```

### Option 2: Build from source (Advanced)

```bash
git clone https://github.com/ERGO-Code/HiGHS.git
cd HiGHS
mkdir build
cd build
cmake ..
make
sudo make install

# Add to PATH
export PATH=$PATH:/usr/local/bin
```

---

## After Installing Solver

### 1. Verify Installation

```bash
cd python-optimizer
source .venv/bin/activate
python check_solvers.py
```

### 2. Update Default Solver

If you installed GLPK instead of HiGHS, update your config:

**File:** `sites/mahavelona.yaml`
```yaml
optimizer:
  solver: "glpk"  # Change from "highs" to "glpk"
```

### 3. Run Test

```bash
python run_mahavelona_pilot.py --days 1
```

---

## Using Alternative Solver Interface (No Binary Needed)

If you can't install solver binaries, use the Python-only interface:

**File:** `optimizer/kora_model.py`

Change solver from `"highs"` to `"appsi_highs"`:

```python
def solve_kora_model(
    inp: KoraOptimizerInputs,
    solver: str = "appsi_highs",  # ← Change this
    ...
)
```

This uses `highspy` Python package directly (already installed).

---

## Troubleshooting

### Check What Solvers Are Available

```bash
cd python-optimizer
source .venv/bin/activate
python check_solvers.py
```

### Common Issues

**Issue:** `glpsol: command not found`
- Solution: Solver not in PATH. Reinstall or add to PATH.

**Issue:** `appsi_highs` not working
- Solution: Update pyomo: `pip install --upgrade pyomo`

**Issue:** Solver is slow
- GLPK is slower than HiGHS. For production, use HiGHS or CBC.

---

## Solver Comparison

| Solver | Speed | Installation | Best For |
|--------|-------|--------------|----------|
| **HiGHS** | Fast | Medium | Production (recommended) |
| **GLPK** | Slow | Easy | Development, testing |
| **CBC** | Medium | Medium | Good alternative |
| **Gurobi** | Very Fast | Hard (license) | Large-scale (expensive) |

---

## Recommended Setup

### For Development/Testing:
```bash
conda install -c conda-forge glpk
# Use solver="glpk" in configs
```

### For Production:
```bash
conda install -c conda-forge highs
# Use solver="highs" in configs
```
