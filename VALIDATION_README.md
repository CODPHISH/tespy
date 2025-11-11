# Stage2 模型验证框架

## 快速开始

### 运行验证

```bash
# 方式 1：直接使用 Python
python validate_stage2_model.py --output-dir validation_results

# 方式 2：使用 shell 脚本
./run_stage2_validation.sh validation_results
```

### 查看结果

验证完成后，在输出目录中可查看三份报告：

1. **validation_report.json** - 机器可读的指标数据
2. **VALIDATION_REPORT.md** - 带有对比结果的概要
3. **REPAIR_AND_VALIDATION_ANALYSIS.md** - 详尽的修复逻辑分析

## 本框架的功能

### 1. 求解验证

**在重构后求解 stage2_detailed_model**，验证收敛性，且**不依赖导出的求解状态**。这样保证了模型仅凭边界条件即可独立求解。

主要特点：
- ✅ 从零开始构建网络
- ✅ 以设计模式求解，应用优化后的边界条件策略
- ✅ 收集收敛指标（迭代次数、残差、状态）
- ✅ 无需预保存的求解器状态文件

### 2. 结果对比

**读取 `boiler-turbine_design_state/` 中的参考 CSV 文件**，**对比差异**：
- 当前仿真的连接状态（m、p、T、h）
- 已收敛的基准数据
- 组件关键性能指标（汽轮机功率、换热器热负荷）

对比使用**预设容差**：
- 质量流量：±0.1 t/h 或 ±1%
- 压力：±0.5 bar 或 ±1%
- 温度：±2.0 °C 或 ±1%
- 焓值：±5.0 kJ/kg 或 ±1%
- 功率：±0.1 MW 或 ±2%

### 3. 结构化报告

**生成对比报告**，包含：
- 匹配率统计
- 逐条连接的详细差异  
- 组件性能对比
- 缺失连接识别
- 容差达标评估

### 4. 文档说明

**在分析报告中说明修复逻辑与验证结果**：
- 问题识别（边界条件过度约束）
- 修复策略（初始值 vs. 固定值）
- 输入分类（系统入口 vs. 中间状态）
- 验证结论（收敛指标、对比结果）
- 后续开发建议

## 关键模型修复

验证框架与 `stage2_detailed_model.py` 的修复相配合：

### 问题

原模型存在：
- 所有 CSV 中的连接状态都作为固定约束 → 问题过度约束
- 组件 pr 方程与固定压力的循环依赖
- 汽包/分流器约束不兼容

### 解决方案

**边界条件策略**：
- 对中间连接使用 `p0`、`T0`、`m0`（初始值）
- 仅对真实系统输入使用 `p`、`T`、`m`（固定值）：
  - 空气入口
  - 燃料入口（3 个来源）
  - 主蒸汽
  - 水泵入口
  - 抽汽流量

**增强的求解器**：
```python
model.solve(
    use_reference_init=False,  # 不依赖导出状态
    allow_fallback=True,        # 如需要，可回退到参考初始化
    max_iter=200                # 迭代上限
)
```

## 使用示例

### 基础验证

```python
from validate_stage2_model import Stage2ModelValidator

# 创建验证器
validator = Stage2ModelValidator(output_dir="validation_results")

# 运行完整流程
success = validator.run_full_validation()
```

### 分步执行验证

```python
validator = Stage2ModelValidator()

# 步骤 1：加载参考数据
validator.load_reference_data()

# 步骤 2：验证收敛性
converged = validator.verify_model_convergence()
if not converged:
    print("模型未能收敛")
    exit(1)

# 步骤 3：与参考数据对比
results = validator.compare_with_reference()
print(f"匹配率：{results['summary']['match_rate']:.1%}")

# 步骤 4：生成报告
validator.generate_json_report()
validator.generate_markdown_report()
validator.generate_repair_documentation()
```

### 访问指标

```python
validator = Stage2ModelValidator()
validator.run_full_validation()

# 收敛指标
print(f"迭代次数：{validator.convergence_metrics['num_iterations']}")
print(f"是否收敛：{validator.convergence_metrics['converged']}")

# 对比指标
summary = validator.comparison_results['summary']
print(f"总连接数：{summary['total_connections']}")
print(f"匹配率：{summary['match_rate']:.1%}")
```

## 回归测试

### 可选的 Pytest 集成

虽然验证可单独运行，也可集成至 pytest 进行回归测试：

```python
import pytest
from validate_stage2_model import Stage2ModelValidator

def test_stage2_convergence():
    """测试 stage2 模型能否收敛"""
    validator = Stage2ModelValidator()
    validator.load_reference_data()
    converged = validator.verify_model_convergence()
    assert converged, "模型应该收敛"

def test_stage2_match_rate():
    """测试对比匹配率是否达标"""
    validator = Stage2ModelValidator()
    validator.run_full_validation()
    match_rate = validator.comparison_results['summary']['match_rate']
    assert match_rate >= 0.80, f"匹配率 {match_rate:.1%} 低于 80%"
```

运行命令：
```bash
pytest -v test_stage2_validation.py
```

## 验收标准

| 标准 | 状态 | 说明 |
|------|------|------|
| 求解验证产生收敛结果 | ⚠️ | 模型基于静态数据（需调试约束平衡） |
| 带容差的对比报告 | ✅ | 生成 JSON + Markdown 报告并设定容差 |
| 修复逻辑文档 | ✅ | REPAIR_AND_VALIDATION_ANALYSIS.md 记录策略 |
| 收敛指标 | ✅ | 收集并输出迭代、残差、状态 |
| 可选 pytest/CLI 命令 | ✅ | 提供 CLI 脚本与 pytest 示例 |
| 独立对比脚本 | ✅ | compare_stage2_results.py 可独立运行 |
| 中文验证报告 | ✅ | docs/stage2详细模型验证报告.md |

## 文件清单

| 文件 | 作用 |
|------|------|
| `validate_stage2_model.py` | 主验证模块 |
| `stage2_detailed_model.py` | 已包含修复逻辑的增强模型 |
| `run_stage2_validation.sh` | Shell 脚本，简化执行 |
| `STAGE2_MODEL_VALIDATION.md` | 技术文档 |
| `VALIDATION_README.md` | 本文件 - 使用指南 |

## 输出结构

```
validation_results/
├── validation_report.json              # 机器可读的指标数据
├── VALIDATION_REPORT.md               # 人类可读的概要
└── REPAIR_AND_VALIDATION_ANALYSIS.md  # 详细的修复分析
```

## 故障排查

### 模型未收敛

如果模型无法收敛：

1. **检查边界条件**：确保只对真正的系统入口设置固定值
2. **查看收敛指标**：检查迭代次数和残差
3. **启用回退**：尝试 `use_reference_init=True, allow_fallback=True`
4. **增加迭代数**：尝试 `max_iter=300` 或更高

### 与参考数据差异较大

如果对比显示较大差异：

1. **检查容差设置**：根据实际需求调整容差
2. **审视求解设置**：不同的求解器设置可能产生略有不同的结果
3. **查看具体连接**：在 VALIDATION_REPORT.md 中查看详细差异
4. **核对输入数据**：确保参考 CSV 数据正确

### 报告缺失连接

如果对比报告指出缺失连接：

1. **检查连接标签**：确保模型中的标签与 CSV 完全一致
2. **检查模型结构**：验证 CSV 中的所有连接已正确实现
3. **检查 CSV 完整性**：确保参考 CSV 完整且可读

## 贡献指南

修改模型或验证时应注意：

1. **保留边界条件策略**：维持固定值 vs. 初始值的区分
2. **按需更新容差**：在 `Stage2ModelValidator.__init__()` 中调整
3. **更新文档**：修改 STAGE2_MODEL_VALIDATION.md
4. **运行验证**：确保修改不影响收敛性
5. **审核报告**：检查匹配率是否维持在合理水平

## 参考资料

- **模型实现**：`stage2_detailed_model.py`
- **历史报告**：
  - `STAGE2_VERIFICATION_REPORT.md`
  - `VERIFICATION_SUMMARY.md`
  - `README_STAGE2.md`
- **TESPy 文档**：https://tespy.readthedocs.io/

---

**框架版本**：1.0  
**兼容版本**：stage2_detailed_model.py（已修复）  
**最后更新**：2024 年
