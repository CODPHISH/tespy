# 锅炉-汽轮机发电厂仿真模型

基于 TESPy (Thermal Engineering Systems in Python) 构建的典型 Rankine 循环发电厂仿真模型。

## 模型概述

本仿真模型展示了一个经典的蒸汽动力循环系统，包含以下主要设备：

1. **锅炉（蒸汽发生器）**：将给水加热至高温高压蒸汽
2. **汽轮机**：高温高压蒸汽膨胀做功，驱动发电机
3. **凝汽器**：将排汽冷凝为液态水，建立真空
4. **给水泵**：将凝结水升压并送回锅炉
5. **循环水系统**：冷却凝汽器的冷却介质

## 文件说明

- `waste_heat_boiler_turbine_model.py` - 主仿真脚本
- `waste_heat_rankine_design.json` - 设计工况计算结果（运行后生成）
- `README_BOILER_TURBINE.md` - 本说明文档

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

```
汽轮机出力:    13.21 MW
给水泵耗功:   0.2236 MW
锅炉吸热:      33.69 MW
净发电功率:    12.99 MW
热效率:        38.55 %
```

## 扩展模型

此基础模型可以进一步扩展为：

1. **再热循环**：在高压缸和中压缸之间增加再热器
2. **回热系统**：从汽轮机抽取部分蒸汽加热给水
3. **除氧器**：去除给水中的溶解氧
4. **多级汽轮机**：高压缸 / 中压缸 / 低压缸
5. **超超临界参数**：更高的主蒸汽参数（250+ bar, 600+ °C）

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
