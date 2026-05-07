#!/usr/bin/env python
"""
Quick test to verify GLPK works with a simple linear model.
"""

import pyomo.environ as pyo
from pyomo.opt import SolverFactory

print("Testing GLPK solver with simple linear program...")
print()

# Create a simple linear model
model = pyo.ConcreteModel()

model.x = pyo.Var(domain=pyo.NonNegativeReals)
model.y = pyo.Var(domain=pyo.NonNegativeReals)

model.obj = pyo.Objective(expr=2*model.x + 3*model.y, sense=pyo.maximize)

model.c1 = pyo.Constraint(expr=model.x + 2*model.y <= 10)
model.c2 = pyo.Constraint(expr=2*model.x + model.y <= 12)

# Solve
solver = SolverFactory('glpk')

if not solver.available():
    print("❌ GLPK solver not available!")
    print("Install with: conda install -c conda-forge glpk")
    exit(1)

print("✅ GLPK solver found")
print("Solving...")

results = solver.solve(model, tee=True)

print()
print("=" * 50)
print("RESULTS")
print("=" * 50)
print(f"Status: {results.solver.status}")
print(f"Termination: {results.solver.termination_condition}")
print(f"x = {pyo.value(model.x):.2f}")
print(f"y = {pyo.value(model.y):.2f}")
print(f"Objective = {pyo.value(model.obj):.2f}")
print()
print("✅ GLPK works! Solver is properly installed.")
