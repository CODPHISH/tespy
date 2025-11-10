#!/bin/bash
# Simple script to run stage2 model validation
#
# Usage:
#   ./run_stage2_validation.sh [output_dir]
#
# If output_dir is not specified, defaults to 'validation_results'

set -e

OUTPUT_DIR="${1:-validation_results}"

echo "=================================================="
echo "Stage2 Model Validation"
echo "=================================================="
echo "Output directory: $OUTPUT_DIR"
echo ""

# Run validation
python3 validate_stage2_model.py --output-dir "$OUTPUT_DIR"

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✓ Validation Complete"
    echo "=================================================="
    echo "Reports generated in: $OUTPUT_DIR/"
    echo "  - validation_report.json"
    echo "  - VALIDATION_REPORT.md"
    echo "  - REPAIR_AND_VALIDATION_ANALYSIS.md"
    echo ""
else
    echo ""
    echo "=================================================="
    echo "✗ Validation Failed"
    echo "=================================================="
    exit 1
fi
