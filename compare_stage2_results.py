#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage2 模型结果对比脚本

此脚本独立运行，用于对比 stage2 模型求解结果与参考 CSV 数据。
可用于验证模型精度和分析差异来源。

使用方法:
    python compare_stage2_results.py [--reference参考数据目录] [--output输出目录]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# 容差配置（根据 "stage2组件数据分析" 文档）
TOLERANCES = {
    "mass_flow": {"absolute": 0.1, "relative": 0.01},  # 0.1 t/h 或 1%
    "pressure": {"absolute": 0.5, "relative": 0.01},   # 0.5 bar 或 1%
    "temperature": {"absolute": 2.0, "relative": 0.01}, # 2°C 或 1%
    "enthalpy": {"absolute": 5.0, "relative": 0.01},   # 5 kJ/kg 或 1%
    "power": {"absolute": 0.1, "relative": 0.02},      # 0.1 MW 或 2%
}


class Stage2ResultComparator:
    """Stage2 模型结果对比器"""

    def __init__(self, reference_path: Path, results_path: Path | None = None):
        """
        初始化对比器
        
        参数:
            reference_path: 参考 CSV 数据目录路径
            results_path: 模型求解结果路径（可选）
        """
        self.reference_path = reference_path
        self.results_path = results_path
        self.reference_data: dict[str, pd.DataFrame] = {}
        self.model_results: dict[str, Any] = {}
        self.comparison: dict[str, Any] = {}

    def load_reference_data(self) -> None:
        """加载参考 CSV 数据"""
        print("\n加载参考数据...")
        print("=" * 80)
        
        # 读取连接数据
        conn_path = self.reference_path / "connections.csv"
        if conn_path.exists():
            self.reference_data["connections"] = pd.read_csv(conn_path, sep=';', index_col=0)
            print(f"✓ 已加载 {len(self.reference_data['connections'])} 条参考连接数据")
        else:
            print(f"⚠ 未找到连接数据文件: {conn_path}")
        
        # 读取组件数据
        comp_dir = self.reference_path / "components"
        if comp_dir.exists():
            for csv_file in comp_dir.glob("*.csv"):
                comp_type = csv_file.stem
                try:
                    df = pd.read_csv(csv_file, sep=';', index_col=0)
                    if not df.empty:
                        self.reference_data[comp_type] = df
                        print(f"✓ 已加载 {len(df)} 个 {comp_type} 组件参数")
                except Exception as e:
                    print(f"⚠ 读取 {csv_file} 失败: {e}")
        else:
            print(f"⚠ 未找到组件数据目录: {comp_dir}")

    def load_model_results(self, model_or_path: Any) -> None:
        """
        加载模型求解结果
        
        参数:
            model_or_path: CompleteBoilerTurbineModel 实例或结果文件路径
        """
        print("\n加载模型求解结果...")
        print("=" * 80)
        
        if isinstance(model_or_path, (str, Path)):
            # 从文件加载
            results_path = Path(model_or_path)
            if results_path.exists():
                with results_path.open('r', encoding='utf-8') as f:
                    self.model_results = json.load(f)
                print(f"✓ 已从文件加载结果: {results_path}")
            else:
                print(f"⚠ 未找到结果文件: {results_path}")
        else:
            # 从模型对象加载
            model = model_or_path
            if hasattr(model, 'nw') and model.nw and model.nw.converged:
                self.model_results = self._extract_from_model(model)
                print("✓ 已从模型对象提取结果")
            else:
                print("⚠ 模型未收敛或无效")

    def _extract_from_model(self, model: Any) -> dict[str, Any]:
        """从模型对象提取结果数据"""
        results = {
            "connections": {},
            "components": {},
            "convergence": {
                "converged": model.nw.converged,
                "iterations": getattr(model.nw, 'iter', None),
            }
        }
        
        # 提取连接状态
        for conn in model.nw.conns:
            label = conn.label
            results["connections"][label] = {
                "m": float(conn.m.val) if hasattr(conn.m, "val") else None,
                "p": float(conn.p.val) if hasattr(conn.p, "val") else None,
                "T": float(conn.T.val) if hasattr(conn.T, "val") else None,
                "h": float(conn.h.val) if hasattr(conn.h, "val") else None,
            }
        
        # 提取组件参数
        for comp in model.nw.comps:
            label = comp.label
            comp_type = type(comp).__name__
            if comp_type not in results["components"]:
                results["components"][comp_type] = {}
            
            comp_data = {}
            if hasattr(comp, "P") and hasattr(comp.P, "val"):
                comp_data["P"] = float(comp.P.val)
            if hasattr(comp, "Q") and hasattr(comp.Q, "val"):
                comp_data["Q"] = float(comp.Q.val)
            if hasattr(comp, "eta_s") and hasattr(comp.eta_s, "val"):
                comp_data["eta_s"] = float(comp.eta_s.val)
            if hasattr(comp, "pr") and hasattr(comp.pr, "val"):
                comp_data["pr"] = float(comp.pr.val)
            
            if comp_data:
                results["components"][comp_type][label] = comp_data
        
        return results

    def compare_connections(self) -> dict[str, Any]:
        """对比连接状态"""
        print("\n对比连接状态...")
        print("=" * 80)
        
        if "connections" not in self.reference_data:
            print("⚠ 无参考连接数据")
            return {}
        
        ref_df = self.reference_data["connections"]
        results = {
            "total": len(ref_df),
            "compared": 0,
            "matches": [],
            "differences": [],
            "missing": [],
            "details": []
        }
        
        model_conns = self.model_results.get("connections", {})
        
        for label in ref_df.index:
            if label not in model_conns:
                results["missing"].append(label)
                continue
            
            ref_row = ref_df.loc[label]
            model_row = model_conns[label]
            
            conn_result = {"label": label}
            has_difference = False
            
            # 对比质量流量
            if pd.notna(ref_row.get("m")) and model_row.get("m") is not None:
                comp = self._compare_value(
                    model_row["m"], ref_row["m"], "mass_flow"
                )
                conn_result["m"] = comp
                if not comp.get("within_tolerance", True):
                    has_difference = True
            
            # 对比压力
            if pd.notna(ref_row.get("p")) and model_row.get("p") is not None:
                comp = self._compare_value(
                    model_row["p"], ref_row["p"], "pressure"
                )
                conn_result["p"] = comp
                if not comp.get("within_tolerance", True):
                    has_difference = True
            
            # 对比温度
            if pd.notna(ref_row.get("T")) and model_row.get("T") is not None:
                comp = self._compare_value(
                    model_row["T"], ref_row["T"], "temperature"
                )
                conn_result["T"] = comp
                if not comp.get("within_tolerance", True):
                    has_difference = True
            
            # 对比焓
            if pd.notna(ref_row.get("h")) and model_row.get("h") is not None:
                comp = self._compare_value(
                    model_row["h"], ref_row["h"], "enthalpy"
                )
                conn_result["h"] = comp
                if not comp.get("within_tolerance", True):
                    has_difference = True
            
            results["compared"] += 1
            results["details"].append(conn_result)
            
            if has_difference:
                results["differences"].append(conn_result)
            else:
                results["matches"].append(label)
        
        print(f"✓ 对比完成: {results['compared']}/{results['total']} 个连接")
        print(f"  - 匹配: {len(results['matches'])} 个")
        print(f"  - 差异: {len(results['differences'])} 个")
        print(f"  - 缺失: {len(results['missing'])} 个")
        
        return results

    def compare_components(self) -> dict[str, Any]:
        """对比组件参数"""
        print("\n对比组件参数...")
        print("=" * 80)
        
        results = {
            "turbines": {"total": 0, "compared": 0, "details": []},
            "heat_exchangers": {"total": 0, "compared": 0, "details": []},
        }
        
        # 对比汽轮机功率
        if "Turbine" in self.reference_data:
            ref_df = self.reference_data["Turbine"]
            model_comps = self.model_results.get("components", {}).get("Turbine", {})
            
            results["turbines"]["total"] = len(ref_df)
            
            for name in ref_df.index:
                if name not in model_comps:
                    continue
                
                ref_P = ref_df.loc[name, "P"] if pd.notna(ref_df.loc[name, "P"]) else None
                model_P = model_comps[name].get("P")
                
                if ref_P is not None and model_P is not None:
                    comp = self._compare_value(
                        abs(model_P) / 1e6,  # W -> MW
                        abs(ref_P) / 1e6,
                        "power"
                    )
                    results["turbines"]["details"].append({
                        "name": name,
                        "power": comp
                    })
                    results["turbines"]["compared"] += 1
            
            print(f"✓ 汽轮机对比: {results['turbines']['compared']}/{results['turbines']['total']} 个")
        
        # 对比换热器传热量
        if "HeatExchanger" in self.reference_data:
            ref_df = self.reference_data["HeatExchanger"]
            model_comps = self.model_results.get("components", {}).get("HeatExchanger", {})
            
            results["heat_exchangers"]["total"] = len(ref_df)
            
            for name in ref_df.index:
                if name not in model_comps:
                    continue
                
                ref_Q = ref_df.loc[name, "Q"] if pd.notna(ref_df.loc[name, "Q"]) else None
                model_Q = model_comps[name].get("Q")
                
                if ref_Q is not None and model_Q is not None:
                    comp = self._compare_value(
                        abs(model_Q) / 1e6,  # W -> MW
                        abs(ref_Q) / 1e6,
                        "power"
                    )
                    results["heat_exchangers"]["details"].append({
                        "name": name,
                        "heat_transfer": comp
                    })
                    results["heat_exchangers"]["compared"] += 1
            
            print(f"✓ 换热器对比: {results['heat_exchangers']['compared']}/{results['heat_exchangers']['total']} 个")
        
        return results

    def _compare_value(self, current: float, reference: float, value_type: str) -> dict[str, Any]:
        """
        对比单个值
        
        参数:
            current: 当前值
            reference: 参考值
            value_type: 值类型（用于查找容差）
            
        返回:
            对比结果字典
        """
        tol = TOLERANCES.get(value_type, {"absolute": 0, "relative": 0})
        
        abs_diff = abs(current - reference)
        rel_diff = abs_diff / abs(reference) if reference != 0 else 0
        
        within_abs = abs_diff <= tol["absolute"]
        within_rel = rel_diff <= tol["relative"]
        within_tolerance = within_abs or within_rel
        
        return {
            "current": float(current),
            "reference": float(reference),
            "absolute_difference": float(abs_diff),
            "relative_difference": float(rel_diff),
            "within_tolerance": within_tolerance,
            "tolerance_absolute": tol["absolute"],
            "tolerance_relative": tol["relative"],
        }

    def generate_comparison_report(self, output_path: Path) -> None:
        """生成对比报告"""
        report = {
            "reference_path": str(self.reference_path),
            "timestamp": pd.Timestamp.now().isoformat(),
            "connections": self.comparison.get("connections", {}),
            "components": self.comparison.get("components", {}),
            "summary": {
                "connections_total": self.comparison.get("connections", {}).get("total", 0),
                "connections_compared": self.comparison.get("connections", {}).get("compared", 0),
                "connections_matched": len(self.comparison.get("connections", {}).get("matches", [])),
                "connections_different": len(self.comparison.get("connections", {}).get("differences", [])),
            }
        }
        
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 对比报告已保存: {output_path}")

    def run_full_comparison(self, output_dir: Path) -> bool:
        """运行完整对比流程"""
        try:
            self.load_reference_data()
            
            # 如果有模型结果，加载并对比
            if self.results_path and self.results_path.exists():
                self.load_model_results(self.results_path)
            
            # 执行对比
            self.comparison = {
                "connections": self.compare_connections(),
                "components": self.compare_components(),
            }
            
            # 生成报告
            output_path = output_dir / "comparison_report.json"
            self.generate_comparison_report(output_path)
            
            return True
        except Exception as e:
            print(f"\n✗ 对比失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description="Stage2 模型结果对比脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法（仅加载参考数据）
    python compare_stage2_results.py
    
    # 指定参考数据目录
    python compare_stage2_results.py --reference boiler-turbine_design_state
    
    # 指定输出目录
    python compare_stage2_results.py --output comparison_results
        """
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("boiler-turbine_design_state"),
        help="参考 CSV 数据目录路径（默认: boiler-turbine_design_state）"
    )
    parser.add_argument(
        "--results",
        type=Path,
        help="模型求解结果文件路径（可选）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("comparison_results"),
        help="输出目录（默认: comparison_results）"
    )
    
    args = parser.parse_args()
    
    # 创建输出目录
    args.output.mkdir(exist_ok=True, parents=True)
    
    # 创建对比器并运行
    comparator = Stage2ResultComparator(
        reference_path=args.reference,
        results_path=args.results
    )
    
    success = comparator.run_full_comparison(args.output)
    
    if success:
        print("\n" + "=" * 80)
        print("✓ 对比完成")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("✗ 对比失败")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
