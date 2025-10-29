# 锅炉-汽轮机发电厂仿真模型

基于 TESPy (Thermal Engineering Systems in Python) 构建的典型 Rankine 循环发电厂仿真模型。

## 模型概述

本仿真模型基于 TESPy 构建，提供了一个可靠的单回路 Rankine 循环基础框架。模型具备详细的热力学分析功能，可用于验证热效率、能量守恒、关键状态点等，可作为引入再热、回热等高级功能的起点。

### 目前包含的设备
1. **锅炉（SimpleHeatExchanger）**：模拟给水加热器，包含压降
2. **汽轮机（Turbine）**：高温蒸汽做功，支持效率设置
3. **凝汽器（Condenser）**：蒸汽冷凝，包含冷却水侧
4. **给水泵（Pump）**：提高给水压力
5. **循环水系统（Source/Sink）**：提供冷却能力

### 文件说明
- `waste_heat_boiler_turbine_model.py`：主仿真脚本，含详细分析
- `waste_heat_rankine_design.json`：设计点结果（运行后生成）
- `README_BOILER_TURBINE.md`：模型说明与扩展指南

## 运行环境

- Python 3.10 或更高版本
- TESPy >= 0.7.0
- NumPy, pandas, CoolProp（TESPy 依赖）

## 快速开始

### 1. 安装依赖

```bash
# 使用项目自带的 TESPy 源码（推荐）
cd /path/to/project
pip install -e .

# 或者从 PyPI 安装
pip install tespy
```

### 2. 运行仿真

```bash
python waste_heat_boiler_turbine_model.py
```

### 3. 查看结果

程序将输出以下内容：

- 网络初始化信息
- 各组件参数和状态点详细结果
- 性能汇总（功率、效率等）
- 设计点保存为 JSON 文件

## 设计参数

### 主蒸汽条件
- 压力：150 bar (≈ 15 MPa)
- 温度：600 °C
- 质量流量：10 kg/s

### 凝汽器条件
- 背压：0.1 bar (高真空)
- 端差（TTD_U）：约 16 °C

### 循环水条件
- 入口温度：20 °C
- 出口温度：30 °C
- 压力：1.2 bar

### 汽轮机
- 等熵效率：90%

### 给水泵
- 等熵效率：75%

## 典型输出结果

运行后将生成详细的热力学分析报告，包括：

### 性能指标
```
净发电功率:      12.987 MW
循环热效率:       38.55 %
总吸热:          33.690 MW
总放热:          20.702 MW
厂用电率:          1.69 %
排汽干度:         0.8655
```

### 热力学验证
- ✓ 能量守恒验证通过（误差 < 0.01%）
- ✓ 汽轮机膨胀过程温度和压力单调下降
- ✓ 排汽干度在合理范围 (0.85-0.95)
- ✓ 循环效率在合理范围: η = 38.55%
- ✓ 循环水温升合理: ΔT = 10.0 K

### 关键状态点
- 主蒸汽：150.00 bar / 600.00°C / 10.00 kg/s / h = 3583.13 kJ/kg
- 排汽：0.100 bar / 45.81°C / 干度 0.8655 / h = 2262.03 kJ/kg
- 凝结水：0.100 bar / 45.81°C / h = 191.81 kJ/kg
- 给水：166.67 bar / 47.71°C / h = 214.16 kJ/kg

### 对标分析
模型效率 38.55% 在简单 Rankine 循环典型值范围（35-42%）内，物理合理性通过验证。

## 扩展模型指导

基础模型已可靠运行。若要进一步增加工程要素，建议按照如下方式逐步扩展：

### 1. 再热循环（Reheat Cycle）
**理论基础**：从高压缸排汽送回锅炉再次加热，提高做功能力并增加排汽干度。

**实现要点**：
```python
# 增加再热器和低压缸
reheater = SimpleHeatExchanger("再热器")
lp_turbine = Turbine("低压缸")

# 连接: 高压缸 → 再热器 → 低压缸
c_hp_out = Connection(hp_turbine, "out1", reheater, "in1")
c_reheat = Connection(reheater, "out1", lp_turbine, "in1")
c_reheat.set_attr(T=540)  # 再热温度通常与主蒸汽相近
```

**预期提升**：循环效率提高约 2-4%，排汽干度增加。

### 2. 回热系统（Regenerative Feedwater Heating）
**理论基础**：从汽轮机中抽取部分蒸汽加热给水，减少锅炉热损失。

**实现难点**：
- 疏水回收系统复杂（建议简化或逐疏逐级）
- Splitter + Merge 组件容易产生线性依赖，需精心设置压力约束

**建议**：
- 从 1 级回热（除氧器）开始
- 除氧器抽汽 6-10% 主蒸汽流量
- 除氧器运行在 0.5-1.0 MPa
- 避免在同一压力回路中重复设置压力约束

**预期提升**：循环效率提高 3-5%，典型再热+回热机组可达 40-43%。

### 3. 多缸汽轮机
**实现**：
```python
hp_turbine = Turbine("高压缸", eta_s=0.88)
ip_turbine = Turbine("中压缸", eta_s=0.90)
lp_turbine = Turbine("低压缸", eta_s=0.86)  # 湿蒸汽区效率较低
```

### 4. 超临界/超超临界参数
**参数调整**：
```python
c1.set_attr(p=250, T=600, m=100)  # 超超临界参数
```

**注意**：CoolProp 在超临界区物性计算可能不稳定，需谨慎调试。

## 收敛性指导

实际工程模型扩展时，常见收敛问题及解决方案：

### 问题 1：线性依赖错误
```
TESPyNetworkError: You specified more than one variable of the linear dependent variables
```

**原因**：同一压力路径上指定了过多压力约束。  
**解决**：
- 只在每个独立压力回路中指定 1 个压力
- 除氧器等混合器出口压力由组件自动计算
- 使用泵的出口压力代替除氧器出口压力

### 问题 2：雅可比矩阵奇异
```
Found singularity in Jacobian matrix
```

**原因**：换热器端差约束与其他约束冲突。  
**解决**：
- 移除 `ttd_u` 参数，让其自由计算
- 检查抽汽流量是否足够（至少 5% 主流）

### 问题 3：流体属性超出范围
```
ValueError: Input out of range
```

**原因**：温度/压力/焓超出 CoolProp 范围。  
**解决**：
- 检查初值设置（T0, p0, h0）
- 降低主蒸汽参数进行测试
- 确保凝汽器真空合理（0.05-0.10 bar）

## 总结

当前提供的 `waste_heat_boiler_turbine_model.py` 是一个**物理合理、可靠收敛**的基础 Rankine 循环模型，适合作为：
1. 学习 TESPy 建模方法的入门案例
2. 验证热力学计算正确性的参考
3. 扩展更复杂电厂模型的起点

对于复杂模型（多级回热+再热），建议：
- 分步构建，逐步添加组件
- 每增加一级抽汽，单独测试收敛性
- 参考 TESPy 官方教程中的 `regenerative_heat_exchanger` 示例

## 参数化研究示例

在 `main()` 函数中可以添加参数化分析：

```python
def parametric_analysis(nw):
    """研究主蒸汽温度对效率的影响."""
    import numpy as np
    
    nw.set_attr(iterinfo=False)  # 关闭迭代信息
    temps = np.linspace(500, 650, 6)
    efficiencies = []
    
    c1 = nw.get_conn('主蒸汽')
    for T in temps:
        c1.set_attr(T=T)
        nw.solve('design')
        
        turbine = nw.get_comp('汽轮机')
        pump = nw.get_comp('给水泵')
        boiler = nw.get_comp('锅炉')
        
        P_net = abs(turbine.P.val) - abs(pump.P.val)
        eta = P_net / boiler.Q.val * 100
        efficiencies.append(eta)
    
    # 可以绘图或输出
    for T, eta in zip(temps, efficiencies):
        print(f"T = {T}°C, η = {eta:.2f}%")
```

## 注意事项

1. **流体属性**：所有工质必须设置 `fluid={'water': 1}`
2. **循环闭合器（CycleCloser）**：用于帮助流体属性在循环中传播
3. **压力单位**：程序中统一使用 bar (1 bar = 0.1 MPa)
4. **收敛性**：如果模型不收敛，可以：
   - 调整初值（使用 `T0=`, `p0=` 参数）
   - 简化约束条件
   - 先求解简化模型，再逐步增加复杂度

## 技术支持

- TESPy 官方文档：https://tespy.readthedocs.io/
- 官方示例集：https://github.com/oemof/tespy/tree/dev/tutorial
- 问题反馈：https://github.com/oemof/tespy/issues

## 许可证

本示例代码基于 TESPy 项目（MIT License）构建，遵循相同的开源许可证。

##  作者

根据 TESPy 官方 Rankine 循环示例改编，用于展示通用的锅炉-汽轮机发电厂建模流程。

---

**提示**：实际工程应用中需要考虑更多因素，如设备特性曲线、部分负荷性能、控制策略等。本模型主要用于教学和初步设计参考。
