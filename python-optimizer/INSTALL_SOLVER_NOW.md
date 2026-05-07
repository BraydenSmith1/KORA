# Quick Solver Installation - 2 Minutes

## The Problem
You're seeing errors because no solver binary is installed. The KORA model needs a Mixed-Integer Programming (MIP) solver to work.

---

## FASTEST FIX (Choose One)

### Option 1: Install via Conda (Recommended - 1 minute)

```bash
# Install Miniconda if you don't have conda
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh
# Follow prompts, restart terminal

# Install GLPK
conda install -c conda-forge glpk

# Verify
glpsol --version
```

### Option 2: Install via Homebrew (macOS - 2 minutes)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install GLPK
brew install glpk

# Verify
glpsol --version
```

### Option 3: Use Docker (5 minutes - but always works)

```bash
# Use the provided Dockerfile which has solvers pre-installed
cd python-optimizer
docker build -t kora-optimizer .
docker run -it kora-optimizer python -m optimizer.kora_model
```

---

## After Installing, Test It

```bash
cd python-optimizer
source .venv/bin/activate

# Check which solvers are now available
python check_solvers.py

# Update config to use GLPK
# Edit sites/mahavelona.yaml, line 65:
#   solver: glpk  # (change from "highs")

# Test the optimizer
python -m optimizer.kora_model
```

---

## What Solver to Use?

| Solver | Speed | Installation | Recommended For |
|--------|-------|--------------|-----------------|
| **GLPK** | Slow | Easy (conda/brew) | **Development/Testing** ✓ |
| **HiGHS** | Fast | Medium (conda) | **Production** ✓ |
| **CBC** | Medium | Medium (conda) | Alternative |

For now, use GLPK to get started. Once it works, install HiGHS for production:

```bash
conda install -c conda-forge highs
```

---

## Still Having Issues?

### Error: "conda: command not found"
```bash
# Conda isn't installed or not in PATH
# Install Miniconda (see Option 1 above)
```

### Error: "brew: command not found"
```bash
# Homebrew isn't installed
# Install Homebrew (see Option 2 above)
```

### None of these work?
Use Docker (Option 3) - it's guaranteed to work because solvers are pre-installed in the container.
