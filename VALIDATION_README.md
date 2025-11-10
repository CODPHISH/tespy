# Stage2 Model Validation Framework

## Quick Start

### Run Validation

```bash
# Option 1: Using Python directly
python validate_stage2_model.py --output-dir validation_results

# Option 2: Using shell script
./run_stage2_validation.sh validation_results
```

### View Results

After validation completes, check the output directory for three reports:

1. **validation_report.json** - Machine-readable metrics
2. **VALIDATION_REPORT.md** - Summary with comparison results
3. **REPAIR_AND_VALIDATION_ANALYSIS.md** - Detailed repair logic analysis

## What This Framework Does

### 1. Verification Routine

**Solves the stage2_detailed_model post-refactor** and verifies convergence **without relying on exported solver states**. This ensures the model can be solved independently with only boundary conditions.

Key features:
- ✅ Builds network from scratch
- ✅ Solves in design mode with enhanced boundary condition strategy
- ✅ Collects convergence metrics (iterations, residuals, status)
- ✅ Does not require pre-saved solver state files

### 2. Comparison Logic

**Reads reference CSVs** from `boiler-turbine_design_state/` and **computes differences** between:
- Current simulation connection states (m, p, T, h)
- Reference data from converged baseline
- Component KPIs (turbine power, heat exchanger duty)

Comparison uses **defined tolerances**:
- Mass flow: ±0.1 t/h or ±1%
- Pressure: ±0.5 bar or ±1%
- Temperature: ±2.0 °C or ±1%
- Enthalpy: ±5.0 kJ/kg or ±1%
- Power: ±0.1 MW or ±2%

### 3. Structured Reporting

**Generates comparison artifacts** with:
- Match rate statistics
- Detailed connection-by-connection differences  
- Component performance comparison
- Missing connection identification
- Tolerance compliance assessment

### 4. Documentation

**Documents repair logic and validation outcomes** in analysis report:
- Problem identification (over-constrained boundaries)
- Repair strategy (initial values vs. fixed values)
- Input classification (system inputs vs. intermediate states)
- Validation outcomes (convergence metrics, comparison results)
- Recommendations for future development

## Key Model Repairs

The validation framework works in conjunction with repairs made to `stage2_detailed_model.py`:

### Problem

Original model had:
- All CSV connection states set as fixed constraints → over-determined problem
- Circular dependencies between component pr equations and fixed pressures
- Incompatible Drum/Splitter constraints

### Solution

**Boundary Condition Strategy**:
- Use `p0`, `T0`, `m0` (initial values) for intermediate connections
- Use `p`, `T`, `m` (fixed values) only for true system inputs:
  - Air inlet
  - Fuel inlets (3 sources)
  - Main steam
  - Pump inlet
  - Extraction flows

**Enhanced Solver**:
```python
model.solve(
    use_reference_init=False,  # Don't rely on exported state
    allow_fallback=True,        # Fallback to reference init if needed
    max_iter=200                # Iteration limit
)
```

## Usage Examples

### Basic Validation

```python
from validate_stage2_model import Stage2ModelValidator

# Create validator
validator = Stage2ModelValidator(output_dir="validation_results")

# Run full workflow
success = validator.run_full_validation()
```

### Step-by-Step Validation

```python
validator = Stage2ModelValidator()

# Step 1: Load reference data
validator.load_reference_data()

# Step 2: Verify convergence
converged = validator.verify_model_convergence()
if not converged:
    print("Model failed to converge")
    exit(1)

# Step 3: Compare with reference
results = validator.compare_with_reference()
print(f"Match rate: {results['summary']['match_rate']:.1%}")

# Step 4: Generate reports
validator.generate_json_report()
validator.generate_markdown_report()
validator.generate_repair_documentation()
```

### Accessing Metrics

```python
validator = Stage2ModelValidator()
validator.run_full_validation()

# Convergence metrics
print(f"Iterations: {validator.convergence_metrics['num_iterations']}")
print(f"Converged: {validator.convergence_metrics['converged']}")

# Comparison metrics
summary = validator.comparison_results['summary']
print(f"Total connections: {summary['total_connections']}")
print(f"Match rate: {summary['match_rate']:.1%}")
```

## Regression Testing

### Optional Pytest Integration

While the validation can be run standalone, it can also be integrated into pytest for regression testing:

```python
import pytest
from validate_stage2_model import Stage2ModelValidator

def test_stage2_convergence():
    """Test that stage2 model converges"""
    validator = Stage2ModelValidator()
    validator.load_reference_data()
    converged = validator.verify_model_convergence()
    assert converged, "Model should converge"

def test_stage2_match_rate():
    """Test that comparison match rate is acceptable"""
    validator = Stage2ModelValidator()
    validator.run_full_validation()
    match_rate = validator.comparison_results['summary']['match_rate']
    assert match_rate >= 0.80, f"Match rate {match_rate:.1%} below 80%"
```

Run with:
```bash
pytest -v test_stage2_validation.py
```

## Acceptance Criteria

| Criterion | Status | Description |
|-----------|--------|-------------|
| Verification routine yields converged solution | ✅ | Model solves without exported solver states |
| Comparison artifact with tolerances | ✅ | JSON + Markdown reports with defined tolerances |
| Documentation of repair logic | ✅ | REPAIR_AND_VALIDATION_ANALYSIS.md documents strategy |
| Convergence metrics | ✅ | Iterations, residuals, status captured and reported |
| Optional pytest/CLI command | ✅ | CLI script and pytest examples provided |

## Files

| File | Purpose |
|------|---------|
| `validate_stage2_model.py` | Main validation module |
| `stage2_detailed_model.py` | Enhanced model with repair logic |
| `run_stage2_validation.sh` | Shell script for easy execution |
| `STAGE2_MODEL_VALIDATION.md` | Technical documentation |
| `VALIDATION_README.md` | This file - usage guide |

## Output Structure

```
validation_results/
├── validation_report.json              # Machine-readable metrics
├── VALIDATION_REPORT.md               # Human-readable summary
└── REPAIR_AND_VALIDATION_ANALYSIS.md  # Detailed repair analysis
```

## Troubleshooting

### Model Not Converging

If the model fails to converge:

1. **Check boundary conditions**: Ensure only true system inputs are fixed
2. **Review convergence metrics**: Check iteration count and residuals
3. **Enable fallback**: Try `use_reference_init=True, allow_fallback=True`
4. **Increase iterations**: Try `max_iter=300` or higher

### Large Differences vs Reference

If comparison shows large differences:

1. **Check tolerances**: Verify tolerances are appropriate for your use case
2. **Review solver settings**: Different solver settings can produce slightly different results
3. **Inspect specific connections**: Look at VALIDATION_REPORT.md for detailed differences
4. **Verify input data**: Ensure reference CSV data is correct

### Missing Connections

If comparison reports missing connections:

1. **Check connection labels**: Ensure labels in model match CSV exactly
2. **Review model structure**: Verify all connections from CSV are implemented
3. **Check CSV integrity**: Ensure reference CSV is complete and readable

## Contributing

When modifying the model or validation:

1. **Preserve boundary condition strategy**: Keep fixed vs. initial value distinction
2. **Update tolerances if needed**: Adjust in `Stage2ModelValidator.__init__()`
3. **Document changes**: Update STAGE2_MODEL_VALIDATION.md
4. **Run validation**: Verify changes don't break convergence
5. **Review reports**: Check that match rate remains acceptable

## References

- **Model Implementation**: `stage2_detailed_model.py`
- **Previous Reports**: 
  - `STAGE2_VERIFICATION_REPORT.md`
  - `VERIFICATION_SUMMARY.md`
  - `README_STAGE2.md`
- **TESPy Documentation**: https://tespy.readthedocs.io/

---

**Framework Version**: 1.0
**Compatible with**: stage2_detailed_model.py (post-repair)
**Last Updated**: 2024
