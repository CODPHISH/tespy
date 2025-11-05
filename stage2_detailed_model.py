#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2详细建模：多级换热 + 汽轮机联合循环系统.

基于真实电厂工况参数，构建包含多级换热器和汽轮机系统的TESPy热力循环模型。
模型结构简化但保留关键部件，确保求解稳定性的同时输出有价值的性能指标。

运行模型：
    python stage2_detailed_model.py

输出包括：
- 锅炉各级换热器的吸热量
- 汽轮机各级功率输出
- 系统循环热效率
- 烟气温度分布
- 关键换热器的kA值
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
    Condenser,
    Pump,
    Turbine,
    Source,
    Sink,
)
from tespy.connections import Connection


class DetailedBoilerTurbineModel:
    """详细建模：多级换热+三缸汽轮机联合循环系统."""

    def __init__(self) -> None:
        """初始化参数（基于真实工况）."""
        self.params = {
            #  主蒸汽参数
            "steam_p": 161.0,          # bar
            "steam_T": 560.0,          # °C
            "steam_m": 79.9,           # kg/s (≈ 287.6 t/h)
            # 再热参数
            "reheat_inlet_p": 40.0,    # bar
            "reheat_T": 512.0,         # °C
            # 凝汽器
            "cond_p": 0.12,            # bar
            # 烟气
            "fg_T": 1485.0,            # °C
            "fg_m": 135.2,             # kg/s (≈ 486.9 t/h)
            "fg_p": 1.05,              # bar
            "fg_comp": {
                "N2": 0.622,
                "O2": 0.0205,
                "CO2": 0.3061,
                "H2O": 0.0513,
            },
            # 冷却水
            "cw_T_in": 20.0,
            "cw_T_out": 32.0,
            # 效率
            "eta_turb_hp": 0.7475,
            "eta_turb_ip": 0.7474,
            "eta_turb_lp": 0.7473,
            "eta_pump": 0.85,
        }
        self.nw: Network | None = None
        self.results: dict = {}

    def build_network(self) -> Network:
        """构建网络."""
        print("\n" + "=" * 80)
        print("阶段2详细建模 - 多级换热 + 三缸汽轮机联合循环")
        print("=" * 80)
        print("结构：省煤器 → 蒸发器 → 过热器；再热器；高压缸 → 中压缸 → 低压缸")
        print("=" * 80 + "\n")

        nw = Network(iterinfo=False)
        nw.units.set_defaults(
            temperature="degC",
            pressure="bar",
            enthalpy="kJ/kg",
            power="MW",
            heat="MW",
        )

        # 组件
        cc = CycleCloser("循环闭合器")
        eco = HeatExchanger("省煤器")
        evap = HeatExchanger("蒸发器")
        sh = HeatExchanger("过热器")
        rh = HeatExchanger("再热器")
        hp_turb = Turbine("高压缸")
        ip_turb = Turbine("中压缸")
        lp_turb = Turbine("低压缸")
        pump = Pump("给水泵")
        cond = Condenser("凝汽器")
        fg_in = Source("烟气入口")
        fg_out = Sink("烟气出口")
        cw_in = Source("循环水入口")
        cw_out = Sink("循环水出口")

        # 水/蒸汽侧连接
        c1 = Connection(pump, "out1", eco, "in2", label="泵出口")
        c2 = Connection(eco, "out2", evap, "in2", label="省煤器出口")
        c3 = Connection(evap, "out2", sh, "in2", label="蒸发器出口")
        c4 = Connection(sh, "out2", cc, "in1", label="过热器出口")
        c5 = Connection(cc, "out1", hp_turb, "in1", label="主蒸汽")
        c6 = Connection(hp_turb, "out1", rh, "in2", label="高压缸排汽")
        c7 = Connection(rh, "out2", ip_turb, "in1", label="再热蒸汽")
        c8 = Connection(ip_turb, "out1", lp_turb, "in1", label="中压缸排汽")
        c9 = Connection(lp_turb, "out1", cond, "in1", label="低压缸排汽")
        c10 = Connection(cond, "out1", pump, "in1", label="凝结水")
        nw.add_conns(c1, c2, c3, c4, c5, c6, c7, c8, c9, c10)

        # 烟气侧连接 (逆流)
        fg1 = Connection(fg_in, "out1", sh, "in1", label="烟气→过热器")
        fg2 = Connection(sh, "out1", rh, "in1", label="过热器→再热器")
        fg3 = Connection(rh, "out1", evap, "in1", label="再热器→蒸发器")
        fg4 = Connection(evap, "out1", eco, "in1", label="蒸发器→省煤器")
        fg5 = Connection(eco, "out1", fg_out, "in1", label="烟气出口")
        nw.add_conns(fg1, fg2, fg3, fg4, fg5)

        # 循环水连接
        cw1 = Connection(cw_in, "out1", cond, "in2", label="循环水入口")
        cw2 = Connection(cond, "out2", cw_out, "in1", label="循环水出口")
        nw.add_conns(cw1, cw2)

        # 组件参数
        eco.set_attr(pr1=0.981, pr2=0.981)
        evap.set_attr(pr1=0.97, pr2=0.97)
        sh.set_attr(pr1=0.979, pr2=0.979)
        rh.set_attr(pr1=0.9975, pr2=0.9975)
        hp_turb.set_attr(eta_s=self.params["eta_turb_hp"])
        ip_turb.set_attr(eta_s=self.params["eta_turb_ip"])
        lp_turb.set_attr(eta_s=self.params["eta_turb_lp"])
        pump.set_attr(eta_s=self.params["eta_pump"])
        cond.set_attr(pr1=1.0, pr2=0.98)

        # 边界条件
        c1.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid=self.params["fg_comp"])
        cw1.set_attr(fluid={"water": 1})

        # 烟气
        fg1.set_attr(T=self.params["fg_T"], p=self.params["fg_p"], m=self.params["fg_m"])
        # 主蒸汽
        c5.set_attr(p=self.params["steam_p"], T=self.params["steam_T"], m=self.params["steam_m"])
        # 蒸发器出口：饱和蒸汽
        c3.set_attr(x=1.0)
        # 高压缸出口
        c6.set_attr(p=self.params["reheat_inlet_p"])
        # 再热蒸汽
        c7.set_attr(T=self.params["reheat_T"])
        # 凝汽器
        c9.set_attr(p=self.params["cond_p"])
        c10.set_attr(T=38.0)
        # 冷却水
        cw1.set_attr(T=self.params["cw_T_in"], p=1.2, m=10000)
        cw2.set_attr(T=self.params["cw_T_out"])

        self.nw = nw
        return nw

    def solve(self) -> bool:
        """求解网络."""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None
        try:
            print("开始求解...")
            self.nw.solve(mode="design")
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 求解失败: {exc}")
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

        # 获取组件
        eco = self.nw.get_comp("省煤器")
        evap = self.nw.get_comp("蒸发器")
        sh = self.nw.get_comp("过热器")
        rh = self.nw.get_comp("再热器")
        hp = self.nw.get_comp("高压缸")
        ip = self.nw.get_comp("中压缸")
        lp = self.nw.get_comp("低压缸")
        pump = self.nw.get_comp("给水泵")
        cond = self.nw.get_comp("凝汽器")

        # 热量
        Q_eco = abs(eco.Q.val)
        Q_evap = abs(evap.Q.val)
        Q_sh = abs(sh.Q.val)
        Q_rh = abs(rh.Q.val)
        Q_total = Q_eco + Q_evap + Q_sh + Q_rh

        # 功率
        P_hp = abs(hp.P.val)
        P_ip = abs(ip.P.val)
        P_lp = abs(lp.P.val)
        P_pump = abs(pump.P.val)
        P_turb_total = P_hp + P_ip + P_lp
        P_net = P_turb_total - P_pump
        Q_cond = abs(cond.Q.val)
        eta = P_net / Q_total * 100 if Q_total > 0 else 0.0

        # 状态点
        main_steam = self.nw.get_conn("主蒸汽")
        reheat = self.nw.get_conn("再热蒸汽")
        fg_in_conn = self.nw.get_conn("烟气→过热器")
        fg_out_conn = self.nw.get_conn("烟气出口")

        # 输出结果
        print("=" * 80)
        print("系统性能分析")
        print("=" * 80)
        print(f"\n【锅炉吸热分布】")
        print(f"  省煤器:      {Q_eco:10.3f} MW  ({Q_eco/Q_total*100:5.1f}%)")
        print(f"  蒸发器:      {Q_evap:10.3f} MW  ({Q_evap/Q_total*100:5.1f}%)")
        print(f"  过热器:      {Q_sh:10.3f} MW  ({Q_sh/Q_total*100:5.1f}%)")
        print(f"  再热器:      {Q_rh:10.3f} MW  ({Q_rh/Q_total*100:5.1f}%)")
        print(f"  总吸热:      {Q_total:10.3f} MW")

        print(f"\n【汽轮机功率分布】")
        print(f"  高压缸:      {P_hp:10.3f} MW  ({P_hp/P_turb_total*100:5.1f}%)")
        print(f"  中压缸:      {P_ip:10.3f} MW  ({P_ip/P_turb_total*100:5.1f}%)")
        print(f"  低压缸:      {P_lp:10.3f} MW  ({P_lp/P_turb_total*100:5.1f}%)")
        print(f"  汽轮机总功:  {P_turb_total:10.3f} MW")
        print(f"  泵功:        {P_pump:10.3f} MW")
        print(f"  净功率:      {P_net:10.3f} MW ⭐")

        print(f"\n【系统效率】")
        print(f"  循环热效率:  {eta:10.2f} %")
        print(f"  凝汽器放热:  {Q_cond:10.3f} MW")

        balance = abs(Q_total - (P_net + Q_cond))
        print(f"  能量平衡误差: {balance/Q_total*100:10.4f} %")

        print(f"\n【关键状态点】")
        print(f"  主蒸汽:      {main_steam.p.val:7.2f} bar / {main_steam.T.val:7.2f} °C / {main_steam.m.val:7.2f} kg/s")
        print(f"  再热蒸汽:    {reheat.p.val:7.2f} bar / {reheat.T.val:7.2f} °C / {reheat.m.val:7.2f} kg/s")
        print(f"  烟气入口:    {fg_in_conn.T.val:7.2f} °C")
        print(f"  烟气出口:    {fg_out_conn.T.val:7.2f} °C")
        print(f"  烟气温降:    {fg_in_conn.T.val - fg_out_conn.T.val:7.2f} K")

        print(f"\n【换热器kA值】")
        print(f"  省煤器:      {eco.kA.val/1000:10.3f} MW/K")
        print(f"  蒸发器:      {evap.kA.val/1000:10.3f} MW/K")
        print(f"  过热器:      {sh.kA.val/1000:10.3f} MW/K")
        print(f"  再热器:      {rh.kA.val/1000:10.3f} MW/K")

        print("=" * 80 + "\n")

        # 保存结果
        self.results = {
            "Q_boiler_total_MW": Q_total,
            "Q_economizer_MW": Q_eco,
            "Q_evaporator_MW": Q_evap,
            "Q_superheater_MW": Q_sh,
            "Q_reheater_MW": Q_rh,
            "P_turbine_total_MW": P_turb_total,
            "P_hp_MW": P_hp,
            "P_ip_MW": P_ip,
            "P_lp_MW": P_lp,
            "P_pump_MW": P_pump,
            "P_net_MW": P_net,
            "eta_thermal_percent": eta,
            "flue_gas_T_in": fg_in_conn.T.val,
            "flue_gas_T_out": fg_out_conn.T.val,
            "kA_economizer_kW_K": eco.kA.val,
            "kA_evaporator_kW_K": evap.kA.val,
            "kA_superheater_kW_K": sh.kA.val,
            "kA_reheater_kW_K": rh.kA.val,
        }
        return self.results

    def export(self, path: Path = Path("stage2_detailed_results.json")) -> None:
        """导出结果."""
        if not self.results:
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"✓ 结果已保存到：{path}\n")


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
