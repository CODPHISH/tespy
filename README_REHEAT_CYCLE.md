# 再热Rankine循环仿真模型

基于基础 Rankine 循环扩展的再热循环模型，展示了如何通过增加再热器提升循环效率。

## 模型特点

### 相比基础模型的改进
1. **双缸汽轮机**：高压缸 + 低压缸
2. **一次再热**：高压缸排汽返回锅炉再热后进入低压缸
3. **效率提升**：约 0.8-2% 效率提升
4. **排汽干度改善**：从 0.865 提升至 0.993，显著减少叶片水蚀风险

### 文件说明
- `reheat_cycle_model.py`：再热循环仿真脚本
- `reheat_cycle_design.json`：设计点结果（运行后生成）
- `README_REHEAT_CYCLE.md`：本说明文档

## 设计参数

### 主蒸汽条件（与基础模型相同）
- 压力：150 bar (15 MPa)
- 温度：600 °C
- 质量流量：10 kg/s

### 再热参数
- 再热压力：30 bar (3 MPa)
- 再热温度：600 °C
- 再热器压降：3%

### 汽轮机
- 高压缸等熵效率：88%
- 低压缸等熵效率：86%（湿蒸汽区略低）

### 凝汽器
- 背压：0.1 bar

## 运行示例

```bash
python reheat_cycle_model.py
```

## 典型输出结果

### 性能对比

| 指标 | 简单循环 | 再热循环 | 改善 |
|------|----------|----------|------|
| 净发电功率 | 12.99 MW | 15.42 MW | +18.7% |
| 循环热效率 | 38.55% | 39.37% | +0.82% |
| 排汽干度 | 0.8655 | 0.9928 | +0.127 |
| 厂用电率 | 1.69% | 1.36% | -0.33% |

### 关键发现

1. **效率提升**：循环效率从 38.55% 提升至 39.37%
   - 理论预期：2-4%
   - 实际提升：0.82%（需优化再热压力以达到更好效果）

2. **排汽干度显著改善**：从 0.8655 提升至 0.9928
   - 大幅降低低压缸末级叶片水蚀风险
   - 这是再热循环最重要的优势之一

3. **功率分配**：
   - 高压缸：28.6%
   - 低压缸：71.4%（再热后功率大幅增加）

4. **再热器吸热**：占总吸热的 14.0%

## 参数优化建议

### 1. 再热压力优化

当前模型使用 30 bar 再热压力。可以通过参数化研究找到最优再热压力：

```python
def optimize_reheat_pressure():
    """研究再热压力对效率的影响."""
    import numpy as np
    
    nw = build_reheat_cycle()
    c2 = nw.get_conn("高压缸排汽")
    
    pressures = np.linspace(20, 50, 7)  # 20-50 bar
    efficiencies = []
    
    for p_rh in pressures:
        c2.set_attr(p=p_rh)
        nw.solve('design')
        
        if nw.converged:
            # 计算效率
            boiler = nw.get_comp("锅炉")
            reheater = nw.get_comp("再热器")
            hp_turb = nw.get_comp("高压缸")
            lp_turb = nw.get_comp("低压缸")
            pump = nw.get_comp("给水泵")
            
            P_net = abs(hp_turb.P.val) + abs(lp_turb.P.val) - abs(pump.P.val)
            Q_total = boiler.Q.val + reheater.Q.val
            eta = P_net / Q_total * 100
            
            efficiencies.append(eta)
            print(f"再热压力 {p_rh:.1f} bar → 效率 {eta:.2f}%")
        else:
            efficiencies.append(None)
    
    # 找到最优点
    best_idx = np.argmax([e for e in efficiencies if e is not None])
    print(f"\n最优再热压力: {pressures[best_idx]:.1f} bar")
    print(f"最高效率: {efficiencies[best_idx]:.2f}%")
```

### 2. 再热温度优化

理论上，再热温度应与主蒸汽温度相等或略低。可以研究：
- 再热温度 580-620°C 范围
- 与材料允许温度的平衡

### 3. 多级再热

对于超超临界机组，可考虑二次再热：
- 一次再热：50-80 bar → 600°C
- 二次再热：10-20 bar → 600°C
- 效率可提升至 43-46%

## 工程意义

### 再热循环的优势

1. **提高循环效率**：2-4%（优化后）
2. **改善排汽干度**：避免末级叶片水蚀
3. **增加单机容量**：适用于大型机组（300-1000MW）

### 再热循环的代价

1. **增加设备投资**：再热器、低压缸
2. **锅炉系统复杂**：需要再热器管系
3. **运行维护成本增加**：更多的设备

### 应用场景

- 大型燃煤火电机组（300MW以上）
- 核电站（PWR、BWR）
- 联合循环汽轮机（蒸汽部分）

## 进一步扩展

在此再热循环基础上，可继续添加：

### 1. 回热系统

从低压缸抽汽加热给水：

```python
# 增加除氧器抽汽
splitter = Splitter("抽汽分流", num_out=2)
deaerator = Merge("除氧器", num_in=2)

# 连接
c_lp_split = Connection(lp_turbine, "out1", splitter, "in1")
c_extract = Connection(splitter, "out1", deaerator, "in1")
c_exhaust = Connection(splitter, "out2", condenser, "in1")
```

预期效果：再热+回热可达 41-43% 效率。

### 2. 多级回热

3-4级回热（高加+除氧器+低加）：
- 效率可达 42-45%
- 典型600MW超临界机组配置

### 3. 超超临界参数

提高主蒸汽参数：
- 压力：250-300 bar
- 温度：600-620°C
- 配合二次再热，效率可达 45-48%

## 注意事项

1. **再热压力选择**：过高减少低压缸做功，过低减少再热效果
   - 经验值：0.15-0.25倍主蒸汽压力
   - 本例：30/150 = 0.20（合理）

2. **排汽干度**：再热后通常 > 0.95
   - 优点：无水蚀风险
   - 缺点：凝汽器负荷增大

3. **收敛性**：再热循环通常收敛良好
   - 比回热系统简单得多
   - 适合作为扩展的第一步

## 参考资料

- TESPy官方文档：https://tespy.readthedocs.io/
- 《汽轮机原理》- 高等教育出版社
- 《电厂热力系统》- 中国电力出版社

## 许可证

本示例遵循 MIT License，与 TESPy 项目相同。

---

**结论**：再热循环是火电机组提效的重要手段，特别适用于大型机组。本模型提供了可靠的仿真基础，可进一步优化参数或增加回热系统。
