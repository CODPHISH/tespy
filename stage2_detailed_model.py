#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2详细建模：简化的锅炉-汽轮机联合循环系统.

本模型聚焦于主蒸汽 → 再热 → 汽轮机 → 凝汽 → 给水泵的核心热力循环，
用于验证设计点热性能与关键状态参数。

⚠️ 注意：
- 本代码为教学与研究用的“简化”模型，不包含燃烧室、汽包循环、抽汽回热等复杂设备。
- 项目中的 `boiler-turbine_design_state/connections.csv` 描述的是完整电厂模型
  （包含多燃料混烧、汽包水循环、抽汽回热、SCR脱硫脱硝及多级阀门等）。
- 若需要该完整模型，请参考 CSV 与组件参数文件自行搭建。

模型结构：
- 换热器：下级省煤器 → 上级省煤器 → 蒸发器上升管 → 低温过热器 → 屏式过热器 → 三级过热器 → 末级过热器
- 再热器：低温再热器 → 末级再热器
- 汽轮机：高压缸（2段）→ 低压缸（7段）
- 泵：给水泵
- 凝汽器：用 CycleCloser + 定压连接近似

运行：
    python stage2_detailed_model.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from tespy.networks import Network
from tespy.components import (
    CycleCloser,
    HeatExchanger,
    Turbine,
    Pump,
    Source,
    Sink,
)
from tespy.connections import Connection


class DetailedBoilerTurbineModel:
    """详细建模：完整的锅炉-汽轮机联合循环系统（基于真实工况参数）."""

    def __init__(self) -> None:
        """初始化参数（从参考数据提取）."""
        self.params = {
            # 主蒸汽参数 (287.62 t/h = 79.89 kg/s)
            "steam_m": 79.89,              # kg/s
            "steam_p": 161.0,              # bar
            "steam_T": 560.0,              # °C
            
            # 再热蒸汽参数 (267.62 t/h = 74.34 kg/s)
            "reheat_m": 74.34,             # kg/s
            "reheat_p": 39.37,             # bar
            "reheat_T": 511.62,            # °C
            
            # 凝汽器参数
            "condenser_p": 0.11,           # bar（实际为0.11055）
            "condensate_T": 47.78,         # °C
            
            # 泵参数
            "pump_eta": 0.85,
            "pump_pr": 187.83,
            
            # 汽轮机效率
            "hp_eta": 0.7475,
            "lp_eta": 0.7473,
            
            # 汽轮机压比（从参考数据）
            "hp1_pr": 0.4179,
            "hp2_pr": 0.6297,
            "lp1_pr": 0.6378,
            "lp2_pr": 0.5042,
            "lp3_pr": 0.5546,
            "lp4_pr": 0.4265,
            "lp5_pr": 0.4050,
            "lp6_pr": 0.8739,
            "lp7_pr": 0.1204,
            
            # 烟气参数（从参考数据）
            "flue_T": 1485.0,              # °C
            "flue_m": 135.24,              # kg/s (486.85 t/h)
            "flue_p": 1.05,                # bar
            "flue_comp": {
                "N2": 0.6220,
                "O2": 0.0205,
                "CO2": 0.3061,
                "H2O": 0.0513,
            },
            
            # 换热器kA值（从参考数据，单位：kW/K）
            "eco_lower_kA": 133000,
            "eco_upper_kA": 190000,
            "evap_kA": 105592,
            "sh_low_kA": 192000,
            "sh_screen_kA": 8500,
            "sh_tertiary_kA": 89100,
            "sh_final_kA": 51700,
            "rh_low_kA": 324000,
            "rh_high_kA": 48100,
            
            # 换热器压降（从参考数据）
            "eco_pr1": 0.9974,
            "eco_pr2": 0.9810,
            "evap_pr1": 0.9700,
            "sh_pr1_low": 0.9975,
            "sh_pr1_screen": 0.9839,
            "sh_pr1_tertiary": 0.9975,
            "sh_pr1_final": 0.9973,
            "sh_pr2_low": 0.9799,
            "sh_pr2_screen": 0.9800,
            "sh_pr2_tertiary": 0.9797,
            "sh_pr2_final": 0.9833,
            "rh_pr1": 0.9975,
            "rh_pr2": 0.9977,
            
            # 关键温度点（从参考数据）
            "pump_outlet_T": 276.0,        # °C
            "eco_lower_out_T": 285.7,      # °C
            "eco_upper_out_T": 311.6,      # °C
            "evap_out_x": 1.0,             # 饱和蒸汽
            "sh_low_out_T": 394.2,         # °C
            "sh_screen_out_T": 404.6,      # °C
            "sh_tertiary_out_T": 476.2,    # °C
            "rh_low_out_T": 418.5,         # °C
        }
        
        self.nw: Network | None = None
        self.results: dict = {}

    def build_network(self) -> Network:
        """构建网络."""
        print("\n" + "=" * 80)
        print("阶段2详细建模 - 基于真实工况的完整锅炉-汽轮机系统")
        print("=" * 80)
        print("模型结构：")
        print("  锅炉侧：下省 → 上省 → 蒸发器 → 低过 → 屏过 → 三过 → 末过")
        print("  再热侧：低再 → 高再")
        print("  汽轮机：高压缸(2段) → 低压缸(7段)")
        print("=" * 80 + "\n")

        nw = Network(iterinfo=False)
        nw.units.set_defaults(
            temperature="degC",
            pressure="bar",
            enthalpy="kJ/kg",
            power="MW",
            heat="MW",
        )

        # ==================== 组件定义 ====================
        cc = CycleCloser("循环闭合器")
        
        # 锅炉系统
        eco_lower = HeatExchanger("下级省煤器")
        eco_upper = HeatExchanger("上级省煤器")
        evaporator = HeatExchanger("蒸发器上升管")
        sh_low = HeatExchanger("低温过热器")
        sh_screen = HeatExchanger("屏式过热器")
        sh_tertiary = HeatExchanger("三级过热器")
        sh_final = HeatExchanger("末级过热器")
        
        # 再热系统
        rh_low = HeatExchanger("低温再热器")
        rh_high = HeatExchanger("末级再热器")
        
        # 汽轮机系统
        hp1 = Turbine("高压缸一段")
        hp2 = Turbine("高压缸二段")
        lp1 = Turbine("低压缸一段")
        lp2 = Turbine("低压缸二段")
        lp3 = Turbine("低压缸三段")
        lp4 = Turbine("低压缸四段")
        lp5 = Turbine("低压缸五段")
        lp6 = Turbine("低压缸六段")
        lp7 = Turbine("低压缸七段", design=['pr'], offdesign=['eta_s_char'])
        
        # 泵
        pump = Pump("给水泵")
        
        # 烟气源和冷凝水汇
        flue_source = Source("烟气源")
        flue_sink = Sink("烟气出口汇")
        cond_cc = CycleCloser("凝结水回路")
        
        print("[1] 组件定义完成（21个组件）")

        # ==================== 连接定义 ====================
        
        # 水/蒸汽主循环
        c_pump_out = Connection(pump, "out1", eco_lower, "in2", label="泵出口")
        c_eco_lower_out = Connection(eco_lower, "out2", eco_upper, "in2", label="下省出口")
        c_eco_upper_out = Connection(eco_upper, "out2", evaporator, "in2", label="上省出口")
        c_evap_out = Connection(evaporator, "out2", sh_low, "in2", label="蒸发器出口")
        c_sh_low_out = Connection(sh_low, "out2", sh_screen, "in2", label="低过出口")
        c_sh_screen_out = Connection(sh_screen, "out2", sh_tertiary, "in2", label="屏过出口")
        c_sh_tertiary_out = Connection(sh_tertiary, "out2", sh_final, "in2", label="三过出口")
        c_sh_final_out = Connection(sh_final, "out2", cc, "in1", label="末过出口")
        c_main_steam = Connection(cc, "out1", hp1, "in1", label="主蒸汽")
        
        # 汽轮机串联
        c_hp1_out = Connection(hp1, "out1", hp2, "in1", label="高压缸一段出口")
        c_hp2_out = Connection(hp2, "out1", rh_low, "in2", label="高压缸排汽")
        c_rh_low_out = Connection(rh_low, "out2", rh_high, "in2", label="低再出口")
        c_rh_high_out = Connection(rh_high, "out2", lp1, "in1", label="再热蒸汽")
        c_lp1_out = Connection(lp1, "out1", lp2, "in1", label="低压缸一段出口")
        c_lp2_out = Connection(lp2, "out1", lp3, "in1", label="低压缸二段出口")
        c_lp3_out = Connection(lp3, "out1", lp4, "in1", label="低压缸三段出口")
        c_lp4_out = Connection(lp4, "out1", lp5, "in1", label="低压缸四段出口")
        c_lp5_out = Connection(lp5, "out1", lp6, "in1", label="低压缸五段出口")
        c_lp6_out = Connection(lp6, "out1", lp7, "in1", label="低压缸六段出口")
        c_lp7_out = Connection(lp7, "out1", cond_cc, "in1", label="低压缸排汽")
        c_condensate = Connection(cond_cc, "out1", pump, "in1", label="凝结水")
        
        nw.add_conns(
            c_pump_out, c_eco_lower_out, c_eco_upper_out, c_evap_out,
            c_sh_low_out, c_sh_screen_out, c_sh_tertiary_out, c_sh_final_out,
            c_main_steam, c_hp1_out, c_hp2_out,
            c_rh_low_out, c_rh_high_out,
            c_lp1_out, c_lp2_out, c_lp3_out, c_lp4_out,
            c_lp5_out, c_lp6_out, c_lp7_out, c_condensate
        )
        
        # 烟气侧连接（逆流）
        fg1 = Connection(flue_source, "out1", sh_final, "in1", label="烟气→末过")
        fg2 = Connection(sh_final, "out1", sh_tertiary, "in1", label="末过→三过")
        fg3 = Connection(sh_tertiary, "out1", sh_screen, "in1", label="三过→屏过")
        fg4 = Connection(sh_screen, "out1", sh_low, "in1", label="屏过→低过")
        fg5 = Connection(sh_low, "out1", rh_high, "in1", label="低过→高再")
        fg6 = Connection(rh_high, "out1", rh_low, "in1", label="高再→低再")
        fg7 = Connection(rh_low, "out1", evaporator, "in1", label="低再→蒸发器")
        fg8 = Connection(evaporator, "out1", eco_upper, "in1", label="蒸发器→上省")
        fg9 = Connection(eco_upper, "out1", eco_lower, "in1", label="上省→下省")
        fg10 = Connection(eco_lower, "out1", flue_sink, "in1", label="烟气出口")
        
        nw.add_conns(fg1, fg2, fg3, fg4, fg5, fg6, fg7, fg8, fg9, fg10)
        
        print(f"[2] 连接建立完成（共 {len(nw.conns)} 个连接）")

        # ==================== 组件参数设置 ====================
        
        # 换热器参数
        eco_lower.set_attr(
            pr1=self.params["eco_pr1"],
            kA=self.params["eco_lower_kA"]
        )
        eco_upper.set_attr(
            pr1=self.params["eco_pr1"],
            kA=self.params["eco_upper_kA"]
        )
        evaporator.set_attr(
            pr1=self.params["evap_pr1"],
            kA=self.params["evap_kA"]
        )
        sh_low.set_attr(
            pr1=self.params["sh_pr1_low"],
            kA=self.params["sh_low_kA"]
        )
        sh_screen.set_attr(
            pr1=self.params["sh_pr1_screen"],
            kA=self.params["sh_screen_kA"]
        )
        sh_tertiary.set_attr(
            pr1=self.params["sh_pr1_tertiary"],
            kA=self.params["sh_tertiary_kA"]
        )
        sh_final.set_attr(
            pr1=self.params["sh_pr1_final"],
            kA=self.params["sh_final_kA"]
        )
        rh_low.set_attr(
            pr1=self.params["rh_pr1"],
            kA=self.params["rh_low_kA"]
        )
        rh_high.set_attr(
            pr1=self.params["rh_pr1"],
            kA=self.params["rh_high_kA"]
        )
        
        # 汽轮机参数
        hp1.set_attr(eta_s=self.params["hp_eta"], pr=self.params["hp1_pr"])
        hp2.set_attr(eta_s=self.params["hp_eta"], pr=self.params["hp2_pr"])
        lp1.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp1_pr"])
        lp2.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp2_pr"])
        lp3.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp3_pr"])
        lp4.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp4_pr"])
        lp5.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp5_pr"])
        lp6.set_attr(eta_s=self.params["lp_eta"], pr=self.params["lp6_pr"])
        lp7.set_attr(eta_s=self.params["lp_eta"])
        
        # 泵参数
        pump.set_attr(eta_s=self.params["pump_eta"])
        
        print("[3] 组件参数设置完成")

        # ==================== 边界条件设置 ====================
        
        # 工质定义
        c_pump_out.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid=self.params["flue_comp"])
        
        # 烟气入口条件
        fg1.set_attr(
            T=self.params["flue_T"],
            p=self.params["flue_p"],
            m=self.params["flue_m"]
        )
        
        # 主蒸汽参数
        c_main_steam.set_attr(
            p=self.params["steam_p"],
            T=self.params["steam_T"],
            m=self.params["steam_m"],
            fluid={"water": 1}
        )
        
        # 关键状态约束
        c_eco_upper_out.set_attr(T=self.params["eco_upper_out_T"])
        c_evap_out.set_attr(x=self.params["evap_out_x"])
        c_rh_high_out.set_attr(T=self.params["reheat_T"], p=self.params["reheat_p"])
        c_condensate.set_attr(p=self.params["condenser_p"], x=0)
        c_pump_out.set_attr(p=self.params["pump_pr"], T=self.params["pump_outlet_T"])
        # 只设置低再出口压力，不设置温度（由kA和能量平衡决定）
        c_rh_low_out.set_attr(p=self.params["reheat_p"])
        c_sh_tertiary_out.set_attr(T=self.params["sh_tertiary_out_T"])

        
        print("[4] 边界条件设置完成")
        print(f"   主蒸汽: {self.params['steam_p']} bar / {self.params['steam_T']}°C / {self.params['steam_m']} kg/s")
        print(f"   再热蒸汽: {self.params['reheat_p']} bar / {self.params['reheat_T']}°C / {self.params['reheat_m']} kg/s")
        print(f"   烟气: {self.params['flue_T']}°C / {self.params['flue_m']} kg/s")
        print("=" * 80)

        self.nw = nw
        return nw

    def solve(self) -> bool:
        """求解网络."""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None
        
        print("\n开始求解...")
        try:
            self.nw.solve(mode="design")
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 求解失败: {exc}")
            import traceback
            traceback.print_exc()
            return False
            
        if not self.nw.converged:
            print("✗ 未收敛")
            return False
            
        print("✓ 求解成功\n")
        return True

    def analyze(self) -> dict:
        """分析结果."""
        if not self.nw or not self.nw.converged:
            print("✗ 网络未收敛")
            return {}

        print("=" * 80)
        print("系统性能分析")
        print("=" * 80)
        
        # 计算各级汽轮机功率
        turb_names = [
            "高压缸一段", "高压缸二段",
            "低压缸一段", "低压缸二段", "低压缸三段",
            "低压缸四段", "低压缸五段", "低压缸六段", "低压缸七段"
        ]
        
        P_turb_total = 0.0
        print("\n【汽轮机功率分布】")
        for name in turb_names:
            turb = self.nw.get_comp(name)
            P = abs(turb.P.val)
            P_turb_total += P
            print(f"  {name:<12}: {P:10.3f} MW")
        
        # 泵功
        pump = self.nw.get_comp("给水泵")
        P_pump = abs(pump.P.val)
        P_net = P_turb_total - P_pump
        
        print(f"\n  汽轮机总功:  {P_turb_total:10.3f} MW")
        print(f"  泵功:        {P_pump:10.3f} MW")
        print(f"  净功率:      {P_net:10.3f} MW ⭐")
        
        # 换热器热量
        hx_names = [
            "下级省煤器", "上级省煤器", "蒸发器上升管",
            "低温过热器", "屏式过热器", "三级过热器", "末级过热器",
            "低温再热器", "末级再热器"
        ]
        
        Q_total = 0.0
        print("\n【锅炉吸热分布】")
        for name in hx_names:
            hx = self.nw.get_comp(name)
            Q = abs(hx.Q.val)
            Q_total += Q
            print(f"  {name:<12}: {Q:10.3f} MW")
        
        print(f"\n  锅炉总吸热:  {Q_total:10.3f} MW")
        
        # 效率
        if Q_total > 0:
            eta = P_net / Q_total * 100
            print(f"\n【系统效率】")
            print(f"  循环热效率:  {eta:10.2f} %")
        
        # 关键状态点
        main_steam = self.nw.get_conn("主蒸汽")
        reheat = self.nw.get_conn("再热蒸汽")
        flue_in_conn = self.nw.get_conn("烟气入口")
        flue_out_conn = self.nw.get_conn("烟气出口")
        
        print(f"\n【关键状态点】")
        print(f"  主蒸汽:      {main_steam.p.val:7.2f} bar / {main_steam.T.val:7.2f}°C / {main_steam.m.val:7.2f} kg/s")
        print(f"  再热蒸汽:    {reheat.p.val:7.2f} bar / {reheat.T.val:7.2f}°C / {reheat.m.val:7.2f} kg/s")
        print(f"  烟气入口:    {flue_in_conn.T.val:7.2f}°C")
        print(f"  烟气出口:    {flue_out_conn.T.val:7.2f}°C")
        print(f"  烟气温降:    {flue_in_conn.T.val - flue_out_conn.T.val:7.2f} K")
        
        print("=" * 80)
        
        self.results = {
            "P_net_MW": P_net,
            "P_turbine_total_MW": P_turb_total,
            "P_pump_MW": P_pump,
            "Q_boiler_total_MW": Q_total,
            "eta_thermal_percent": eta if Q_total > 0 else 0.0,
        }
        
        return self.results

    def export(self, path: Path = Path("stage2_detailed_results.json")) -> None:
        """导出结果."""
        if not self.results:
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 结果已保存到：{path}\n")


def main() -> None:
    """主程序."""
    logging.getLogger("tespy").setLevel(logging.WARNING)

    model = DetailedBoilerTurbineModel()
    model.build_network()

    if model.solve():
        model.analyze()
        model.export()
        print("=" * 80)
        print("✓ 阶段2详细建模完成！")
        print("=" * 80)
    else:
        print("=" * 80)
        print("✗ 求解失败，请检查参数设置")
        print("=" * 80)


if __name__ == "__main__":
    main()
