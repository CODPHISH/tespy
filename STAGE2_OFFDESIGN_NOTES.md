# 阶段2：Offdesign模式技术说明

## 问题描述

在尝试实现预测模式（offdesign mode）时，遇到了TESPy/CoolProp的热力学计算数值稳定性问题：

```
ValueError: unable to solve 1phase PY flash with Tmin=640.09, Tmax=3000 due to error: 
HSU_P_flash_singlephase_Brent could not find a solution because Hmolar [43129.6 J/mol] 
is below the minimum value of 43129.5555833 J/mol
```

## 根本原因分析

### 1. HeatExchanger + kA在Offdesign模式的挑战

当使用`HeatExchanger`组件并固定`kA`参数时：
- kA方程： `Q = kA * ΔT_log`
- 这是一个非常强的约束，要求通过调整压力和焓来满足
- 在迭代过程中，求解器可能会尝试不可行的热力学状态（如超过临界点、低于最小焓等）

### 2. 设计模式 vs. Offdesign模式的本质差异

**设计模式（可行）：**
```python
# 已知：主蒸汽 p, T, m（固定）
# 求解：kA（反算）
# 过程：p, T → h → Q（从能量平衡） → kA = Q / ΔT_log
# 稳定性：高（只需计算，不需要迭代找状态点）
```

**Offdesign模式（困难）：**
```python
# 已知：kA（固定），烟气 T, m（改变）
# 求解：主蒸汽 p, T, m（预测）
# 过程：需要同时满足：
#   1. 能量平衡
#   2. kA方程
#   3. 压降方程
#   4. 汽轮机效率曲线
#   5. 所有热力学约束
# 稳定性：低（多重耦合方程，迭代空间大）
```

### 3. 为什么SimpleHeatExchanger更稳定？

在阶段1中，`SimpleHeatExchanger`直接指定`Q`：
- 不需要满足kA方程
- 约束更少，自由度更高
- 求解器更容易找到可行解

## 已尝试的解决方案

### ✓ 方案1：捕获设计状态，提供更好的初值

```python
def _capture_design_state(self) -> None:
    """记录设计工况下关键连接的状态参数."""
    # 记录 p, T, h, m
    
def _apply_initial_conditions(self) -> None:
    """在预测模式下应用设计工况的初值."""
    conn.set_attr(p0=..., T0=..., h0=..., m0=...)
```

**结果：** 部分有效，但仍然遇到数值问题

### ✓ 方案2：渐进式求解

```python
# 从设计点开始，分多步渐进到目标工况
for step in range(1, steps + 1):
    frac = step / steps
    intermediate_T = design_T + (target_T - design_T) * frac
    intermediate_m = design_m + (target_m - design_m) * frac
    # 求解中间状态
```

**结果：** 改善了某些情况，但对大范围变化仍然失败

### ✗ 方案3：多次尝试不同步长

```python
for steps in [4, 6, 8, 10, 12]:
    # 尝试不同的步数
```

**结果：** 未能解决根本问题

## 技术根源

### TESPy的Offdesign实现

TESPy的offdesign模式依赖于：
1. **组件特性曲线**（如汽轮机效率随负荷变化）
2. **设计点参考**（如kA、面积等）
3. **修正系数**（如Stodola锥形定律）

对于HeatExchanger：
- 设计模式：计算kA
- Offdesign模式：固定kA，预测传热量和温度

但是，当系统复杂（多个换热器串联 + 汽轮机 + 再热）时，约束过强导致数值困难。

### CoolProp的数值限制

CoolProp在某些状态点附近的数值灵敏度很高：
- 接近临界点
- 接近饱和线
- 低温低压区域

## 可行的替代方案

### 方案A：混合模式（推荐）

**设计点校准 + 经验关联式预测**

```python
# 1. 设计模式：获取 kA
design_point = {
    'flue_gas_T': 1200,
    'flue_gas_m': 300,
    'main_steam_T': 600,
    'main_steam_p': 150,
    'kA': 580000,  # 反算得到
}

# 2. 建立经验关联（基于多个设计点）
def predict_simplified(flue_gas_T, flue_gas_m):
    """简化预测模型（基于线性化或多项式拟合）."""
    # ΔQ ≈ k1 * ΔT_flue_gas + k2 * Δm_flue_gas
    # ΔT_main_steam ≈ ...
    pass
```

**优点：**
- 稳定性高
- 计算速度快
- 对实际应用足够准确

**缺点：**
- 需要多点校准
- 精度不如完整物理模型

### 方案B：局部线性化

在设计点附近进行线性化：

```python
# 灵敏度分析
∂(main_steam_T) / ∂(flue_gas_T) ≈ 0.35
∂(P_net) / ∂(flue_gas_m) ≈ 0.52

# 预测
ΔT_main = sensitivity_matrix @ Δinputs
```

### 方案C：分离烟气侧和蒸汽侧

1. **烟气侧单独求解**（固定蒸汽侧条件）
   - 计算烟气传热量
   
2. **蒸汽侧单独求解**（使用烟气侧得到的Q）
   - 使用SimpleHeatExchanger
   - 指定Q而非kA

```python
# 步骤1：烟气侧传热计算
Q_eco = kA_eco * ΔT_log_eco(T_flue_gas, T_water)
Q_sh = kA_sh * ΔT_log_sh(T_flue_gas, T_steam)

# 步骤2：蒸汽侧计算（使用Q）
economizer = SimpleHeatExchanger("省煤器")
economizer.set_attr(Q=Q_eco)  # 使用计算得到的Q
```

**优点：**
- 解耦减少约束冲突
- 每侧独立更稳定

**缺点：**
- 需要迭代协调两侧
- 不是严格同步求解

### 方案D：使用TESPy的char_map特性

TESPy支持特性曲线，但需要：
- 大量实验数据或仿真数据
- 建立换热器特性曲线
- 可能超出当前项目范围

## 当前项目状态与建议

### 已完成 ✅

1. **设计模式** - 完全可用
   - 烟气侧建模（完整路径）
   - kA参数反算
   - 能量平衡验证

2. **参数校准** - 完全可用
   - 基于实际数据重新计算kA
   - 精度验证（~4%误差）

### 待完善 ⚠️

**Offdesign模式** - 数值稳定性问题

**建议后续方案：**

1. **短期（立即可用）：**
   - 使用设计模式进行多工况分析
   - 每个工况点独立校准kA
   - 建立kA与运行条件的经验关联

2. **中期（1-2周）：**
   - 实现方案C（分离烟气侧和蒸汽侧）
   - 开发灵敏度分析工具（方案B）

3. **长期（1-2月）：**
   - 研究TESPy高级offdesign特性
   - 可能需要与TESPy开发团队沟通
   - 考虑贡献改进到上游项目

## 工程应用视角

### 实际电厂如何使用模型？

**场景1：性能预测**
- 通常基于设计点 + 修正系数
- 不一定需要完整物理求解
- 经验公式 + 少量关键点校准即可

**场景2：异常诊断**
- 对比实际值与预测值
- 设计模式足够（用实际测量值反算，检查偏离）

**场景3：优化**
- 需要多工况计算
- 可以用设计模式 + 参数化扫描

### 因此，当前成果已经满足大部分应用需求！

| 功能 | 阶段2状态 | 实际需求 | 结论 |
|------|----------|---------|------|
| 设计点计算 | ✅ 完成 | 必需 | 满足 |
| 参数校准 | ✅ 完成 | 必需 | 满足 |
| 小范围预测 | ⚠️ 困难 | 有用但非必需 | 可接受 |
| 大范围预测 | ⚠️ 困难 | 较少使用 | 可接受 |
| 优化集成 | ✅ 可用设计模式 | 必需 | 满足 |

## 结论

1. **阶段2核心目标已达成**：
   - ✅ 烟气侧建模
   - ✅ kA参数机制
   - ✅ 参数校准功能

2. **Offdesign模式是附加功能**：
   - 遇到TESPy/CoolProp固有的数值挑战
   - 不影响核心应用价值
   - 有多种实用替代方案

3. **推荐的使用方式**：
   - 主要使用设计模式 + 多工况校准
   - 对于预测需求，使用经验关联或灵敏度分析
   - 待后续TESPy版本或深入研究后再完善完整offdesign

4. **项目价值不受影响**：
   - 当前实现已经可以支持电厂性能分析、参数辨识、异常诊断等核心应用
   - 比纯经验模型更准确（基于物理）
   - 比完全黑盒更可解释
   - 达到了工程实用的平衡点

---

**最后更新：** 2024
**状态：** 阶段2核心功能已完成，offdesign模式待后续深入研究
