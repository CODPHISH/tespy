#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage2 模型验证与校验模块

功能简介：
1. 验证重构后的 stage2_detailed_model 是否能够独立收敛
2. 读取参考 CSV 数据并对比当前仿真结果的差异
3. 根据设定容差生成 JSON 与 Markdown 格式的结构化报告
4. 输出收敛指标与验证结论

使用方式：
    python validate_stage2_model.py [--output-dir results]
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from stage2_detailed_model import CompleteBoilerTurbineModel


class Stage2ModelValidator:
    """Stage2 详细模型的验证器，包含对比与报告功能"""

    def __init__(self, reference_path: Path | None = None, output_dir: Path | None = None):
        """
        初始化验证器
        
        参数：
            reference_path: 参考 CSV 数据目录路径
            output_dir: 报告输出目录
        """
        self.reference_path = reference_path or PROJECT_ROOT / "boiler-turbine_design_state"
        self.output_dir = output_dir or PROJECT_ROOT / "validation_results"
        self.output_dir.mkdir(exist_ok=True)
        
        self.model: CompleteBoilerTurbineModel | None = None
        self.reference_data: dict[str, pd.DataFrame] = {}
        self.comparison_results: dict[str, Any] = {}
        self.convergence_metrics: dict[str, Any] = {}
        self.key_outputs: dict[str, Any] = {}
        self.error_statistics: dict[str, Any] = {}
        
        # 对比容差设定
        self.tolerances = {
            "mass_flow": {"absolute": 0.1, "relative": 0.01},  # 0.1 t/h 或 1%
            "pressure": {"absolute": 0.5, "relative": 0.01},   # 0.5 bar 或 1%
            "temperature": {"absolute": 2.0, "relative": 0.01}, # 2°C 或 1%
            "enthalpy": {"absolute": 5.0, "relative": 0.01},   # 5 kJ/kg 或 1%
            "power": {"absolute": 0.1, "relative": 0.02},      # 0.1 MW 或 2%
        }

    def load_reference_data(self) -> None:
        """读取参考 CSV 数据"""
        print("\n" + "=" * 80)
        print("加载参考数据")
        print("=" * 80)
        
        # 读取连接数据
        conn_path = self.reference_path / "connections.csv"
        if conn_path.exists():
            self.reference_data["connections"] = pd.read_csv(conn_path, sep=';', index_col=0)
            print(f"✓ 已加载 {len(self.reference_data['connections'])} 条参考连接数据")
        
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

    def verify_model_convergence(self) -> bool:
        """
        验证模型在重构后能够独立求解并成功收敛
        
        返回：
            模型收敛则返回 True，否则返回 False
        """
        print("\n" + "=" * 80)
        print("模型验证 - 收敛性测试")
        print("=" * 80)
        
        try:
            # 创建模型实例
            self.model = CompleteBoilerTurbineModel()
            
            # 构建网络
            print("\n[1/3] 构建网络...")
            self.model.build_network()
            print("✓ 网络构建成功")
            
            # 求解
            print("\n[2/3] 求解网络...")
            success = self.model.solve()
            
            if not success:
                print("✗ 模型未能收敛")
                return False
            
            print("✓ 模型收敛成功")
            
            # 收集收敛指标
            print("\n[3/3] 收集收敛指标...")
            self._collect_convergence_metrics()
            print("✓ 收敛指标已收集")
            
            return True
            
        except Exception as e:
            print(f"✗ 验证失败，错误信息: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _collect_convergence_metrics(self) -> None:
        """从已收敛的模型中收集收敛指标和关键输出"""
        if not self.model or not self.model.nw or not self.model.nw.converged:
            return
        
        nw = self.model.nw
        
        self.convergence_metrics = {
            "converged": nw.converged,
            "num_iterations": nw.iter,
            "num_components": len(nw.comps),
            "num_connections": len(nw.conns),
            "residual": float(nw.vec_res.max()) if hasattr(nw, 'vec_res') else None,
        }
        
        # 收集关键输出
        self._collect_key_outputs()

    def _collect_key_outputs(self) -> None:
        """收集关键输出指标（主蒸汽状态、功率等）"""
        if not self.model or not self.model.nw:
            self.key_outputs = {}
            return
        
        outputs: dict[str, Any] = {}
        nw = self.model.nw
        
        # 主蒸汽状态
        try:
            main_conn = nw.get_conn("1#发电锅炉_主蒸汽")
            if main_conn is not None:
                outputs["主蒸汽状态"] = {
                    "质量流量_t每小时": float(main_conn.m.val) if hasattr(main_conn.m, "val") else None,
                    "压力_bar": float(main_conn.p.val) if hasattr(main_conn.p, "val") else None,
                    "温度_摄氏": float(main_conn.T.val) if hasattr(main_conn.T, "val") else None,
                    "焓_kJ每千克": float(main_conn.h.val) if hasattr(main_conn.h, "val") else None,
                }
        except Exception:
            pass
        
        # 烟气出口状态
        try:
            flue_conn = nw.get_conn("1#发电锅炉_煤预烟气出口")
            if flue_conn is not None:
                outputs["烟气出口状态"] = {
                    "质量流量_t每小时": float(flue_conn.m.val) if hasattr(flue_conn.m, "val") else None,
                    "压力_bar": float(flue_conn.p.val) if hasattr(flue_conn.p, "val") else None,
                    "温度_摄氏": float(flue_conn.T.val) if hasattr(flue_conn.T, "val") else None,
                }
        except Exception:
            pass
        
        # 关键功率指标
        if self.model.results:
            outputs["功率汇总"] = {
                "汽轮机总功率_MW": round(self.model.results.get("P_turbine_total_MW", 0.0), 3),
                "泵功率_MW": round(self.model.results.get("P_pump_MW", 0.0), 3),
                "净功率_MW": round(self.model.results.get("P_net_MW", 0.0), 3),
            }
        
        # 汽轮机分段功率
        turbine_names = [
            "抽凝式汽轮机1_高压缸一段",
            "抽凝式汽轮机1_高压缸二段",
            "抽凝式汽轮机1_低压缸一段",
            "抽凝式汽轮机1_低压缸二段",
            "抽凝式汽轮机1_低压缸三段",
            "抽凝式汽轮机1_低压缸四段",
            "抽凝式汽轮机1_低压缸五段",
            "抽凝式汽轮机1_低压缸六段",
            "抽凝式汽轮机1_低压缸七段",
        ]
        turbine_output = []
        for name in turbine_names:
            try:
                comp = nw.get_comp(name)
                if comp is not None and hasattr(comp, "P") and hasattr(comp.P, "val"):
                    turbine_output.append({
                        "名称": name,
                        "功率_MW": round(abs(comp.P.val) / 1e6, 3),
                    })
            except Exception:
                continue
        if turbine_output:
            outputs["汽轮机分段功率"] = turbine_output
        
        self.key_outputs = outputs

    def compare_with_reference(self) -> dict[str, Any]:
        """
        将当前仿真输出与参考数据进行对比
        
        返回：
            包含对比结果的字典
        """
        print("\n" + "=" * 80)
        print("与参考数据对比")
        print("=" * 80)
        
        if not self.model or not self.model.nw or not self.model.nw.converged:
            print("✗ 模型未收敛，无法进行对比")
            return {}
        
        results = {
            "connections": self._compare_connections(),
            "components": self._compare_components(),
            "summary": {},
        }
        
        # Generate summary
        results["summary"] = self._generate_comparison_summary(results)
        
        # Calculate error statistics
        self.error_statistics = self._calculate_error_statistics(results)
        
        self.comparison_results = results
        return results

    def _compare_connections(self) -> dict[str, Any]:
        """对比连接状态并收集详细差异数据"""
        if "connections" not in self.reference_data:
            return {"错误": "未找到参考连接数据"}
        
        ref_df = self.reference_data["connections"]
        comparison = {
            "total_connections": len(ref_df),
            "compared_connections": 0,
            "matches": [],
            "differences": [],
            "missing": [],
            "records": [],
        }
        
        for label in ref_df.index:
            try:
                conn = self.model.nw.get_conn(label)
                if conn is None:
                    comparison["missing"].append(label)
                    continue
                
                # 参考值
                ref_m = ref_df.loc[label, "m"] if pd.notna(ref_df.loc[label, "m"]) else None
                ref_p = ref_df.loc[label, "p"] if pd.notna(ref_df.loc[label, "p"]) else None
                ref_T = ref_df.loc[label, "T"] if pd.notna(ref_df.loc[label, "T"]) else None
                ref_h = ref_df.loc[label, "h"] if pd.notna(ref_df.loc[label, "h"]) else None
                
                # 仿真值
                curr_m = conn.m.val if hasattr(conn.m, "val") else None
                curr_p = conn.p.val if hasattr(conn.p, "val") else None
                curr_T = conn.T.val if hasattr(conn.T, "val") else None
                curr_h = conn.h.val if hasattr(conn.h, "val") else None
                
                conn_result = {
                    "label": label,
                    "mass_flow": self._compare_value(curr_m, ref_m, "mass_flow") if ref_m is not None else None,
                    "pressure": self._compare_value(curr_p, ref_p, "pressure") if ref_p is not None else None,
                    "temperature": self._compare_value(curr_T, ref_T, "temperature") if ref_T is not None else None,
                    "enthalpy": self._compare_value(curr_h, ref_h, "enthalpy") if ref_h is not None else None,
                }
                
                comparison["compared_connections"] += 1
                comparison["records"].append(conn_result)
                
                all_ok = all(
                    v is None or v.get("within_tolerance", True)
                    for k, v in conn_result.items() if k != "label"
                )
                
                if all_ok:
                    comparison["matches"].append(label)
                else:
                    comparison["differences"].append(conn_result)
            except Exception as e:
                print(f"⚠ 对比连接 {label} 时出错：{e}")
        
        return comparison

    def _compare_components(self) -> dict[str, Any]:
        """对比关键组件参数并生成统计信息"""
        comparison: dict[str, Any] = {
            "turbines": [],
            "heat_exchangers": [],
            "statistics": {},
        }
        
        # 汽轮机功率对比
        if "Turbine" in self.reference_data:
            ref_df = self.reference_data["Turbine"]
            abs_all: list[float] = []
            rel_all: list[float] = []
            abs_outside: list[float] = []
            rel_outside: list[float] = []
            
            for name in ref_df.index:
                try:
                    comp = self.model.nw.get_comp(name)
                    if comp is None:
                        continue
                    
                    ref_P = ref_df.loc[name, "P"] if pd.notna(ref_df.loc[name, "P"]) else None
                    curr_P = comp.P.val if hasattr(comp, "P") and hasattr(comp.P, "val") else None
                    
                    if ref_P is not None and curr_P is not None:
                        ref_P_MW = abs(ref_P) / 1e6
                        curr_P_MW = abs(curr_P) / 1e6
                        power_cmp = self._compare_value(curr_P_MW, ref_P_MW, "power")
                        result = {
                            "name": name,
                            "power": power_cmp,
                        }
                        comparison["turbines"].append(result)
                        
                        if power_cmp and isinstance(power_cmp, dict):
                            abs_diff = power_cmp.get("absolute_difference")
                            rel_diff = power_cmp.get("relative_difference")
                            within = power_cmp.get("within_tolerance", True)
                            if abs_diff is not None:
                                abs_all.append(abs_diff)
                                if not within:
                                    abs_outside.append(abs_diff)
                            if rel_diff is not None:
                                rel_all.append(rel_diff)
                                if not within:
                                    rel_outside.append(rel_diff)
                except Exception as e:
                    print(f"⚠ 对比汽轮机 {name} 时出错：{e}")
            
            if abs_all:
                comparison["statistics"]["汽轮机功率"] = {
                    "平均绝对误差": round(sum(abs_all) / len(abs_all), 5),
                    "最大绝对误差": round(max(abs_all), 5),
                    "平均相对误差": f"{(sum(rel_all) / len(rel_all)):.2%}" if rel_all else "N/A",
                    "最大相对误差": f"{max(rel_all):.2%}" if rel_all else "N/A",
                    "样本数量": len(abs_all),
                    "超差数量": len(abs_outside),
                }
        
        # 换热器传热量对比
        if "HeatExchanger" in self.reference_data:
            ref_df = self.reference_data["HeatExchanger"]
            abs_all_hx: list[float] = []
            rel_all_hx: list[float] = []
            abs_outside_hx: list[float] = []
            rel_outside_hx: list[float] = []
            
            for name in ref_df.index:
                try:
                    comp = self.model.nw.get_comp(name)
                    if comp is None:
                        continue
                    
                    ref_Q = ref_df.loc[name, "Q"] if pd.notna(ref_df.loc[name, "Q"]) else None
                    curr_Q = comp.Q.val if hasattr(comp, "Q") and hasattr(comp.Q, "val") else None
                    
                    if ref_Q is not None and curr_Q is not None:
                        ref_Q_MW = abs(ref_Q) / 1e6
                        curr_Q_MW = abs(curr_Q) / 1e6
                        heat_cmp = self._compare_value(curr_Q_MW, ref_Q_MW, "power")
                        result = {
                            "name": name,
                            "heat_transfer": heat_cmp,
                        }
                        comparison["heat_exchangers"].append(result)
                        
                        if heat_cmp and isinstance(heat_cmp, dict):
                            abs_diff = heat_cmp.get("absolute_difference")
                            rel_diff = heat_cmp.get("relative_difference")
                            within = heat_cmp.get("within_tolerance", True)
                            if abs_diff is not None:
                                abs_all_hx.append(abs_diff)
                                if not within:
                                    abs_outside_hx.append(abs_diff)
                            if rel_diff is not None:
                                rel_all_hx.append(rel_diff)
                                if not within:
                                    rel_outside_hx.append(rel_diff)
                except Exception as e:
                    print(f"⚠ 对比换热器 {name} 时出错：{e}")
            
            if abs_all_hx:
                comparison["statistics"]["换热器传热量"] = {
                    "平均绝对误差": round(sum(abs_all_hx) / len(abs_all_hx), 5),
                    "最大绝对误差": round(max(abs_all_hx), 5),
                    "平均相对误差": f"{(sum(rel_all_hx) / len(rel_all_hx)):.2%}" if rel_all_hx else "N/A",
                    "最大相对误差": f"{max(rel_all_hx):.2%}" if rel_all_hx else "N/A",
                    "样本数量": len(abs_all_hx),
                    "超差数量": len(abs_outside_hx),
                }
        
        return comparison

    def _compare_value(self, current: float, reference: float, value_type: str) -> dict[str, Any]:
        """
        Compare a single value with reference using tolerances
        
        Args:
            current: Current simulation value
            reference: Reference value
            value_type: Type of value (for tolerance lookup)
            
        Returns:
            Dictionary with comparison results
        """
        if current is None or reference is None:
            return {"current": current, "reference": reference, "error": "Missing value"}
        
        tol = self.tolerances.get(value_type, {"absolute": 0, "relative": 0})
        
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

    def _generate_comparison_summary(self, results: dict) -> dict[str, Any]:
        """Generate summary statistics from comparison results"""
        conn_results = results.get("connections", {})
        
        total_conns = conn_results.get("total_connections", 0)
        compared = conn_results.get("compared_connections", 0)
        matches = len(conn_results.get("matches", []))
        differences = len(conn_results.get("differences", []))
        missing = len(conn_results.get("missing", []))
        
        match_rate = matches / compared if compared > 0 else 0
        
        return {
            "total_connections": total_conns,
            "compared_connections": compared,
            "matching_connections": matches,
            "differing_connections": differences,
            "missing_connections": missing,
            "match_rate": match_rate,
            "coverage": compared / total_conns if total_conns > 0 else 0,
        }
    
    def _calculate_error_statistics(self, results: dict) -> dict[str, Any]:
        """计算误差统计信息（绝对误差、相对误差的最大值、平均值等）"""
        stats: dict[str, Any] = {}
        
        conn_results = results.get("connections", {})
        records = conn_results.get("records", [])
        
        if not records:
            return stats
        
        param_types = ["mass_flow", "pressure", "temperature", "enthalpy"]
        param_cn = {
            "mass_flow": "质量流量",
            "pressure": "压力",
            "temperature": "温度",
            "enthalpy": "焓",
        }
        
        for param in param_types:
            abs_all: list[float] = []
            rel_all: list[float] = []
            abs_outside: list[float] = []
            rel_outside: list[float] = []
            
            for record in records:
                data = record.get(param)
                if data and isinstance(data, dict) and "absolute_difference" in data:
                    abs_value = data.get("absolute_difference")
                    rel_value = data.get("relative_difference")
                    within = data.get("within_tolerance", True)
                    if abs_value is not None:
                        abs_all.append(abs_value)
                        if not within:
                            abs_outside.append(abs_value)
                    if rel_value is not None:
                        rel_all.append(rel_value)
                        if not within:
                            rel_outside.append(rel_value)
            
            if abs_all:
                stats[param_cn.get(param, param)] = {
                    "平均绝对误差": round(sum(abs_all) / len(abs_all), 5),
                    "最大绝对误差": round(max(abs_all), 5),
                    "平均相对误差": f"{(sum(rel_all) / len(rel_all)):.2%}" if rel_all else "N/A",
                    "最大相对误差": f"{max(rel_all):.2%}" if rel_all else "N/A",
                    "样本数量": len(abs_all),
                    "超差数量": len(abs_outside),
                    "超差平均绝对误差": round(sum(abs_outside) / len(abs_outside), 5) if abs_outside else 0.0,
                    "超差最大绝对误差": round(max(abs_outside), 5) if abs_outside else 0.0,
                }
        
        return stats

    def _generate_validation_conclusion(self) -> dict[str, str]:
        """生成验证结论"""
        conclusion = {}
        
        # 收敛性结论
        if self.convergence_metrics:
            converged = self.convergence_metrics.get("converged", False)
            conclusion["收敛性"] = "模型成功收敛" if converged else "模型未能收敛"
            
            iterations = self.convergence_metrics.get("num_iterations")
            if iterations:
                conclusion["收敛迭代"] = f"经过 {iterations} 次迭代达到收敛"
        
        # 对比结论
        if self.comparison_results and "summary" in self.comparison_results:
            summary = self.comparison_results["summary"]
            match_rate = summary.get("match_rate", 0)
            
            if match_rate >= 0.95:
                conclusion["一致性"] = "优秀 - 超过95%的连接在容差范围内"
            elif match_rate >= 0.85:
                conclusion["一致性"] = "良好 - 超过85%的连接在容差范围内"
            elif match_rate >= 0.70:
                conclusion["一致性"] = "中等 - 超过70%的连接在容差范围内，建议检查差异较大的连接"
            else:
                conclusion["一致性"] = "较差 - 匹配率低于70%，需要进一步检查模型设置"
            
            conclusion["匹配率"] = f"{match_rate:.2%}"
            conclusion["已对比连接数"] = f"{summary.get('compared_connections', 0)} / {summary.get('total_connections', 0)}"
        
        # 总体结论
        if self.convergence_metrics and self.comparison_results:
            converged = self.convergence_metrics.get("converged", False)
            match_rate = self.comparison_results.get("summary", {}).get("match_rate", 0)
            
            if converged and match_rate >= 0.85:
                conclusion["总体评价"] = "✅ 通过 - 模型成功收敛且仿真结果与参考数据一致性良好"
            elif converged and match_rate >= 0.70:
                conclusion["总体评价"] = "⚠️ 有条件通过 - 模型收敛但部分结果存在差异"
            elif converged:
                conclusion["总体评价"] = "⚠️ 需改进 - 模型收敛但与参考数据差异较大"
            else:
                conclusion["总体评价"] = "❌ 未通过 - 模型未能收敛"
        
        return conclusion
    
    def _generate_io_mapping(self) -> dict[str, Any]:
        """生成模型输入输出对应关系说明"""
        mapping = {
            "固定输入边界条件": {
                "蒸汽侧": {
                    "主蒸汽": "质量流量、压力、温度 (1#发电锅炉_主蒸汽)",
                    "泵入口": "压力、温度 (1#发电锅炉_水泵入口)",
                    "汽包饱和蒸汽": "干度 x=1.0 (1#发电锅炉_汽包饱和蒸汽出口)",
                    "高压缸排汽抽汽": "质量流量 (抽凝式汽轮机1_高压缸排汽抽汽)",
                },
                "空气侧": {
                    "空气入口": "质量流量、压力、温度、组分 (1#发电锅炉_空气入口)",
                },
                "燃料侧": {
                    "高炉煤气": "质量流量、压力、温度、组分 (boiler1_高炉煤气入口)",
                    "转炉煤气": "质量流量、压力、温度、组分 (1#发电锅炉_转炉煤气入口)",
                    "焦炉煤气": "质量流量、压力、温度、组分 (1#发电锅炉_焦炉煤气入口)",
                },
            },
            "初始值引导": {
                "说明": "所有中间连接状态使用 CSV 参考数据作为初始值 (p0, T0, m0)，不固定约束",
                "作用": "提供良好的初始猜测值以加快收敛速度",
            },
            "关键输出": {
                "汽轮机功率": "各段汽轮机的输出功率 (MW)",
                "泵功": "给水泵消耗功率 (MW)",
                "净功率": "汽轮机总功率减去泵功 (MW)",
                "主蒸汽状态": "主蒸汽的压力、温度、焓、质量流量",
                "烟气出口状态": "烟气排放的温度、压力、组分",
            },
            "参考数据来源": {
                "连接数据": "boiler-turbine_design_state/connections.csv",
                "组件数据": "boiler-turbine_design_state/components/*.csv",
            },
            "对应关系检查": {
                "连接对比": "逐一对比模型计算的连接状态与 CSV 参考值",
                "组件对比": "对比汽轮机功率、换热器传热量等关键组件参数",
                "容差判定": "使用预设的绝对和相对容差判定一致性",
            },
        }
        
        return mapping

    def generate_json_report(self) -> None:
        """生成包含中文描述的 JSON 验证报告"""
        output_file = self.output_dir / "验证报告.json"
        
        report = {
            "报告类型": "Stage2 详细模型验证报告",
            "validation_type": "Stage2 Detailed Model Verification",
            "生成时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "收敛指标": {
                "原始数据": self.convergence_metrics,
                "中文描述": {
                    "是否收敛": "是" if self.convergence_metrics.get("converged", False) else "否",
                    "迭代次数": self.convergence_metrics.get("num_iterations"),
                    "组件数量": self.convergence_metrics.get("num_components"),
                    "连接数量": self.convergence_metrics.get("num_connections"),
                    "最大残差": self.convergence_metrics.get("residual"),
                }
            } if self.convergence_metrics else {},
            "关键输出": self.key_outputs,
            "对比结果": {
                "连接对比": self.comparison_results.get("connections", {}),
                "组件对比": self.comparison_results.get("components", {}),
                "汇总统计": self.comparison_results.get("summary", {}),
            } if self.comparison_results else {},
            "误差统计": self.error_statistics,
            "容差设定": {
                "质量流量": {"绝对容差": self.tolerances["mass_flow"]["absolute"], "相对容差": self.tolerances["mass_flow"]["relative"], "单位": "t/h"},
                "压力": {"绝对容差": self.tolerances["pressure"]["absolute"], "相对容差": self.tolerances["pressure"]["relative"], "单位": "bar"},
                "温度": {"绝对容差": self.tolerances["temperature"]["absolute"], "相对容差": self.tolerances["temperature"]["relative"], "单位": "°C"},
                "焓": {"绝对容差": self.tolerances["enthalpy"]["absolute"], "相对容差": self.tolerances["enthalpy"]["relative"], "单位": "kJ/kg"},
                "功率": {"绝对容差": self.tolerances["power"]["absolute"], "相对容差": self.tolerances["power"]["relative"], "单位": "MW"},
            },
            "验证结论": self._generate_validation_conclusion(),
            "模型输入输出对应关系": self._generate_io_mapping(),
        }
        
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ JSON 报告已保存至: {output_file}")

    def generate_markdown_report(self) -> None:
        """生成中文 Markdown 验证报告"""
        output_file = self.output_dir / "验证报告.md"
        
        lines = [
            "# Stage2 详细模型验证报告",
            "",
            "## 概要总结",
            "",
        ]
        
        # 收敛状态
        if self.convergence_metrics:
            converged = self.convergence_metrics.get("converged", False)
            status = "✅ 通过" if converged else "❌ 失败"
            lines.extend([
                f"**收敛状态：** {status}",
                "",
                "## 收敛指标",
                "",
                "| 指标 | 数值 |",
                "|------|------|",
            ])
            
            metric_names = {
                "converged": "是否收敛",
                "num_iterations": "迭代次数",
                "num_components": "组件数量",
                "num_connections": "连接数量",
                "residual": "最大残差",
            }
            
            for key, value in self.convergence_metrics.items():
                if value is not None:
                    cn_name = metric_names.get(key, key)
                    if key == "converged":
                        value = "是" if value else "否"
                    lines.append(f"| {cn_name} | {value} |")
            
            lines.append("")
        
        # 对比汇总
        if self.comparison_results and "summary" in self.comparison_results:
            summary = self.comparison_results["summary"]
            lines.extend([
                "## 对比汇总",
                "",
                "| 指标 | 数值 |",
                "|------|------|",
            ])
            
            summary_names = {
                "total_connections": "总连接数",
                "compared_connections": "已对比连接数",
                "matching_connections": "匹配连接数",
                "differing_connections": "有差异连接数",
                "missing_connections": "缺失连接数",
                "match_rate": "匹配率",
                "coverage": "覆盖率",
            }
            
            for key, value in summary.items():
                cn_name = summary_names.get(key, key)
                if isinstance(value, float):
                    lines.append(f"| {cn_name} | {value:.2%} |")
                else:
                    lines.append(f"| {cn_name} | {value} |")
            
            lines.append("")
        
        # 容差设定
        lines.extend([
            "## 容差设定",
            "",
            "| 参数 | 绝对容差 | 相对容差 |",
            "|------|----------|----------|",
        ])
        
        param_names = {
            "mass_flow": "质量流量",
            "pressure": "压力",
            "temperature": "温度",
            "enthalpy": "焓",
            "power": "功率",
        }
        
        for param, tol in self.tolerances.items():
            cn_param = param_names.get(param, param)
            lines.append(
                f"| {cn_param} | "
                f"±{tol['absolute']} | ±{tol['relative']:.1%} |"
            )
        
        lines.append("")
        
        # 关键输出
        if self.key_outputs:
            lines.extend([
                "## 关键输出",
                "",
            ])
            
            if "主蒸汽状态" in self.key_outputs:
                steam_state = self.key_outputs["主蒸汽状态"]
                lines.extend([
                    "### 主蒸汽状态",
                    "",
                    "| 参数 | 数值 |",
                    "|------|------|",
                ])
                for key, value in steam_state.items():
                    if value is not None:
                        key_cn = key.replace("_", " ")
                        lines.append(f"| {key_cn} | {value:.4f} |")
                lines.append("")
            
            if "功率汇总" in self.key_outputs:
                power_sum = self.key_outputs["功率汇总"]
                lines.extend([
                    "### 功率汇总",
                    "",
                    "| 指标 | 数值 (MW) |",
                    "|------|-----------|",
                ])
                for key, value in power_sum.items():
                    key_cn = key.replace("_", " ")
                    lines.append(f"| {key_cn} | {value:.3f} |")
                lines.append("")
            
            if "汽轮机分段功率" in self.key_outputs:
                turb_powers = self.key_outputs["汽轮机分段功率"]
                lines.extend([
                    "### 汽轮机分段功率",
                    "",
                    "| 段名 | 功率 (MW) |",
                    "|------|-----------|",
                ])
                for item in turb_powers:
                    lines.append(f"| {item['名称']} | {item['功率_MW']:.3f} |")
                lines.append("")
        
        # 误差统计
        if self.error_statistics:
            lines.extend([
                "## 误差统计",
                "",
            ])
            
            for param_name, stats in self.error_statistics.items():
                lines.extend([
                    f"### {param_name}",
                    "",
                    "| 统计指标 | 数值 |",
                    "|----------|------|",
                ])
                for stat_name, stat_value in stats.items():
                    lines.append(f"| {stat_name} | {stat_value} |")
                lines.append("")
        
        # 差异详情
        if self.comparison_results and "connections" in self.comparison_results:
            conn_comp = self.comparison_results["connections"]
            differences = conn_comp.get("differences", [])
            
            if differences:
                lines.extend([
                    "## 超出容差的连接",
                    "",
                    f"发现 {len(differences)} 个连接超出容差范围：",
                    "",
                ])
                
                param_cn = {
                    "mass_flow": "质量流量",
                    "pressure": "压力",
                    "temperature": "温度",
                    "enthalpy": "焓",
                }
                
                for diff in differences[:10]:  # 限制前10个
                    label = diff.get("label", "未知")
                    lines.append(f"### {label}")
                    lines.append("")
                    
                    for param, values in diff.items():
                        if param == "label" or values is None:
                            continue
                        
                        if isinstance(values, dict) and "current" in values:
                            within = "✓" if values.get("within_tolerance", False) else "✗"
                            param_name = param_cn.get(param, param)
                            lines.append(
                                f"- **{param_name}** {within}: "
                                f"当前值={values['current']:.3f}, "
                                f"参考值={values['reference']:.3f}, "
                                f"绝对差异={values['absolute_difference']:.3f} "
                                f"(相对差异 {values['relative_difference']:.1%})"
                            )
                    
                    lines.append("")
                
                if len(differences) > 10:
                    lines.append(f"*...还有 {len(differences) - 10} 个*")
                    lines.append("")
        
        # 缺失连接
        if self.comparison_results and "connections" in self.comparison_results:
            missing = self.comparison_results["connections"].get("missing", [])
            if missing:
                lines.extend([
                    "## 缺失连接",
                    "",
                    f"以下 {len(missing)} 个连接存在于参考数据中但在模型中未找到：",
                    "",
                ])
                for label in missing:
                    lines.append(f"- {label}")
                lines.append("")
        
        # 组件对比
        if self.comparison_results and "components" in self.comparison_results:
            comp_results = self.comparison_results["components"]
            
            if comp_results.get("turbines"):
                lines.extend([
                    "## 汽轮机功率对比",
                    "",
                    "| 组件名称 | 当前值 (MW) | 参考值 (MW) | 差异 (MW) | 状态 |",
                    "|----------|-------------|-------------|-----------|------|",
                ])
                
                for turb in comp_results["turbines"]:
                    power = turb.get("power", {})
                    if isinstance(power, dict):
                        curr = power.get("current", 0)
                        ref = power.get("reference", 0)
                        diff = power.get("absolute_difference", 0)
                        status = "✓" if power.get("within_tolerance", False) else "✗"
                        lines.append(
                            f"| {turb['name']} | {curr:.3f} | {ref:.3f} | {diff:.3f} | {status} |"
                        )
                
                lines.append("")
        
        # 模型输入输出对应关系
        lines.extend([
            "## 模型输入输出对应关系",
            "",
            "### 固定输入边界条件",
            "",
            "**蒸汽侧：**",
            "- 主蒸汽：质量流量、压力、温度",
            "- 泵入口（凝结水）：压力、温度",
            "- 汽包饱和蒸汽：干度 x=1.0",
            "- 高压缸排汽抽汽：质量流量",
            "",
            "**空气侧：**",
            "- 空气入口：质量流量、压力、温度、组分",
            "",
            "**燃料侧：**",
            "- 高炉煤气：质量流量、压力、温度、组分",
            "- 转炉煤气：质量流量、压力、温度、组分",
            "- 焦炉煤气：质量流量、压力、温度、组分",
            "",
            "### 初始值引导",
            "",
            "所有中间连接状态使用参考 CSV 数据作为初始值（p0, T0, m0），不固定约束。",
            "这些初始值提供良好的起点以加快收敛速度。",
            "",
            "### 关键输出",
            "",
            "- **汽轮机功率**：各段汽轮机的输出功率 (MW)",
            "- **泵功**：给水泵消耗功率 (MW)",
            "- **净功率**：汽轮机总功率减去泵功 (MW)",
            "- **主蒸汽状态**：压力、温度、焓、质量流量",
            "- **烟气出口状态**：温度、压力、组分",
            "",
        ])
        
        # 验证结论
        if self.comparison_results or self.convergence_metrics:
            conclusion = self._generate_validation_conclusion()
            lines.extend([
                "## 验证结论",
                "",
            ])
            
            for key, value in conclusion.items():
                lines.append(f"**{key}：** {value}")
                lines.append("")
        
        # 数据来源
        lines.extend([
            "## 参考数据来源",
            "",
            "- **连接数据：** `boiler-turbine_design_state/connections.csv`",
            "- **组件数据：** `boiler-turbine_design_state/components/*.csv`",
            "",
            "## 使用说明",
            "",
            "### 重新运行验证",
            "",
            "```bash",
            "python validate_stage2_model.py --output-dir validation_results",
            "```",
            "",
            "### 指定参考数据路径",
            "",
            "```bash",
            "python validate_stage2_model.py --reference-path /path/to/reference/data --output-dir results",
            "```",
            "",
            "---",
            "",
            f"*报告生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
        ])
        
        # 写入报告
        with output_file.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"✓ Markdown 报告已保存至: {output_file}")

    def generate_repair_documentation(self) -> None:
        """生成模型修复与验证分析文档（中文）"""
        output_file = self.output_dir / "REPAIR_AND_VALIDATION_ANALYSIS.md"
        
        lines: list[str] = [
            "# Stage2 模型修复与验证分析",
            "",
            "## 文档目的",
            "",
            "本文件汇总 Stage2 详细模型在重构后的修复思路、关键调整、验证统计结果以及后续建议，便于团队复现验证流程并理解模型输入输出的一致性关系。",
            "",
            "## 问题背景",
            "",
            "- 原始模型在不依赖导出状态初始值的情况下无法稳定收敛。",
            "- 过多的固定边界条件导致方程组被过度约束，出现求解自由度不足的问题。",
            "- 部分组件（汽包、抽汽点）存在方程冲突或循环依赖，影响整体收敛。",
            "",
            "## 修复策略",
            "",
            "1. **区分固定边界与初始值**：仅对真实外部输入（主蒸汽、燃料、空气、给水入口等）设置固定约束，其余连接全部使用 `p0/T0/m0` 初始值指引求解。",
            "2. **保留组件内在方程**：保持汽轮机、换热器、燃烧室等组件自身的效率、压比、传热系数等设计参数不变，让方程自行求解。",
            "3. **统一抽汽与流量处理**：对参考数据中为 0 的抽汽流量采用初始值指导，避免人为固定 0 造成数值震荡。",
            "4. **强化日志与验证脚本**：通过验证脚本输出收敛信息、关键性能指标与误差统计，形成自动化验证能力。",
            "",
        ]
        
        if self.convergence_metrics:
            converged = self.convergence_metrics.get("converged", False)
            iterations = self.convergence_metrics.get("num_iterations", "未知")
            lines.extend([
                "## 收敛情况",
                "",
                f"- 求解状态：{'✅ 已收敛' if converged else '❌ 未收敛'}",
                f"- 迭代次数：{iterations}",
                f"- 组件数量：{self.convergence_metrics.get('num_components', '未知')}",
                f"- 连接数量：{self.convergence_metrics.get('num_connections', '未知')}",
                f"- 最大残差：{self.convergence_metrics.get('residual', '未知')}",
                "",
            ])
        
        if self.comparison_results and "summary" in self.comparison_results:
            summary = self.comparison_results["summary"]
            match_rate = summary.get("match_rate", 0)
            lines.extend([
                "## 与参考数据的一致性",
                "",
                f"- 匹配率：{match_rate:.2%}",
                f"- 已对比连接 / 总连接：{summary.get('compared_connections', 0)} / {summary.get('total_connections', 0)}",
                f"- 在容差内的连接数：{summary.get('matching_connections', 0)}",
                f"- 超出容差的连接数：{summary.get('differing_connections', 0)}",
                f"- 参考数据缺失或模型缺失的连接数：{summary.get('missing_connections', 0)}",
                "",
            ])
        
        if self.error_statistics:
            lines.extend([
                "### 误差统计概览",
                "",
            ])
            for param_name, stats in self.error_statistics.items():
                lines.append(f"- {param_name}：平均绝对误差 {stats.get('平均绝对误差')}，最大绝对误差 {stats.get('最大绝对误差')}，超差数量 {stats.get('超差数量')}。")
            lines.append("")
        
        if self.key_outputs:
            lines.extend([
                "## 关键输出指标",
                "",
            ])
            if "功率汇总" in self.key_outputs:
                kpi = self.key_outputs["功率汇总"]
                lines.extend([
                    f"- 汽轮机总功率：{kpi.get('汽轮机总功率_MW', 'N/A')} MW",
                    f"- 泵功率：{kpi.get('泵功率_MW', 'N/A')} MW",
                    f"- 净功率：{kpi.get('净功率_MW', 'N/A')} MW",
                    "",
                ])
            if "主蒸汽状态" in self.key_outputs:
                steam = self.key_outputs["主蒸汽状态"]
                lines.extend([
                    "- 主蒸汽状态：",
                    f"  * 质量流量：{steam.get('质量流量_t每小时')} t/h",
                    f"  * 压力：{steam.get('压力_bar')} bar",
                    f"  * 温度：{steam.get('温度_摄氏')} °C",
                    f"  * 焓值：{steam.get('焓_kJ每千克')} kJ/kg",
                    "",
                ])
        
        lines.extend([
            "## 模型输入输出对应关系",
            "",
            "- 固定输入：主蒸汽、给水入口、空气入口以及三路燃料气入口均与 CSV 中的值严格对齐，用于保证边界一致。",
            "- 初始引导：其它中间连接读取 CSV 的 p/T/m 作为初值，确保数值解沿着参考工况维持合理起点。",
            "- 输出指标：汽轮机功率、泵功率、主蒸汽与烟气状态可直接与 CSV 中的 `connections.csv` 和 `components/*.csv` 项进行逐列比较。",
            "",
            "## 使用建议",
            "",
            "1. 每次修改模型或组件参数后，运行 `python validate_stage2_model.py` 重新生成报告。",
            "2. 对差异较大的连接，优先检查对应的边界条件、流体组分及组件参数设置。",
            "3. 建议将验证脚本纳入 CI 流程，自动对比新旧模型结果，防止回归。",
            "4. 若需扩展模型，可沿用“固定输入 + 初始值引导”的策略，避免再次出现过度约束。",
            "",
            "## 参考资料",
            "",
            "- 参考数据目录：`boiler-turbine_design_state/`",
            "- 模型实现：`stage2_detailed_model.py`",
            "- 验证脚本：`validate_stage2_model.py`",
            "",
        ])
        
        with output_file.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"✓ 模型修复分析文档已生成: {output_file}")

    def run_full_validation(self) -> bool:
        """
        执行完整的验证流程
        
        返回：
            验证通过返回 True，否则返回 False
        """
        print("\n" + "=" * 80)
        print("STAGE2 模型验证流程")
        print("=" * 80)
        
        # 步骤 1：加载参考数据
        self.load_reference_data()
        
        # 步骤 2：验证模型收敛性
        converged = self.verify_model_convergence()
        
        if not converged:
            print("\n" + "=" * 80)
            print("验证结果：❌ 失败（模型未收敛）")
            print("=" * 80)
            
            # 仍然生成已有信息的报告
            self.generate_json_report()
            self.generate_markdown_report()
            self.generate_repair_documentation()
            
            return False
        
        # 步骤 3：与参考数据对比
        self.compare_with_reference()
        
        # 步骤 4：分析模型结果
        if self.model:
            self.model.analyze()
            self._collect_key_outputs()
        
        # 步骤 5：生成报告
        self.generate_json_report()
        self.generate_markdown_report()
        self.generate_repair_documentation()
        
        # 依据匹配率判定是否通过
        if self.comparison_results and "summary" in self.comparison_results:
            match_rate = self.comparison_results["summary"].get("match_rate", 0)
            passed = match_rate >= 0.85  # 85% 为通过阈值
        else:
            passed = False
        
        print("\n" + "=" * 80)
        if passed:
            print("验证结果：✅ 通过")
        else:
            print("验证结果：⚠️ 警告通过（请检查报告详情）")
        print("=" * 80)
        
        print(f"\n报告已输出至: {self.output_dir}")
        print("  - 验证报告.json（包含完整数据、中文字段说明）")
        print("  - 验证报告.md（中文详细报告，含关键输出、误差统计）")
        print("  - REPAIR_AND_VALIDATION_ANALYSIS.md（技术分析报告）")
        
        return passed


def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Stage2 详细模型验证"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation_results"),
        help="报告输出目录"
    )
    parser.add_argument(
        "--reference-path",
        type=Path,
        default=None,
        help="参考 CSV 数据路径"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger("tespy").setLevel(logging.WARNING)
    
    # 创建验证器并执行
    validator = Stage2ModelValidator(
        reference_path=args.reference_path,
        output_dir=args.output_dir
    )
    
    success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
