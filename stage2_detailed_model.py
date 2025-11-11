#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整复刻connections.csv的详细建模
基于静态数据结构重建完整模型结构（已移除CSV读取逻辑）
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

# 导入静态数据
from stage2_static_inputs import CONNECTIONS_DATA, COMPONENT_DATA

from tespy.networks import Network
from tespy.components import (
    CycleCloser,
    HeatExchanger,
    Turbine,
    Pump,
    Source,
    Sink,
    Splitter,
    Merge,
    Valve,
    Drum,
    DiabaticCombustionChamber,
    Pipe,
)
from tespy.connections import Connection, Ref


class CompleteBoilerTurbineModel:
    """完整的锅炉-汽轮机系统模型（完全复刻connections.csv）"""

    def __init__(self) -> None:
        """初始化"""
        self.nw: Network | None = None
        self.components: dict = {}
        self.connections: dict = {}
        self.results: dict = {}
        self.convergence_info: dict = {}
        self.component_data = COMPONENT_DATA
        self.connection_data = CONNECTIONS_DATA

        print(f"✓ 已加载 {len(self.connection_data)} 条连接静态数据")
        print(f"✓ 已加载 {sum(len(v) for v in self.component_data.values())} 个组件参数条目")

    def build_network(self) -> Network:
        """构建完整网络"""
        print("\n" + "=" * 80)
        print("完整建模 - 基于静态数据的完整复刻")
        print("=" * 80)

        nw = Network(
            iterinfo=True,
            fluids=[
                "water",
                "N2",
                "O2",
                "CO2",
                "CO",
                "H2",
                "CH4",
            ],
        )
        nw.units.set_defaults(
            temperature="C",
            pressure="bar",
            enthalpy="kJ/kg",
            power="W",
            heat="W",
            mass_flow="t/h",
        )

        # ==================== 组件定义 ====================
        print("\n[1] 定义组件...")
        
        # 汽轮机 (9个)
        turb_hp1 = Turbine("抽凝式汽轮机1_高压缸一段")
        turb_hp2 = Turbine("抽凝式汽轮机1_高压缸二段")
        turb_lp1 = Turbine("抽凝式汽轮机1_低压缸一段")
        turb_lp2 = Turbine("抽凝式汽轮机1_低压缸二段")
        turb_lp3 = Turbine("抽凝式汽轮机1_低压缸三段")
        turb_lp4 = Turbine("抽凝式汽轮机1_低压缸四段")
        turb_lp5 = Turbine("抽凝式汽轮机1_低压缸五段")
        turb_lp6 = Turbine("抽凝式汽轮机1_低压缸六段")
        turb_lp7 = Turbine("抽凝式汽轮机1_低压缸七段")
        
        # 阀门 (5个)
        valve_hp_in = Valve("抽凝式汽轮机1_高压缸进气阀")
        valve_hp_out = Valve("抽凝式汽轮机1_高压缸排气阀")
        valve_mp_in = Valve("抽凝式汽轮机1_中压缸进气阀")
        valve_mp_out = Valve("抽凝式汽轮机1_中压缸排气阀")
        valve_water_in = Valve("1#发电锅炉_进水阀")
        
        # 分离器 (汽轮机抽汽，8个)
        split_hp1 = Splitter("抽凝式汽轮机1_高压缸一段抽汽分离")
        split_hp_exhaust = Splitter("抽凝式汽轮机1_高压缸排汽分离")
        split_lp1 = Splitter("抽凝式汽轮机1_再热蒸汽1段抽汽分离")
        split_lp2 = Splitter("抽凝式汽轮机1_再热蒸汽2段抽汽分离")
        split_lp3 = Splitter("抽凝式汽轮机1_再热蒸汽3段抽汽分离")
        split_lp4 = Splitter("抽凝式汽轮机1_再热蒸汽4段抽汽分离")
        split_lp5 = Splitter("抽凝式汽轮机1_再热蒸汽5段抽汽分离")
        split_lp6 = Splitter("抽凝式汽轮机1_再热蒸汽6段抽汽分离")
        
        # 混合器 (2个)
        merge_fuel_1 = Merge("1#发电锅炉_燃料气混合器1")  # 高炉煤气 + 转炉煤气
        merge_fuel_2 = Merge("1#发电锅炉_燃料气混合器2")  # 混合气 + 焦炉煤气
        
        # 换热器 (11个)
        hx_air_preheat = HeatExchanger("1#发电锅炉_空气预热器")
        hx_fuel_preheat = HeatExchanger("1#发电锅炉_煤气预热器")
        hx_evap = HeatExchanger("1#发电锅炉_蒸发器上升管")
        hx_sh_screen = HeatExchanger("1#发电锅炉_屏式过热器")
        hx_sh_final = HeatExchanger("1#发电锅炉_末级过热器")
        hx_rh_final = HeatExchanger("1#发电锅炉_末级再热器")
        hx_sh_tertiary = HeatExchanger("1#发电锅炉_三级过热器")
        hx_sh_low = HeatExchanger("1#发电锅炉_低温过热器")
        hx_rh_low = HeatExchanger("1#发电锅炉_低温再热器")
        hx_eco_upper = HeatExchanger("1#发电锅炉_上级省煤器")
        hx_eco_lower = HeatExchanger("1#发电锅炉_下级省煤器")
        
        # 泵 (1个)
        pump = Pump("1#发电锅炉_给水泵")
        
        # 汽包 (1个)
        drum = Drum("1#发电锅炉_汽包")
        
        # 燃烧室 (1个)
        combustor = DiabaticCombustionChamber("1#发电锅炉_炉膛燃烧室")
        
        # 管道 (1个)
        pipe_scr = Pipe("1#发电锅炉_脱硫脱硝")
        
        # 源 (4个)
        src_air = Source("1#发电锅炉_空气源")
        src_bfg = Source("boiler1_高炉煤气源")
        src_cog = Source("1#发电锅炉_转炉煤气源")
        src_coke = Source("1#发电锅炉_焦炉煤气源")
        
        # 汇 (9个：烟气出口 + 各抽汽出口)
        sink_flue = Sink("1#发电锅炉_烟气出口汇")
        sink_hp1_ext = Sink("抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口汇")
        sink_hp_exhaust_ext = Sink("抽凝式汽轮机1_高压缸排汽抽汽汇")
        sink_lp1_ext = Sink("抽凝式汽轮机1_再热蒸汽1段抽汽出口汇")
        sink_lp2_ext = Sink("抽凝式汽轮机1_再热蒸汽2段抽汽出口汇")
        sink_lp3_ext = Sink("抽凝式汽轮机1_再热蒸汽3段抽汽出口汇")
        sink_lp4_ext = Sink("抽凝式汽轮机1_再热蒸汽4段抽汽出口汇")
        sink_lp5_ext = Sink("抽凝式汽轮机1_再热蒸汽5段抽汽出口汇")
        sink_lp6_ext = Sink("抽凝式汽轮机1_再热蒸汽6段抽汽出口汇")
        
        # CycleCloser  
        cc_condenser = CycleCloser("凝汽器回路")
        
        total_comps = 60
        print(f"   已定义 {total_comps} 个组件")
        
        # ==================== 连接定义 ====================
        print("\n[2] 定义连接...")
        
        # 【水/蒸汽侧主循环】
        c_pump_in = Connection(cc_condenser, "out1", pump, "in1", label="1#发电锅炉_水泵入口")
        c_pump_out = Connection(pump, "out1", valve_water_in, "in1", label="1#发电锅炉_水泵出口")
        c_valve_out = Connection(valve_water_in, "out1", hx_eco_lower, "in2", label="1#发电锅炉_水侧下省入口")
        c_eco_lower_out = Connection(hx_eco_lower, "out2", hx_eco_upper, "in2", label="1#发电锅炉_水侧上省入口")
        c_eco_upper_out = Connection(hx_eco_upper, "out2", drum, "in1", label="1#发电锅炉_汽包给水入口")
        c_drum_downcomer = Connection(drum, "out1", hx_evap, "in2", label="1#发电锅炉_下降管入口")
        c_evap_out = Connection(hx_evap, "out2", drum, "in2", label="1#发电锅炉_上升管出口")
        c_drum_sat_steam = Connection(drum, "out2", hx_sh_low, "in2", label="1#发电锅炉_汽包饱和蒸汽出口")
        c_sh_low_out = Connection(hx_sh_low, "out2", hx_sh_screen, "in2", label="1#发电锅炉_蒸汽低过出口")
        c_sh_screen_out = Connection(hx_sh_screen, "out2", hx_sh_tertiary, "in2", label="1#发电锅炉_蒸汽屏过出口")
        c_sh_tertiary_out = Connection(hx_sh_tertiary, "out2", hx_sh_final, "in2", label="1#发电锅炉_蒸汽三过出口")
        c_main_steam = Connection(hx_sh_final, "out2", valve_hp_in, "in1", label="1#发电锅炉_主蒸汽")
        
        # 【高压缸路径】
        c_valve_hp_in_out = Connection(valve_hp_in, "out1", turb_hp1, "in1", label="抽凝式汽轮机1_高压蒸汽去高压缸1段")
        c_hp1_out = Connection(turb_hp1, "out1", split_hp1, "in1", label="抽凝式汽轮机1_高压缸一段蒸汽抽汽分离")
        c_hp1_main = Connection(split_hp1, "out1", turb_hp2, "in1", label="抽凝式汽轮机1_高压蒸汽去高压缸2段")
        c_hp1_ext = Connection(split_hp1, "out2", sink_hp1_ext, "in1", label="抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口")
        c_hp2_out = Connection(turb_hp2, "out1", valve_hp_out, "in1", label="抽凝式汽轮机1_高压蒸汽去排气阀门")
        c_hp_exhaust_full = Connection(valve_hp_out, "out1", split_hp_exhaust, "in1", label="抽凝式汽轮机1_高压缸排汽")
        c_hp_exhaust_main = Connection(split_hp_exhaust, "out1", hx_rh_low, "in2", label="1#发电锅炉_再热蒸汽入口")
        c_hp_ext_tap = Connection(split_hp_exhaust, "out2", sink_hp_exhaust_ext, "in1", label="抽凝式汽轮机1_高压缸排汽抽汽")
        
        # 【再热路径】
        c_rh_low_out = Connection(hx_rh_low, "out2", hx_rh_final, "in2", label="1#发电锅炉_再热蒸汽低再出口")
        c_rh_final_out = Connection(hx_rh_final, "out2", valve_mp_in, "in1", label="1#发电锅炉_再热蒸汽高再出口")
        c_valve_mp_in_out = Connection(valve_mp_in, "out1", turb_lp1, "in1", label="抽凝式汽轮机1_蒸汽去中压缸1段")
        
        # 【低压缸路径 - 7段，每段后抽汽】
        c_lp1_out = Connection(turb_lp1, "out1", split_lp1, "in1", label="抽凝式汽轮机1_再热蒸汽去1段抽汽分离")
        c_lp1_main = Connection(split_lp1, "out1", turb_lp2, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸2段")
        c_lp1_ext = Connection(split_lp1, "out2", sink_lp1_ext, "in1", label="抽凝式汽轮机1_再热蒸汽1段抽汽出口")
        
        c_lp2_out = Connection(turb_lp2, "out1", split_lp2, "in1", label="抽凝式汽轮机1_再热蒸汽去2段抽汽分离")
        c_lp2_main = Connection(split_lp2, "out1", turb_lp3, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸3段")
        c_lp2_ext = Connection(split_lp2, "out2", sink_lp2_ext, "in1", label="抽凝式汽轮机1_再热蒸汽2段抽汽出口")
        
        c_lp3_out = Connection(turb_lp3, "out1", split_lp3, "in1", label="抽凝式汽轮机1_再热蒸汽去3段抽汽分离")
        c_lp3_main = Connection(split_lp3, "out1", turb_lp4, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸4段")
        c_lp3_ext = Connection(split_lp3, "out2", sink_lp3_ext, "in1", label="抽凝式汽轮机1_再热蒸汽3段抽汽出口")
        
        c_lp4_out = Connection(turb_lp4, "out1", split_lp4, "in1", label="抽凝式汽轮机1_再热蒸汽去4段抽汽分离")
        c_lp4_main = Connection(split_lp4, "out1", turb_lp5, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸5段")
        c_lp4_ext = Connection(split_lp4, "out2", sink_lp4_ext, "in1", label="抽凝式汽轮机1_再热蒸汽4段抽汽出口")
        
        c_lp5_out = Connection(turb_lp5, "out1", split_lp5, "in1", label="抽凝式汽轮机1_再热蒸汽去5段抽汽分离")
        c_lp5_main = Connection(split_lp5, "out1", turb_lp6, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸6段")
        c_lp5_ext = Connection(split_lp5, "out2", sink_lp5_ext, "in1", label="抽凝式汽轮机1_再热蒸汽5段抽汽出口")
        
        c_lp6_out = Connection(turb_lp6, "out1", split_lp6, "in1", label="抽凝式汽轮机1_再热蒸汽去6段抽汽分离")
        c_lp6_main = Connection(split_lp6, "out1", turb_lp7, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸7段")
        c_lp6_ext = Connection(split_lp6, "out2", sink_lp6_ext, "in1", label="抽凝式汽轮机1_再热蒸汽6段抽汽出口")
        
        c_lp7_out = Connection(turb_lp7, "out1", valve_mp_out, "in1", label="抽凝式汽轮机1_再热蒸汽去排气阀门")
        c_turbine_exhaust = Connection(valve_mp_out, "out1", cc_condenser, "in1", label="抽凝式汽轮机1_中压缸排气出口")
        
        # 【燃料气/空气侧】
        # 注：由于Merge需要2个inlet，但第二个空气入口在CSV中流量为0，我们简化为只用一个空气源
        # 直接连接到预热器，绕过Merge
        c_air_in = Connection(src_air, "out1", hx_air_preheat, "in2", label="1#发电锅炉_空气入口")
        c_air_preheated = Connection(hx_air_preheat, "out2", combustor, "in1", label="1#发电锅炉_空气锅炉入口")
        
        # 燃料气混合 (高炉煤气 + 转炉煤气 -> 预热器 -> + 焦炉煤气 -> 燃烧室)
        c_bfg_in = Connection(src_bfg, "out1", merge_fuel_1, "in1", label="boiler1_高炉煤气入口")
        c_cog_in = Connection(src_cog, "out1", merge_fuel_1, "in2", label="1#发电锅炉_转炉煤气入口")
        c_fuel_mixed_1 = Connection(merge_fuel_1, "out1", hx_fuel_preheat, "in2", label="1#发电锅炉_高转煤气混合后")
        c_fuel_preheated = Connection(hx_fuel_preheat, "out2", merge_fuel_2, "in1", label="1#发电锅炉_高转煤气预热后")
        c_coke_in = Connection(src_coke, "out1", merge_fuel_2, "in2", label="1#发电锅炉_焦炉煤气入口")
        c_fuel_final = Connection(merge_fuel_2, "out1", combustor, "in2", label="1#发电锅炉_混合燃料气锅炉入口")
        
        # 【烟气侧】
        c_flue_combustor = Connection(combustor, "out1", hx_sh_final, "in1", label="1#发电锅炉_燃烧烟气")
        c_flue_1 = Connection(hx_sh_final, "out1", hx_sh_tertiary, "in1", label="1#发电锅炉_末过烟气入口")
        c_flue_2 = Connection(hx_sh_tertiary, "out1", hx_sh_screen, "in1", label="1#发电锅炉_三过烟气入口")
        c_flue_3 = Connection(hx_sh_screen, "out1", hx_sh_low, "in1", label="1#发电锅炉_低过烟气入口")
        c_flue_4 = Connection(hx_sh_low, "out1", hx_rh_final, "in1", label="1#发电锅炉_再烟气入口")
        c_flue_5 = Connection(hx_rh_final, "out1", hx_rh_low, "in1", label="1#发电锅炉_低再烟气入口")
        c_flue_6 = Connection(hx_rh_low, "out1", hx_evap, "in1", label="1#发电锅炉_上升管烟气出口")
        c_flue_7 = Connection(hx_evap, "out1", hx_eco_upper, "in1", label="1#发电锅炉_上省烟气入口")
        c_flue_8 = Connection(hx_eco_upper, "out1", pipe_scr, "in1", label="1#发电锅炉_SCR烟气入口")
        c_flue_9 = Connection(pipe_scr, "out1", hx_eco_lower, "in1", label="1#发电锅炉_下省烟气入口")
        c_flue_10 = Connection(hx_eco_lower, "out1", hx_air_preheat, "in1", label="1#发电锅炉_空预烟气入口")
        c_flue_11 = Connection(hx_air_preheat, "out1", hx_fuel_preheat, "in1", label="1#发电锅炉_煤预烟气入口")
        c_flue_out = Connection(hx_fuel_preheat, "out1", sink_flue, "in1", label="1#发电锅炉_煤预烟气出口")
        
        # 添加连接到网络
        nw.add_conns(
            # 水/蒸汽侧
            c_pump_in, c_pump_out, c_valve_out, c_eco_lower_out, c_eco_upper_out,
            c_drum_downcomer, c_evap_out, c_drum_sat_steam,
            c_sh_low_out, c_sh_screen_out, c_sh_tertiary_out, c_main_steam,
            # 高压缸
            c_valve_hp_in_out, c_hp1_out, c_hp1_main, c_hp1_ext,
            c_hp2_out, c_hp_exhaust_full, c_hp_exhaust_main, c_hp_ext_tap,
            # 再热
            c_rh_low_out, c_rh_final_out, c_valve_mp_in_out,
            # 低压缸
            c_lp1_out, c_lp1_main, c_lp1_ext,
            c_lp2_out, c_lp2_main, c_lp2_ext,
            c_lp3_out, c_lp3_main, c_lp3_ext,
            c_lp4_out, c_lp4_main, c_lp4_ext,
            c_lp5_out, c_lp5_main, c_lp5_ext,
            c_lp6_out, c_lp6_main, c_lp6_ext,
            c_lp7_out, c_turbine_exhaust,
            # 燃料气/空气
            c_air_in, c_air_preheated,
            c_bfg_in, c_cog_in, c_fuel_mixed_1, c_fuel_preheated, c_coke_in, c_fuel_final,
            # 烟气
            c_flue_combustor, c_flue_1, c_flue_2, c_flue_3, c_flue_4, c_flue_5,
            c_flue_6, c_flue_7, c_flue_8, c_flue_9, c_flue_10, c_flue_11, c_flue_out,
        )
        
        print(f"   已定义 {len(nw.conns)} 个连接")
        
        # ==================== 组件参数设置 ====================
        print("\n[3] 设置组件参数...")
        self._set_component_parameters(nw)
        
        # ==================== 边界条件设置 ====================
        print("\n[4] 设置边界条件...")
        self._set_boundary_conditions(nw)
        
        print("=" * 80)
        self.nw = nw
        return nw

    def _set_component_parameters(self, nw: Network) -> None:
        """设置组件参数（从静态数据读取）
        
        策略：保留关键压降参数但避免重复约束
        - 汽轮机：设置效率和压力比（保持设计膨胀比）
        - 换热器：设置传热系数kA，并仅设置气侧压降（pr1），不设置水侧pr2
        - 泵：设置效率和压力比
        - 阀门、管道：设置压力比（保持原设计压降）
        - 燃烧室：设置空气系数与效率
        通过避免在水/蒸汽侧重复设置压降并减少绝对压力约束，降低循环依赖风险。
        """
        # 汽轮机参数
        if 'Turbine' in self.component_data:
            for name, params in self.component_data['Turbine'].items():
                try:
                    comp = nw.get_comp(name)
                    eta_s = params.get('eta_s')
                    pr = params.get('pr')
                    if eta_s is not None:
                        comp.set_attr(eta_s=eta_s)
                    if pr is not None:
                        comp.set_attr(pr=pr)
                except KeyError:
                    pass
        
        # 换热器参数 - 仅设置kA与气侧压降pr1
        if 'HeatExchanger' in self.component_data:
            for name, params in self.component_data['HeatExchanger'].items():
                try:
                    comp = nw.get_comp(name)
                    kA = params.get('kA')
                    pr1 = params.get('pr1')
                    if kA is not None:
                        comp.set_attr(kA=kA)
                    if pr1 is not None:
                        comp.set_attr(pr1=pr1)
                    # 不设置pr2，避免在水/蒸汽侧的循环压降重复约束
                except KeyError:
                    pass
        
        # 泵参数
        if 'Pump' in self.component_data:
            for name, params in self.component_data['Pump'].items():
                try:
                    comp = nw.get_comp(name)
                    eta_s = params.get('eta_s')
                    pr = params.get('pr')
                    if eta_s is not None:
                        comp.set_attr(eta_s=eta_s)
                    if pr is not None:
                        comp.set_attr(pr=pr)
                except KeyError:
                    pass
        
        # 阀门参数
        if 'Valve' in self.component_data:
            for name, params in self.component_data['Valve'].items():
                try:
                    comp = nw.get_comp(name)
                    pr = params.get('pr')
                    if pr is not None:
                        comp.set_attr(pr=pr)
                except KeyError:
                    pass
        
        # 管道参数
        if 'Pipe' in self.component_data:
            for name, params in self.component_data['Pipe'].items():
                try:
                    comp = nw.get_comp(name)
                    pr = params.get('pr')
                    if pr is not None:
                        comp.set_attr(pr=pr)
                except KeyError:
                    pass
        
        # 燃烧室参数
        if 'DiabaticCombustionChamber' in self.component_data:
            for name, params in self.component_data['DiabaticCombustionChamber'].items():
                try:
                    comp = nw.get_comp(name)
                    lamb = params.get('lamb')
                    eta = params.get('eta')
                    if lamb is not None:
                        comp.set_attr(lamb=lamb)
                    if eta is not None:
                        comp.set_attr(eta=eta)
                except KeyError:
                    pass

        print("   ✓ 组件参数设置完成（关键效率与压降参数已配置）")

    def _set_boundary_conditions(self, nw: Network) -> None:
        """设置边界条件（使用静态连接数据）
        
        策略：采用最小约束策略
        1. 设置关键设计点参数（固定）
        2. 设置入口边界条件（固定）
        3. 其他连接只设置初始值（不固定）
        """
        conn_data = self.connection_data

        # === 设置所有连接的初始值（不固定） ===
        for label, data in conn_data.items():
            try:
                conn = nw.get_conn(label)
                if conn is None:
                    continue
                # 只设置初始值，不固定
                if data['m'] is not None and data['m'] > 1e-6:  # 避免0流量
                    conn.set_attr(m0=data['m'])
                if data['p'] is not None and data['p'] > 0:
                    conn.set_attr(p0=data['p'])
                if data['T'] is not None:
                    conn.set_attr(T0=data['T'])
                if data['h'] is not None:
                    conn.set_attr(h0=data['h'])
            except KeyError:
                pass

        # === 仅设置关键固定边界条件 ===

        # 主蒸汽：固定流量、温度和压力
        try:
            conn = nw.get_conn("1#发电锅炉_主蒸汽")
            data = conn_data.get("1#发电锅炉_主蒸汽", {})
            conn.set_attr(m=data.get('m'), T=data.get('T'), p=data.get('p'))
        except KeyError:
            pass

        # 空气入口：固定流量、压力、温度、流体组分
        try:
            conn = nw.get_conn("1#发电锅炉_空气入口")
            data = conn_data.get("1#发电锅炉_空气入口", {})
            conn.set_attr(m=data.get('m'), p=data.get('p'), T=data.get('T'), fluid={'N2': 0.76, 'O2': 0.24})
        except KeyError:
            pass

        # 高炉煤气入口：固定流量、压力、温度、流体组分
        try:
            conn = nw.get_conn("boiler1_高炉煤气入口")
            data = conn_data.get("boiler1_高炉煤气入口", {})
            fluid_comp = {'N2': 0.4609, 'CO': 0.2078, 'CO2': 0.3293, 'H2': 0.002}
            # 只在一个燃气入口设置压力，其他的仅设置流量和温度
            conn.set_attr(m=data.get('m'), p=data.get('p'), T=data.get('T'), fluid=fluid_comp)
        except KeyError:
            pass

        # 转炉煤气：固定流量、温度、流体组分（不设置压力）
        try:
            conn = nw.get_conn("1#发电锅炉_转炉煤气入口")
            data = conn_data.get("1#发电锅炉_转炉煤气入口", {})
            fluid_comp = {'N2': 0.3389, 'CO': 0.4223, 'CO2': 0.2381, 'H2': 0.0007}
            conn.set_attr(m=data.get('m'), T=data.get('T'), fluid=fluid_comp)
        except KeyError:
            pass

        # 焦炉煤气：固定流量、温度、流体组分（不设置压力）
        try:
            conn = nw.get_conn("1#发电锅炉_焦炉煤气入口")
            data = conn_data.get("1#发电锅炉_焦炉煤气入口", {})
            fluid_comp = {'N2': 0.2018, 'CO': 0.2305, 'CO2': 0.0996, 'H2': 0.1311, 'CH4': 0.337}
            conn.set_attr(m=data.get('m'), T=data.get('T'), fluid=fluid_comp)
        except KeyError:
            pass

        # 泵入口（凝结水）：固定质量分数与流体，不固定压力
        # 泵入口压力通过CycleCloser与排气出口压力形成线性依赖，不能同时固定
        try:
            conn = nw.get_conn("1#发电锅炉_水泵入口")
            data = conn_data.get("1#发电锅炉_水泵入口", {})
            conn.set_attr(x=data.get('x'), fluid={'water': 1})
        except KeyError:
            pass

        # 汽包饱和蒸汽：固定干度
        try:
            conn = nw.get_conn("1#发电锅炉_汽包饱和蒸汽出口")
            conn.set_attr(x=1.0)
        except KeyError:
            pass

        # 高压缸排汽抽汽：固定流量（静态数据给出为20 t/h）
        try:
            conn = nw.get_conn("抽凝式汽轮机1_高压缸排汽抽汽")
            data = conn_data.get("抽凝式汽轮机1_高压缸排汽抽汽", {})
            if data.get('m') is not None and data['m'] > 0:
                conn.set_attr(m=data['m'])
        except KeyError:
            pass

        # 所有低压缸抽汽出口设置为0流量（静态数据中均为0）
        for i in range(1, 7):
            try:
                label = f"抽凝式汽轮机1_再热蒸汽{i}段抽汽出口"
                conn = nw.get_conn(label)
                conn.set_attr(m=0.0)
            except KeyError:
                pass

        # 高压缸一段抽汽出口设置为0
        try:
            conn = nw.get_conn("抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口")
            conn.set_attr(m=0.0)
        except KeyError:
            pass

        # 再热蒸汽出口：固定温度（设计点）
        try:
            conn = nw.get_conn("1#发电锅炉_再热蒸汽高再出口")
            data = conn_data.get("1#发电锅炉_再热蒸汽高再出口", {})
            if data.get('T') is not None:
                conn.set_attr(T=data['T'])
        except KeyError:
            pass

        # 汽包下降管：固定流量（循环倍率）
        try:
            conn = nw.get_conn("1#发电锅炉_下降管入口")
            data = conn_data.get("1#发电锅炉_下降管入口", {})
            if data.get('m') is not None:
                conn.set_attr(m=data['m'])
        except KeyError:
            pass

        # 仅固定一个压力锚点（凝汽器背压）
        # 由于设置了所有组件的pr，整个循环压力链已被确定
        # 只需要一个锚点即可确定所有压力
        try:
            conn = nw.get_conn("抽凝式汽轮机1_中压缸排气出口")
            data = conn_data.get("抽凝式汽轮机1_中压缸排气出口", {})
            if data.get('p') is not None:
                conn.set_attr(p=data['p'])
        except KeyError:
            pass

        # 添加4个温度约束满足参数需求
        # 1. 水侧上省入口（给水温度）
        try:
            conn = nw.get_conn("1#发电锅炉_水侧上省入口")
            data = conn_data.get("1#发电锅炉_水侧上省入口", {})
            if data.get('T') is not None:
                conn.set_attr(T=data['T'])
        except KeyError:
            pass

        # 2. 蒸汽低过出口
        try:
            conn = nw.get_conn("1#发电锅炉_蒸汽低过出口")
            data = conn_data.get("1#发电锅炉_蒸汽低过出口", {})
            if data.get('T') is not None:
                conn.set_attr(T=data['T'])
        except KeyError:
            pass

        # 3. 蒸汽三过出口
        try:
            conn = nw.get_conn("1#发电锅炉_蒸汽三过出口")
            data = conn_data.get("1#发电锅炉_蒸汽三过出口", {})
            if data.get('T') is not None:
                conn.set_attr(T=data['T'])
        except KeyError:
            pass

        # 4. 再热蒸汽低再出口
        try:
            conn = nw.get_conn("1#发电锅炉_再热蒸汽低再出口")
            data = conn_data.get("1#发电锅炉_再热蒸汽低再出口", {})
            if data.get('T') is not None:
                conn.set_attr(T=data['T'])
        except KeyError:
            pass

        print("   ✓ 边界条件设置完成（入口+关键温度锚点+压力锚点）")

    def solve(
        self,
        *,
        max_iter: int | None = 500,
    ) -> bool:
        """求解网络（使用静态数据初始值）"""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None

        if max_iter is not None:
            self.nw.set_attr(max_iter=max_iter)

        print("\n开始求解...")
        print("提示: 使用静态数据初始值进行求解...")
        print("提示: 增加迭代次数到500...")

        solver_desc = "静态数据初始值"
        try:
            # 直接求解，不使用init_path（静态数据已经提供了初始值）
            self.nw.solve(mode="design")
        except Exception as exc:
            print(f"✗ 求解失败（{solver_desc}）: {exc}")
            import traceback
            traceback.print_exc()
            return False

        if not self.nw.converged:
            print("✗ 未收敛")
            return False

        # 收集求解信息
        self.convergence_info = {
            "converged": self.nw.converged,
            "iterations": getattr(self.nw, "iter", None),
            "max_iter": getattr(self.nw, "max_iter", None),
            "solver_strategy": solver_desc,
        }
        if hasattr(self.nw, "vec_res") and self.nw.vec_res is not None:
            try:
                self.convergence_info["residual"] = float(self.nw.vec_res.max())
            except Exception:
                pass

        print("✓ 求解成功\n")
        return True

    def analyze(self) -> dict:
        """分析结果"""
        if not self.nw or not self.nw.converged:
            print("✗ 网络未收敛")
            return {}

        print("=" * 80)
        print("系统性能分析")
        print("=" * 80)
        
        # 计算汽轮机总功率
        turb_names = [
            "抽凝式汽轮机1_高压缸一段", "抽凝式汽轮机1_高压缸二段",
            "抽凝式汽轮机1_低压缸一段", "抽凝式汽轮机1_低压缸二段",
            "抽凝式汽轮机1_低压缸三段", "抽凝式汽轮机1_低压缸四段",
            "抽凝式汽轮机1_低压缸五段", "抽凝式汽轮机1_低压缸六段",
            "抽凝式汽轮机1_低压缸七段"
        ]
        
        P_turb_total = 0.0
        print("\n【汽轮机功率分布】")
        for name in turb_names:
            turb = self.nw.get_comp(name)
            P = abs(turb.P.val) / 1e6  # W -> MW
            P_turb_total += P
            print(f"  {name:<30}: {P:10.3f} MW")
        
        # 泵功
        pump = self.nw.get_comp("1#发电锅炉_给水泵")
        P_pump = abs(pump.P.val) / 1e6
        P_net = P_turb_total - P_pump
        
        print(f"\n  汽轮机总功:  {P_turb_total:10.3f} MW")
        print(f"  泵功:        {P_pump:10.3f} MW")
        print(f"  净功率:      {P_net:10.3f} MW ⭐")
        
        print("=" * 80)
        
        self.results = {
            "P_net_MW": P_net,
            "P_turbine_total_MW": P_turb_total,
            "P_pump_MW": P_pump,
        }
        
        return self.results

    def export(self, path: Path = Path("stage2_complete_results.json")) -> None:
        """导出结果"""
        if not self.results:
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 结果已保存到：{path}\n")


def main() -> None:
    """主程序"""
    logging.getLogger("tespy").setLevel(logging.WARNING)

    model = CompleteBoilerTurbineModel()
    model.build_network()

    if model.solve():
        model.analyze()
        model.export()
        print("=" * 80)
        print("✓ 完整建模成功！")
        print("=" * 80)
    else:
        print("=" * 80)
        print("✗ 求解失败")
        print("=" * 80)


if __name__ == "__main__":
    main()
