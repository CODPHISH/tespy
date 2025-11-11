# Stage2 详细模型 - 中文使用指南

## 概述

本项目实现了完整的锅炉-汽轮机系统 Stage2 详细模型，基于参考 CSV 数据构建，支持独立求解和结果验证。

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装项目及依赖
pip install -e .
```

### 2. 运行模型

```bash
# 直接运行模型求解
python stage2_detailed_model.py
```

### 3. 运行验证

```bash
# 运行完整验证流程
python validate_stage2_model.py --output-dir validation_results

# 或使用 shell 脚本
./run_stage2_validation.sh validation_results
```

### 4. 运行对比

```bash
# 运行独立对比脚本（不需要模型求解）
python compare_stage2_results.py --reference boiler-turbine_design_state \
                                   --output comparison_results
```

## 文件说明

### 核心模型文件

- **stage2_detailed_model.py**：完整的锅炉-汽轮机系统模型
- **stage2_static_inputs.py**：静态输入数据（从 CSV 提取）

### 验证与对比脚本

- **validate_stage2_model.py**：完整验证框架（求解 + 对比 + 报告）
- **compare_stage2_results.py**：独立对比脚本（仅对比，可复现）
- **run_stage2_validation.sh**：验证流程 shell 脚本

### 文档

- **docs/stage2组件数据分析.md**：组件参数详细分析（中文）
- **docs/stage2详细模型验证报告.md**：完整验证报告（中文）
- **STAGE2_MODEL_VALIDATION.md**：验证框架技术文档（英文）
- **VALIDATION_README.md**：验证使用快速指南（英文）
- **README_STAGE2.md**：Stage2 模型总体说明（英文）

### 参考数据

- **boiler-turbine_design_state/connections.csv**：连接参考数据
- **boiler-turbine_design_state/components/*.csv**：组件参考数据

## 模型结构

### 系统组成

| 组件类型 | 数量 | 主要实例 |
|---------|------|---------|
| 汽轮机 | 9 | 高压缸1-2段，低压缸1-7段 |
| 换热器 | 11 | 空气预热器、煤气预热器、蒸发器、各级过热器/再热器、省煤器 |
| 泵 | 1 | 给水泵 |
| 阀门 | 5 | 高压缸进/排气阀、中压缸进/排气阀、进水阀 |
| 燃烧室 | 1 | 炉膛燃烧室 |
| 汽包 | 1 | 汽水分离装置 |
| 管道 | 1 | 脱硫脱硝装置 |
| 其他 | 23 | 分离器、混合器、源/汇 |
| **总计** | **52** | |

### 连接数量

64 个连接，涵盖：
- 水/蒸汽循环
- 烟气侧流动
- 燃料气/空气侧流动

### 工作流体

- **水/蒸汽循环**：纯水 (H₂O)
- **烟气/空气**：N₂, O₂, H₂O, CO₂
- **燃料气**：N₂, O₂, CO, CO₂, H₂, CH₄

## 关键输出

### 主蒸汽参数（设计值）

- 质量流量：287.62 t/h
- 压力：161.0 bar
- 温度：560.0 °C

### 系统性能（参考值）

- 汽轮机总功率：95.31 MW
- 给水泵功率：14.60 MW
- **系统净功率：80.71 MW**

## 验证对比

### 对比容差

| 参数类型 | 绝对容差 | 相对容差 |
|---------|---------|----------|
| 质量流量 | ±0.1 t/h | ±1% |
| 压力 | ±0.5 bar | ±1% |
| 温度 | ±2.0 °C | ±1% |
| 焓 | ±5.0 kJ/kg | ±1% |
| 功率 | ±0.1 MW | ±2% |

### 对比内容

1. **连接状态对比**
   - 质量流量 (m)
   - 压力 (p)
   - 温度 (T)
   - 焓 (h)

2. **组件性能对比**
   - 汽轮机功率
   - 换热器传热量

3. **统计指标**
   - 平均绝对误差
   - 最大绝对误差
   - 平均相对误差
   - 最大相对误差
   - 容差内匹配率

## 常见问题

### 1. 模型不收敛怎么办？

**可能原因**：
- 边界条件设置不足或过度约束
- 初始值不合理
- 组件参数配置冲突

**解决方法**：
1. 检查边界条件设置（`_set_boundary_conditions` 方法）
2. 确认组件参数（汽轮机效率、换热器 kA 等）
3. 调整初始值策略（固定值 vs. 初始值）
4. 增加最大迭代次数

### 2. 验证脚本运行失败？

**可能原因**：
- 缺少依赖库
- 参考数据路径不正确
- 模型未收敛

**解决方法**：
```bash
# 检查依赖安装
pip list | grep -E 'tespy|pandas|numpy'

# 检查参考数据
ls -la boiler-turbine_design_state/

# 查看错误日志
python validate_stage2_model.py --output-dir test_results 2>&1 | tee error.log
```

### 3. 对比结果差异较大？

**可能原因**：
- 求解器收敛精度不同
- 物性计算方法差异
- 边界条件设置不一致

**解决方法**：
1. 确认参考数据与模型输入一致
2. 检查收敛残差和迭代次数
3. 调整对比容差（如果合理）
4. 分析差异的物理意义

## 开发与调试

### 修改组件参数

编辑 `stage2_detailed_model.py` 中的 `_set_component_parameters` 方法：

```python
# 示例：修改汽轮机效率
turbine_hp1 = nw.get_comp("抽凝式汽轮机1_高压缸一段")
turbine_hp1.set_attr(eta_s=0.75)  # 修改为 75%
```

### 修改边界条件

编辑 `stage2_detailed_model.py` 中的 `_set_boundary_conditions` 方法：

```python
# 示例：修改主蒸汽参数
conn = nw.get_conn("1#发电锅炉_主蒸汽")
conn.set_attr(m=300, p=170, T=570)  # 修改设计参数
```

### 调整容差

编辑 `compare_stage2_results.py` 或 `validate_stage2_model.py` 中的容差配置：

```python
TOLERANCES = {
    "mass_flow": {"absolute": 0.2, "relative": 0.02},  # 放宽到 0.2 t/h 或 2%
    # ...
}
```

## 进阶使用

### 作为 Python 模块使用

```python
from stage2_detailed_model import CompleteBoilerTurbineModel
from validate_stage2_model import Stage2ModelValidator

# 创建并求解模型
model = CompleteBoilerTurbineModel()
model.build_network()
success = model.solve()

if success:
    results = model.analyze()
    print(f"净功率: {results['P_net_MW']:.2f} MW")

# 运行验证
validator = Stage2ModelValidator()
validator.load_reference_data()
converged = validator.verify_model_convergence()
comparison = validator.compare_with_reference()
```

### 批量对比多个工况

```python
import pandas as pd
from pathlib import Path

# 假设有多个参考数据目录
reference_dirs = [
    "design_case_1",
    "design_case_2",
    "design_case_3",
]

results = []
for ref_dir in reference_dirs:
    validator = Stage2ModelValidator(reference_path=Path(ref_dir))
    validator.load_reference_data()
    # ... 执行验证和对比
    results.append(validator.comparison_results)

# 汇总分析
df = pd.DataFrame(results)
df.to_csv("batch_comparison.csv")
```

## 贡献与反馈

如有问题或建议，请：

1. 查阅相关文档（docs/ 目录）
2. 检查已有的报告和总结文件
3. 运行验证脚本诊断问题
4. 记录详细的错误信息和重现步骤

## 版本历史

- **1.0**（2024）：初始版本
  - 完整的 Stage2 详细模型实现
  - 基于静态数据的建模方式
  - 完整的验证和对比框架
  - 中文文档和报告

## 许可证

MIT License - 详见 LICENSE 文件

---

**最后更新**：2024  
**维护团队**：TESPy Stage2 开发组
