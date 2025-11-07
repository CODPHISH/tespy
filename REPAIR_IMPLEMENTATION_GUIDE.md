# Stage2 Detailed Model - Repair Implementation Guide

## Quick Summary

The cyclic dependency in `stage2_detailed_model.py` was caused by **misunderstanding the role of reference CSV data**.

### The Problem
```
CSV files = SIMULATION RESULTS (not inputs)
├─ connections.csv: Reference state points
└─ components/*.csv: Computed component properties (pr, pr1, pr2, kA)

WRONG: Set all CSV values as fixed constraints
       → Over-determined system
       → Cyclic dependency error

RIGHT: Use CSV only for validation
       Set only TRUE inputs (boundary conditions, design parameters)
```

## Implementation Steps

### Step 1: Identify Correct Inputs

From `connections.csv` and `components/*.csv`, extract:

**Boundary Conditions** (set these):
- Pump inlet (cycle return): p=1.0 bar, T≈100°C, fluid=water
- Air inlet: m, p, T from connections.csv, fluid={N2:0.76, O2:0.24}
- Fuel inlets (3 types): m, p, T, specific fluid compositions

**Design Parameters** (set these):
- Turbine eta_s values (from Turbine.csv)
- Pump eta_s (from Pump.csv)
- Combustor lamb, eta (from DiabaticCombustionChamber.csv)

**Computed Results** (DO NOT set):
- All pr values
- All pr1, pr2 values
- Heat exchanger kA values
- Intermediate connection pressures

### Step 2: Modify _set_boundary_conditions()

Replace the current CSV-based constraint approach with:

```python
def _set_boundary_conditions(self, nw: Network) -> None:
    # === Only set source boundary points ===
    
    # 1. Pump inlet (cycle closure point)
    try:
        conn = nw.get_conn("1#发电锅炉_水泵入口")
        # Use connections.csv reference values, but as initial conditions
        conn.set_attr(
            p=1.0,          # Condensate pressure
            T=99.0,         # Condensate temperature
            fluid={'water': 1}
        )
    except KeyError:
        pass
    
    # 2. Air inlet (combustion)
    try:
        conn = nw.get_conn("1#发电锅炉_空气入口")
        # Extract from connections.csv row for this inlet
        conn.set_attr(
            m=data_from_csv['m'],  # Mass flow
            p=data_from_csv['p'],  # Pressure
            T=data_from_csv['T'],  # Temperature
            fluid={'N2': 0.76, 'O2': 0.24}
        )
    except KeyError:
        pass
    
    # 3-5. Fuel inlet (similar for all three fuel sources)
    for inlet_label, fluid_comp in [
        ("boiler1_高炉煤气入口", {...}),
        ("1#发电锅炉_转炉煤气入口", {...}),
        ("1#发电锅炉_焦炉煤气入口", {...})
    ]:
        try:
            conn = nw.get_conn(inlet_label)
            data = get_from_connections_csv(inlet_label)
            conn.set_attr(
                m=data['m'],
                p=data['p'],
                T=data['T'],
                fluid=fluid_comp
            )
        except KeyError:
            pass
    
    # === DO NOT SET ===
    # - Intermediate connection pressures
    # - Pressure ratios (pr, pr1, pr2)
    # - Heat exchanger kA values
    # - Multiple component constraints in series
```

### Step 3: Modify _set_component_parameters()

Replace with design-parameter-only approach:

```python
def _set_component_parameters(self, nw: Network) -> None:
    
    # === Turbines: Only set efficiency ===
    turbine_efficiencies = {
        "抽凝式汽轮机1_高压缸一段": 0.7475393654293013,
        "抽凝式汽轮机1_高压缸二段": 0.7475393654295656,
        # ... all 9 turbines from Turbine.csv eta_s column
    }
    
    for name, eta_s in turbine_efficiencies.items():
        try:
            turb = nw.get_comp(name)
            turb.set_attr(eta_s=eta_s)  # ✓ Design parameter
            # DO NOT: turb.set_attr(pr=...)  # ✗ This is computed
        except KeyError:
            pass
    
    # === Pump: Only set efficiency ===
    try:
        pump = nw.get_comp("1#发电锅炉_给水泵")
        pump.set_attr(eta_s=0.85)  # ✓ Design parameter
        # DO NOT: pump.set_attr(pr=...)  # ✗ Computed from head requirements
    except KeyError:
        pass
    
    # === Combustor: Set process parameters ===
    try:
        combustor = nw.get_comp("1#发电锅炉_炉膛燃烧室")
        combustor.set_attr(
            lamb=1.2,   # ✓ Air ratio (design choice)
            eta=0.98    # ✓ Combustion efficiency (design choice)
        )
        # DO NOT: combustor.set_attr(pr=...)  # ✗ Computed
    except KeyError:
        pass
    
    # === Heat Exchangers: Leave unconstrained ===
    # TESPy will compute:
    # - pr (from inlet/outlet pressure drop)
    # - kA (from energy balance)
    # - Q (from fluid properties)
    # Just define they exist, don't over-specify
    
    # === Valves: Leave unconstrained ===
    # TESPy will compute pr from flow requirements
    
    print("✓ Component parameters set (design parameters only)")
```

### Step 4: Validation Against Reference

After model converges, check:

```python
# Extract computed results
turbine_hp1 = nw.get_comp("抽凝式汽轮机1_高压缸一段")

# Compare with reference (from components/Turbine.csv)
print(f"Computed P: {turbine_hp1.P.val / 1e6:.3f} MW")
print(f"Reference P: -16.483122 MW")
print(f"Computed pr: {turbine_hp1.pr.val:.4f}")
print(f"Reference pr: 0.4179")

# Should match closely (within numerical precision)
```

## Key Differences from Previous Approach

| Aspect | Previous (Wrong) | Correct |
|--------|-----------------|---------|
| CSV data role | Fixed constraints | Reference for validation |
| pr setting | Set on all components | Never set, computed by solver |
| pr1, pr2 setting | Set as fixed | Let solver compute |
| kA setting | Set from CSV | Let solver compute from energy |
| Boundary points | All connections | Only source inlets |
| Component params | pr, pr1, pr2, kA, Q | eta_s, lamb, eta only |
| Result | Cyclic dependency | Proper convergence |

## Expected Outcome

✅ Model successfully converges
✅ Outlet state points match connections.csv reference
✅ Component properties (pr, kA, Q) match components/*.csv
✅ System produces physically meaningful results

## Testing

To test the corrected model:

```bash
python stage2_corrected_model.py
```

Expected output:
```
================================================================================
纠正模型 - 基于参考数据反推的正确输入
================================================================================

[1] 定义组件...
   已定义 60 个组件

[2] 定义连接...
   已定义 64 个连接

[3] 设置边界条件...
   ✓ 边界条件设置完成

[4] 设置组件参数...
   ✓ 组件参数设置完成（设计参数）

================================================================================
开始求解...

✓ 求解成功

================================================================================
系统性能分析
================================================================================
...
```

## File Updates Required

1. **stage2_detailed_model.py** - Main file to update:
   - Replace `_set_component_parameters()` method
   - Replace `_set_boundary_conditions()` method
   - Keep network topology (connections.csv defines this)

2. **Alternative**: Use corrected file
   - `stage2_corrected_model.py` - Already implements fix
   - Can be used as template

## Reference Documentation

- `DIAGNOSTIC_AND_REPAIR_REPORT.md` - Full technical analysis
- `stage2_analysis_model.py` - Simplified implementation example
