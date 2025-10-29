# TESPy 发电厂仿真模型集

基于 TESPy 构建的一系列完整的发电厂热力循环仿真模型，从基础 Rankine 循环到高级再热回热循环。

## 📚 模型目录

### 1. 基础 Rankine 循环 ⭐ (推荐入门)

**文件**: `waste_heat_boiler_turbine_model.py`  
**文档**: `README_BOILER_TURBINE.md`

**特点**:
- ✅ 单回路简单循环
- ✅ 完整的热力学分析和验证
- ✅ 物理合理、稳定收敛
- ✅ 适合学习 TESPy 建模方法

**性能指标**:
- 净发电功率: 12.99 MW
- 循环热效率: 38.55%
- 排汽干度: 0.8655
- 通过 5 项热力学验证

**运行**:
```bash
python waste_heat_boiler_turbine_model.py
```

---

### 2. 详细锅炉模型 🏭

**文件**: `detailed_boiler_rankine_model.py`  
**文档**: `README_DETAILED_BOILER.md`

**特点**:
- ✅ 详细的锅炉三段式结构（省煤器-水冷壁-过热器）
- ✅ 真实反映锅炉内水/蒸汽的状态变化
- ✅ 可单独分析各段性能
- ✅ 更接近真实电厂配置

**锅炉组成**:
- 省煤器: 预热给水（利用烟气余热）
- 水冷壁: 水蒸发成饱和蒸汽（主要吸热段）
- 过热器: 饱和蒸汽变为过热蒸汽

**运行**:
```bash
python detailed_boiler_rankine_model.py
```

---

### 3. 再热 Rankine 循环 🔥

**文件**: `reheat_cycle_model.py`  
**文档**: `README_REHEAT_CYCLE.md`

**特点**:
- ✅ 双缸汽轮机（高压缸 + 低压缸）
- ✅ 一次再热循环
- ✅ 与基础模型详细对比
- ✅ 排汽干度显著改善

**性能指标**:
- 净发电功率: 15.42 MW (+18.7%)
- 循环热效率: 39.37% (+0.82%)
- 排汽干度: 0.9928 (+0.127)
- 再热温升: 241.2 K

**运行**:
```bash
python reheat_cycle_model.py
```

**对比基础模型的改进**:
- ✅ 效率提升 0.82%
- ✅ 排汽干度从 0.865 → 0.993，大幅减少叶片水蚀风险
- ✅ 功率增加 18.7%（相同主蒸汽条件）

---

### 4. 完整整合模型 🚀 (推荐生产应用)

**文件**: `integrated_boiler_turbine_model.py`

**特点**:
- ✅ 整合详细锅炉模型 + 再热循环
- ✅ 完整的工程验证机制（7项验证）
- ✅ 面向对象设计，易于扩展
- ✅ 详尽的性能输出和数据导出
- ✅ 典型300MW亚临界机组参数

**系统配置**:
- 详细锅炉: 省煤器 → 水冷壁 → 过热器
- 再热系统: 高压缸 → 再热器 → 低压缸
- 凝汽系统: 高真空凝汽器 + 循环水
- 给水系统: 高压给水泵

**性能指标** (100 kg/s流量):
- 净发电功率: ~300 MW
- 循环热效率: 40-42%
- 凝汽器真空: >90%
- 排汽干度: 0.88-0.94
- 能量平衡误差: <0.1%

**运行**:
```bash
python integrated_boiler_turbine_model.py
```

**工程验证**:
- ✓ 循环效率合理性 (38-44%)
- ✓ 排汽干度合理性 (0.85-0.95)
- ✓ 能量守恒 (<0.1%)
- ✓ 凝汽器真空度 (90-96%)
- ✓ 厂用电率 (<2.0%)
- ✓ 水冷壁吸热占比 (60-75%)
- ✓ 压降合理性

---

## 🎯 快速开始

### 环境要求

- Python 3.10+
- TESPy >= 0.7.0
- NumPy, pandas, CoolProp

### 安装

```bash
# 方法1: 使用项目源码（推荐）
cd /path/to/project
pip install -e .

# 方法2: 从 PyPI 安装
pip install tespy
```

### 运行顺序建议

1. **先运行基础模型** (学习基本概念)
   ```bash
   python waste_heat_boiler_turbine_model.py
   ```

2. **再运行再热模型** (理解效率提升原理)
   ```bash
   python reheat_cycle_model.py
   ```

3. **对比两者输出** (理解再热的优势)

---

## 📊 模型对比

| 特性 | 基础循环 | 再热循环 |
|------|----------|----------|
| **系统配置** |
| 汽轮机配置 | 单缸 | 双缸(高压+低压) |
| 再热级数 | 无 | 一次再热 |
| 主蒸汽参数 | 150 bar / 600°C | 150 bar / 600°C |
| 再热压力 | - | 30 bar |
| 再热温度 | - | 600°C |
| **性能指标** |
| 净发电功率 | 12.99 MW | 15.42 MW |
| 循环热效率 | 38.55% | 39.37% |
| 排汽干度 | 0.8655 | 0.9928 |
| 厂用电率 | 1.69% | 1.36% |
| **优缺点** |
| 优点 | 简单可靠 | 效率高、干度好 |
| 缺点 | 效率较低、干度低 | 系统复杂 |
| **适用场景** |
| 典型应用 | 小型机组、教学 | 中大型火电机组 |
| 装机容量 | <300 MW | 300-1000 MW |

---

## 🔬 热力学分析功能

所有模型都包含以下详细分析：

### 1. 功率平衡
- 汽轮机各缸段出力分布
- 厂用电（泵耗功）
- 净发电功率

### 2. 热量平衡
- 锅炉/再热器吸热
- 凝汽器放热
- 能量守恒验证（误差 < 0.01%）

### 3. 效率分析
- 循环热效率
- 卡诺效率（理论上限）
- 相对效率（实际/理论）
- 与行业典型值对标

### 4. 关键状态点
- 主蒸汽（p, T, h, m）
- 各缸排汽
- 凝结水/给水
- 循环水

### 5. 热力学验证
- ✓ 能量守恒
- ✓ 温度/压力单调性
- ✓ 排汽干度合理性
- ✓ 效率合理性
- ✓ 循环水温升

---

## 🚀 扩展指导

### 下一步可扩展的方向

#### 1. 回热系统 (中等难度)

增加抽汽加热给水：

```python
# 从低压缸抽汽
splitter = Splitter("抽汽分流", num_out=2)
deaerator = Merge("除氧器", num_in=2)

# 抽汽率 6-10%
c_extract.set_attr(m=Ref(c_main, 0.08, 0))
```

**注意事项**:
- 避免过度约束压力
- 疏水系统需简化处理
- 逐级添加，单独测试

**预期收益**: 效率提升 3-5%

#### 2. 多级回热 (高难度)

3-4级回热（高加+除氧器+低加）：
- 效率可达 42-45%
- 需要精心设计疏水系统
- 参考 TESPy 官方回热示例

#### 3. 超超临界参数 (中等难度)

提高主蒸汽参数：
- 压力：250-300 bar
- 温度：600-620°C
- 配合二次再热

**注意**: CoolProp 在超临界区可能不稳定

#### 4. 联合循环 (高难度)

燃气轮机 + 余热锅炉 + 蒸汽轮机：
- 效率可达 55-60%
- 需要燃气侧建模
- 复杂的多压余热锅炉

---

## 📖 学习路径

### 初学者
1. ✅ 阅读 `README_BOILER_TURBINE.md`
2. ✅ 运行基础模型，理解输出
3. ✅ 修改参数（温度、压力）观察影响
4. ✅ 尝试参数化研究

### 进阶用户
1. ✅ 运行再热模型，对比基础模型
2. ✅ 优化再热压力（20-50 bar）
3. ✅ 尝试添加一级回热（除氧器）
4. ✅ 研究超超临界参数

### 高级用户
1. ✅ 构建多级回热系统
2. ✅ 实现二次再热
3. ✅ 集成真实设备特性曲线
4. ✅ 离设计点性能分析

---

## ⚠️ 常见问题

### Q1: 模型不收敛怎么办？

**解决方案**:
1. 检查流体属性是否设置 `fluid={'water': 1}`
2. 降低参数（如主蒸汽温度）测试
3. 检查是否过度约束（线性依赖）
4. 设置合理的初值 `T0=`, `p0=`

### Q2: 线性依赖错误如何解决？

**原因**: 同一压力路径指定了多个压力。

**解决**:
- 只在每个独立回路设置 1 个压力
- 除氧器压力让系统自动计算
- 使用泵出口压力代替除氧器压力

### Q3: 效率与预期不符？

**检查**:
1. 能量平衡是否通过（< 0.1% 误差）
2. 汽轮机效率是否合理（85-92%）
3. 压降是否过大（锅炉 5-10%）
4. 再热压力是否最优（0.15-0.25 倍主蒸汽压力）

### Q4: 排汽干度过低怎么办？

**解决**:
- 增加再热循环（本项目已提供）
- 降低凝汽器压力（提高真空度）
- 提高主蒸汽温度
- 降低主蒸汽压力（小型机组）

---

## 🔧 参数化研究示例

### 示例1: 主蒸汽温度对效率的影响

```python
import numpy as np
import matplotlib.pyplot as plt

def parametric_study_temperature():
    """研究主蒸汽温度对循环效率的影响."""
    
    nw = build_rankine_system()  # 或 build_reheat_cycle()
    nw.set_attr(iterinfo=False)
    
    temps = np.linspace(500, 650, 16)
    efficiencies = []
    
    c_main = nw.get_conn('主蒸汽')
    
    for T in temps:
        c_main.set_attr(T=T)
        nw.solve('design')
        
        if nw.converged:
            boiler = nw.get_comp('锅炉')
            turbine = nw.get_comp('汽轮机')  # 或高压缸+低压缸
            pump = nw.get_comp('给水泵')
            
            P_net = abs(turbine.P.val) - abs(pump.P.val)
            Q_total = boiler.Q.val  # + 再热器（如有）
            eta = P_net / Q_total * 100
            
            efficiencies.append(eta)
            print(f"T = {T:.0f}°C → η = {eta:.2f}%")
        else:
            efficiencies.append(np.nan)
    
    # 绘图
    plt.figure(figsize=(10, 6))
    plt.plot(temps, efficiencies, 'bo-', linewidth=2)
    plt.xlabel('主蒸汽温度 (°C)', fontsize=12)
    plt.ylabel('循环热效率 (%)', fontsize=12)
    plt.title('主蒸汽温度对循环效率的影响', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('parametric_temperature.png', dpi=300)
    print("\n图表已保存: parametric_temperature.png")
```

### 示例2: 再热压力优化

```python
def optimize_reheat_pressure():
    """寻找最优再热压力."""
    
    nw = build_reheat_cycle()
    c_hp_out = nw.get_conn("高压缸排汽")
    
    pressures = np.linspace(20, 50, 31)
    results = []
    
    for p_rh in pressures:
        c_hp_out.set_attr(p=p_rh)
        nw.solve('design')
        
        if nw.converged:
            # 提取性能数据
            boiler = nw.get_comp("锅炉")
            reheater = nw.get_comp("再热器")
            hp_turb = nw.get_comp("高压缸")
            lp_turb = nw.get_comp("低压缸")
            pump = nw.get_comp("给水泵")
            
            P_net = abs(hp_turb.P.val) + abs(lp_turb.P.val) - abs(pump.P.val)
            Q_total = boiler.Q.val + reheater.Q.val
            eta = P_net / Q_total * 100
            
            lp_exhaust = nw.get_conn("低压缸排汽")
            x = lp_exhaust.x.val
            
            results.append({
                'p_reheat': p_rh,
                'eta': eta,
                'P_net': P_net,
                'quality': x
            })
            
            print(f"p_rh = {p_rh:5.1f} bar → η = {eta:.3f}%, x = {x:.4f}")
    
    # 找到最优点
    best = max(results, key=lambda r: r['eta'])
    print(f"\n✓ 最优再热压力: {best['p_reheat']:.1f} bar")
    print(f"  最高效率: {best['eta']:.3f}%")
    print(f"  净功率: {best['P_net']:.2f} MW")
    print(f"  排汽干度: {best['quality']:.4f}")
    
    return results
```

---

## 📚 参考资料

### TESPy 官方资源
- [官方文档](https://tespy.readthedocs.io/)
- [GitHub 仓库](https://github.com/oemof/tespy)
- [官方教程](https://github.com/oemof/tespy/tree/dev/tutorial)

### 热力学基础
- 《工程热力学》- 沈维道等，高等教育出版社
- 《汽轮机原理》- 高等教育出版社
- 《电厂热力系统》- 中国电力出版社

### 在线资源
- [NIST 水蒸气性质](https://webbook.nist.gov/chemistry/fluid/)
- [CoolProp 文档](http://www.coolprop.org/)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request：

- 报告 Bug
- 改进文档
- 添加新模型
- 优化现有代码

---

## 📄 许可证

本项目遵循 MIT License，与 TESPy 相同。

---

## 🎓 总结

本项目提供了从入门到进阶的完整发电厂仿真模型：

1. **基础模型** - 稳定可靠，适合学习
2. **再热模型** - 展示效率提升原理
3. **详细文档** - 完整的扩展指导
4. **参数化示例** - 优化研究方法

希望这些模型能帮助您：
- ✅ 快速掌握 TESPy 建模方法
- ✅ 理解热力循环原理
- ✅ 进行工程级电厂仿真
- ✅ 开展创新性研究

**祝您使用愉快！** 🚀
