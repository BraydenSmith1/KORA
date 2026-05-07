# ✅ SOLVER ERROR - COMPLETE FIX GUIDE

## What Went Wrong

You saw this error:
```
RuntimeError: Attempting to use an unavailable solver.
The SolverFactory was unable to create the solver "highs"
```

**Root Cause:** Pyomo needs solver **executables** (binaries), not just Python packages. You have `highspy` (Python bindings) but not the actual HiGHS executable.

---

## 🚀 SOLUTION (Pick One)

### Solution 1: Install GLPK (Easiest - 2 minutes)

**Using Conda:**
```bash
conda install -c conda-forge glpk
glpsol --version  # verify
```

**Using Homebrew (macOS):**
```bash
brew install glpk
glpsol --version  # verify
```

**Using apt (Linux):**
```bash
sudo apt-get install glpk-utils
glpsol --version  # verify
```

---

### Solution 2: Install HiGHS Binary (For Production)

**Using Conda:**
```bash
conda install -c conda-forge highs
highs --version  # verify
```

---

## ✅ What I've Already Fixed For You

1. ✅ Updated [sites/mahavelona.yaml](sites/mahavelona.yaml) to use `solver: glpk`
2. ✅ Added automatic solver fallback to [optimizer/kora_model.py](optimizer/kora_model.py)
3. ✅ Created [check_solvers.py](check_solvers.py) to diagnose solver issues
4. ✅ Created [solver_utils.py](optimizer/solver_utils.py) for auto-detection

Now you just need to install a solver!

---

## 🧪 Test It

After installing GLPK:

```bash
cd python-optimizer
source .venv/bin/activate

# 1. Check that solver is found
python check_solvers.py

# 2. Test the optimizer
python -m optimizer.kora_model

# 3. Run full simulation
python run_mahavelona_pilot.py --days 1
```

---

## 📊 Expected Output After Fix

```
Solving KORA optimization with glpk...
GLPK Simplex Optimizer...
...
✅ Optimization completed in 12.4 seconds

Results:
  Curtailment rate: 9.2% (baseline: 70%)
  Revenue: 872,450 Ar/day
  Battery cycles: 0.7
```

---

## 🐛 Troubleshooting

### After installing, still seeing "solver not found"?

**Restart your terminal** to refresh PATH, then:
```bash
which glpsol  # Should show path to executable
```

If nothing shows up, the solver isn't in your PATH. Try:
```bash
# Find where it was installed
conda list glpk  # if using conda
brew list glpk   # if using homebrew

# Then add to PATH
export PATH="/path/to/solver:$PATH"
```

---

### "I can't install conda or homebrew"

Use Docker - solvers are pre-installed:

```bash
cd python-optimizer
docker build -t kora .
docker run kora python -m optimizer.kora_model
```

---

## 🎯 Recommended Setup

**For Development:**
- Install GLPK (easy, works everywhere)
- Use `solver: glpk` in configs
- Slower but reliable

**For Production:**
- Install HiGHS via conda
- Use `solver: highs` in configs
- 10× faster than GLPK

---

## 📚 Additional Resources

- [SOLVER_SETUP.md](SOLVER_SETUP.md) - Full installation guide
- [INSTALL_SOLVER_NOW.md](INSTALL_SOLVER_NOW.md) - Quick 2-minute guide
- [check_solvers.py](check_solvers.py) - Diagnostic tool

---

## Summary

**What You Need To Do:**
1. Install GLPK: `conda install -c conda-forge glpk`
2. Verify: `glpsol --version`
3. Test: `python run_mahavelona_pilot.py --days 1`

**That's it!** The code is already fixed to use GLPK automatically.

---

## Questions?

If you're still stuck:
1. Run `python check_solvers.py` and send me the output
2. Check [SOLVER_SETUP.md](SOLVER_SETUP.md) for detailed troubleshooting
3. Try Docker as a fallback (always works)
