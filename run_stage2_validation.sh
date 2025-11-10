#!/bin/bash
# Stage2 模型验证脚本
#
# 用法：
#   ./run_stage2_validation.sh [output_dir]
#
# 如果未指定 output_dir，默认为 'validation_results'

set -e

OUTPUT_DIR="${1:-validation_results}"

echo "=================================================="
echo "Stage2 模型验证"
echo "=================================================="
echo "输出目录：$OUTPUT_DIR"
echo ""

# 运行验证
python3 validate_stage2_model.py --output-dir "$OUTPUT_DIR"

# 检查退出码
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✓ 验证完成"
    echo "=================================================="
    echo "报告已生成到：$OUTPUT_DIR/"
    echo "  - validation_report.json"
    echo "  - VALIDATION_REPORT.md"
    echo "  - REPAIR_AND_VALIDATION_ANALYSIS.md"
    echo ""
else
    echo ""
    echo "=================================================="
    echo "✗ 验证失败"
    echo "=================================================="
    exit 1
fi
