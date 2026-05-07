# Understanding the KORA Model Issue

## What's Happening

The KORA model you're trying to run has **nonlinear terms** that GLPK cannot solve.

### The Nonlinear Term

In `optimizer/kora_model.py`, the objective function includes:
```python
revenue = sum(price[t] * demand[t] for t in T)
```

Where **BOTH** `price[t]` and `demand[t]` are **decision variables**. This creates a **bilinear term** (variable × variable), which makes the model nonlinear.

### Why This Matters

- **GLPK** = Linear Programming solver (LP/MILP only)
- **KORA model** = Nonlinear Programming (NLP/MINLP)
- ❌ GLPK cannot solve KORA

## Solutions

### Option 1: Use IPOPT (Nonlinear Solver) ⭐ RECOMMENDED

IPOPT is a free nonlinear solver that can handle the KORA model:

```bash
conda install -c conda-forge ipopt
```

Then update `sites/mahavelona.yaml`:
```yaml
optimizer:
  solver: "ipopt"  # Change from "glpk"
```

**Caveat:** IPOPT doesn't handle binary variables well (y_charge, y_discharge). We may need to relax those or use a different approach.

### Option 2: Linearize the Model (Advanced)

We can reformulate the bilinear term using:
1. **Piecewise linearization** - approximate price × demand
2. **McCormick envelopes** - standard linearization technique
3. **Discretize prices** - make price a choice from fixed levels

I can help implement this if needed.

### Option 3: Use the Simple Model (Quick Test)

Use the basic linear model (`optimizer/model.py`) with **fixed prices** first to verify everything works, then tackle the nonlinear KORA model:

```python
# This works with GLPK (linear model, fixed prices)
from optimizer.model import solve_model, OptimizerInputs
```

### Option 4: Use a Commercial Solver ($$)

- **Gurobi** (free academic license)
- **CPLEX** (free academic license)
- **BARON** (MINLP specialist)

These can handle MINLP but require licenses.

## Quick Test to Verify GLPK Works

I've created `test_glpk_simple.py` which proves GLPK is installed correctly:

```bash
python test_glpk_simple.py
```

Output:
```
✅ GLPK works! Solver is properly installed.
```

## Recommended Next Steps

### Path A: Install IPOPT (5 minutes)

```bash
conda install -c conda-forge ipopt

# Update config
sed -i '' 's/solver: glpk/solver: ipopt/' sites/mahavelona.yaml

# Test
python -m optimizer.kora_model
```

### Path B: Create Linearized KORA Model (30-60 minutes)

I can help you create `optimizer/kora_model_linear.py` that:
- Discretizes prices into 5-10 fixed levels
- Uses binary variables to select price level
- Remains linear (works with GLPK)

Which path do you want to take?

---

## Summary

✅ **GLPK is installed and working**
❌ **KORA model needs a nonlinear solver**

**Choose:**
1. Install IPOPT (easiest)
2. Linearize the model (best for GLPK)
3. Use commercial solver
