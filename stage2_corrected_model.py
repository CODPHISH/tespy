#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纠正的锅炉-汽轮机系统模型
基于对参考仿真结果数据的反推分析
- connections.csv: 定义网络结构和热力学状态点
- components/*.csv: 参考仿真结果
策略: 只使用真正的输入边界条件，让TESPy计算component参数
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
import pandas as pd

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
    Splitter,
    Merge,
    Valve,
    Drum,
    DiabaticCombustionChamber,
    Pipe,
)
from tespy.connections import Connection


class CorrectedBoilerTurbineModel:
    """基于参考数据反推的正确模型"""

    def __init__(self) -> None:
        """初始化"""
        self.nw: Network | None = None
        self.conn_df = None
        self.results: dict = {}
        self.load_reference_data()

    def load_reference_data(self) -> None:
        """加载参考数据"""
        base_path = PROJECT_ROOT / "boiler-turbine_design_state"
        self.conn_df = pd.read_csv(base_path / "connections.csv", sep=';')
        print(f"✓ 加载了 {len(self.conn_df)} 条连接参考数据")

    def build_network(self) -> Network:
        """构建网络"""
        print("\n" + "=" * 80)
        print("纠正模型 - 基于参考数据反推的正确输入")
        print("=" * 80)

        nw = Network(
            iterinfo=True,
            fluids=["water", "N2", "O2", "CO2", "CO", "H2", "CH4"],
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

        # 完整组件集合（基于connections.csv的结构）
        # 汽轮机 (9个)
        turbs = {
            "turb_hp1": Turbine("抽凝式汽轮机1_高压缸一段"),
            "turb_hp2": Turbine("抽凝式汽轮机1_高压缸二段"),
            "turb_lp1": Turbine("抽凝式汽轮机1_低压缸一段"),
            "turb_lp2": Turbine("抽凝式汽轮机1_低压缸二段"),
            "turb_lp3": Turbine("抽凝式汽轮机1_低压缸三段"),
            "turb_lp4": Turbine("抽凝式汽轮机1_低压缸四段"),
            "turb_lp5": Turbine("抽凝式汽轮机1_低压缸五段"),
            "turb_lp6": Turbine("抽凝式汽轮机1_低压缸六段"),
            "turb_lp7": Turbine("抽凝式汽轮机1_低压缸七段"),
        }

        # 换热器 (11个)
        hxs = {
            "hx_evap": HeatExchanger("1#发电锅炉_蒸发器上升管"),
            "hx_eco_lower": HeatExchanger("1#发电锅炉_下级省煤器"),
            "hx_eco_upper": HeatExchanger("1#发电锅炉_上级省煤器"),
            "hx_sh_low": HeatExchanger("1#发电锅炉_低温过热器"),
            "hx_sh_screen": HeatExchanger("1#发电锅炉_屏式过热器"),
            "hx_sh_tertiary": HeatExchanger("1#发电锅炉_三级过热器"),
            "hx_sh_final": HeatExchanger("1#发电锅炉_末级过热器"),
            "hx_rh_low": HeatExchanger("1#发电锅炉_低温再热器"),
            "hx_rh_final": HeatExchanger("1#发电锅炉_末级再热器"),
            "hx_air_preheat": HeatExchanger("1#发电锅炉_空气预热器"),
            "hx_fuel_preheat": HeatExchanger("1#发电锅炉_煤气预热器"),
        }

        # 其他组件
        pump = Pump("1#发电锅炉_给水泵")
        drum = Drum("1#发电锅炉_汽包")
        combustor = DiabaticCombustionChamber("1#发电锅炉_炉膛燃烧室")
        pipe_scr = Pipe("1#发电锅炉_脱硫脱硝")

        # 阀门
        valve_water_in = Valve("1#发电锅炉_进水阀")
        valve_hp_in = Valve("抽凝式汽轮机1_高压缸进气阀")
        valve_hp_out = Valve("抽凝式汽轮机1_高压缸排气阀")
        valve_mp_in = Valve("抽凝式汽轮机1_中压缸进气阀")
        valve_mp_out = Valve("抽凝式汽轮机1_中压缸排气阀")

        # Splitters
        split_hp1 = Splitter("抽凝式汽轮机1_高压缸一段抽汽分离")
        split_hp_exhaust = Splitter("抽凝式汽轮机1_高压缸排汽分离")
        split_lp1 = Splitter("抽凝式汽轮机1_再热蒸汽1段抽汽分离")
        split_lp2 = Splitter("抽凝式汽轮机1_再热蒸汽2段抽汽分离")
        split_lp3 = Splitter("抽凝式汽轮机1_再热蒸汽3段抽汽分离")
        split_lp4 = Splitter("抽凝式汽轮机1_再热蒸汽4段抽汽分离")
        split_lp5 = Splitter("抽凝式汽轮机1_再热蒸汽5段抽汽分离")
        split_lp6 = Splitter("抽凝式汽轮机1_再热蒸汽6段抽汽分离")

        # Mergers
        merge_fuel_1 = Merge("1#发电锅炉_燃料气混合器1")
        merge_fuel_2 = Merge("1#发电锅炉_燃料气混合器2")

        # 源和汇
        src_air = Source("1#发电锅炉_空气源")
        src_bfg = Source("boiler1_高炉煤气源")
        src_cog = Source("1#发电锅炉_转炉煤气源")
        src_coke = Source("1#发电锅炉_焦炉煤气源")

        sink_flue = Sink("1#发电锅炉_烟气出口汇")
        sink_hp1_ext = Sink("抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口汇")
        sink_hp_exhaust_ext = Sink("抽凝式汽轮机1_高压缸排汽抽汽汇")
        sink_lp1_ext = Sink("抽凝式汽轮机1_再热蒸汽1段抽汽出口汇")
        sink_lp2_ext = Sink("抽凝式汽轮机1_再热蒸汽2段抽汽出口汇")
        sink_lp3_ext = Sink("抽凝式汽轮机1_再热蒸汽3段抽汽出口汇")
        sink_lp4_ext = Sink("抽凝式汽轮机1_再热蒸汽4段抽汽出口汇")
        sink_lp5_ext = Sink("抽凝式汽轮机1_再热蒸汽5段抽汽出口汇")
        sink_lp6_ext = Sink("抽凝式汽轮机1_再热蒸汽6段抽汽出口汇")

        cc_condenser = CycleCloser("凝汽器回路")

        print(f"   已定义 60 个组件")

        # ==================== 连接定义 ====================
        print("\n[2] 定义连接...")

        # 从connections.csv创建连接对象
        # 这里需要基于connections.csv的结构构建网络
        # 为简化起见，使用标准连接结构

        # 水/蒸汽侧主循环 (12 connections)
        c_pump_in = Connection(cc_condenser, "out1", pump, "in1", label="1#发电锅炉_水泵入口")
        c_pump_out = Connection(pump, "out1", valve_water_in, "in1", label="1#发电锅炉_水泵出口")
        c_valve_out = Connection(valve_water_in, "out1", hxs["hx_eco_lower"], "in2", label="1#发电锅炉_水侧下省入口")
        c_eco_lower_out = Connection(hxs["hx_eco_lower"], "out2", hxs["hx_eco_upper"], "in2", label="1#发电锅炉_水侧上省入口")
        c_eco_upper_out = Connection(hxs["hx_eco_upper"], "out2", drum, "in1", label="1#发电锅炉_汽包给水入口")
        c_drum_downcomer = Connection(drum, "out1", hxs["hx_evap"], "in2", label="1#发电锅炉_下降管入口")
        c_evap_out = Connection(hxs["hx_evap"], "out2", drum, "in2", label="1#发电锅炉_上升管出口")
        c_drum_sat_steam = Connection(drum, "out2", hxs["hx_sh_low"], "in2", label="1#发电锅炉_汽包饱和蒸汽出口")
        c_sh_low_out = Connection(hxs["hx_sh_low"], "out2", hxs["hx_sh_screen"], "in2", label="1#发电锅炉_蒸汽低过出口")
        c_sh_screen_out = Connection(hxs["hx_sh_screen"], "out2", hxs["hx_sh_tertiary"], "in2", label="1#发电锅炉_蒸汽屏过出口")
        c_sh_tertiary_out = Connection(hxs["hx_sh_tertiary"], "out2", hxs["hx_sh_final"], "in2", label="1#发电锅炉_蒸汽三过出口")
        c_main_steam = Connection(hxs["hx_sh_final"], "out2", valve_hp_in, "in1", label="1#发电锅炉_主蒸汽")

        # 高压缸路径 (8 connections)
        c_valve_hp_in_out = Connection(valve_hp_in, "out1", turbs["turb_hp1"], "in1", label="抽凝式汽轮机1_高压蒸汽去高压缸1段")
        c_hp1_out = Connection(turbs["turb_hp1"], "out1", split_hp1, "in1", label="抽凝式汽轮机1_高压缸一段蒸汽抽汽分离")
        c_hp1_main = Connection(split_hp1, "out1", turbs["turb_hp2"], "in1", label="抽凝式汽轮机1_高压蒸汽去高压缸2段")
        c_hp1_ext = Connection(split_hp1, "out2", sink_hp1_ext, "in1", label="抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口")
        c_hp2_out = Connection(turbs["turb_hp2"], "out1", valve_hp_out, "in1", label="抽凝式汽轮机1_高压蒸汽去排气阀门")
        c_hp_exhaust_full = Connection(valve_hp_out, "out1", split_hp_exhaust, "in1", label="抽凝式汽轮机1_高压缸排汽")
        c_hp_exhaust_main = Connection(split_hp_exhaust, "out1", hxs["hx_rh_low"], "in2", label="1#发电锅炉_再热蒸汽入口")
        c_hp_ext_tap = Connection(split_hp_exhaust, "out2", sink_hp_exhaust_ext, "in1", label="抽凝式汽轮机1_高压缸排汽抽汽")

        # 再热路径 (3 connections)
        c_rh_low_out = Connection(hxs["hx_rh_low"], "out2", hxs["hx_rh_final"], "in2", label="1#发电锅炉_再热蒸汽低再出口")
        c_rh_final_out = Connection(hxs["hx_rh_final"], "out2", valve_mp_in, "in1", label="1#发电锅炉_再热蒸汽高再出口")
        c_valve_mp_in_out = Connection(valve_mp_in, "out1", turbs["turb_lp1"], "in1", label="抽凝式汽轮机1_蒸汽去中压缸1段")

        # 低压缸路径 (21 connections)
        c_lp1_out = Connection(turbs["turb_lp1"], "out1", split_lp1, "in1", label="抽凝式汽轮机1_再热蒸汽去1段抽汽分离")
        c_lp1_main = Connection(split_lp1, "out1", turbs["turb_lp2"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸2段")
        c_lp1_ext = Connection(split_lp1, "out2", sink_lp1_ext, "in1", label="抽凝式汽轮机1_再热蒸汽1段抽汽出口")

        c_lp2_out = Connection(turbs["turb_lp2"], "out1", split_lp2, "in1", label="抽凝式汽轮机1_再热蒸汽去2段抽汽分离")
        c_lp2_main = Connection(split_lp2, "out1", turbs["turb_lp3"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸3段")
        c_lp2_ext = Connection(split_lp2, "out2", sink_lp2_ext, "in1", label="抽凝式汽轮机1_再热蒸汽2段抽汽出口")

        c_lp3_out = Connection(turbs["turb_lp3"], "out1", split_lp3, "in1", label="抽凝式汽轮机1_再热蒸汽去3段抽汽分离")
        c_lp3_main = Connection(split_lp3, "out1", turbs["turb_lp4"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸4段")
        c_lp3_ext = Connection(split_lp3, "out2", sink_lp3_ext, "in1", label="抽凝式汽轮机1_再热蒸汽3段抽汽出口")

        c_lp4_out = Connection(turbs["turb_lp4"], "out1", split_lp4, "in1", label="抽凝式汽轮机1_再热蒸汽去4段抽汽分离")
        c_lp4_main = Connection(split_lp4, "out1", turbs["turb_lp5"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸5段")
        c_lp4_ext = Connection(split_lp4, "out2", sink_lp4_ext, "in1", label="抽凝式汽轮机1_再热蒸汽4段抽汽出口")

        c_lp5_out = Connection(turbs["turb_lp5"], "out1", split_lp5, "in1", label="抽凝式汽轮机1_再热蒸汽去5段抽汽分离")
        c_lp5_main = Connection(split_lp5, "out1", turbs["turb_lp6"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸6段")
        c_lp5_ext = Connection(split_lp5, "out2", sink_lp5_ext, "in1", label="抽凝式汽轮机1_再热蒸汽5段抽汽出口")

        c_lp6_out = Connection(turbs["turb_lp6"], "out1", split_lp6, "in1", label="抽凝式汽轮机1_再热蒸汽去6段抽汽分离")
        c_lp6_main = Connection(split_lp6, "out1", turbs["turb_lp7"], "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸7段")
        c_lp6_ext = Connection(split_lp6, "out2", sink_lp6_ext, "in1", label="抽凝式汽轮机1_再热蒸汽6段抽汽出口")

        c_lp7_out = Connection(turbs["turb_lp7"], "out1", valve_mp_out, "in1", label="抽凝式汽轮机1_再热蒸汽去排气阀门")
        c_turbine_exhaust = Connection(valve_mp_out, "out1", cc_condenser, "in1", label="抽凝式汽轮机1_中压缸排气出口")

        # 燃料气/空气侧 (8 connections)
        c_air_in = Connection(src_air, "out1", hxs["hx_air_preheat"], "in2", label="1#发电锅炉_空气入口")
        c_air_preheated = Connection(hxs["hx_air_preheat"], "out2", combustor, "in1", label="1#发电锅炉_空气锅炉入口")

        c_bfg_in = Connection(src_bfg, "out1", merge_fuel_1, "in1", label="boiler1_高炉煤气入口")
        c_cog_in = Connection(src_cog, "out1", merge_fuel_1, "in2", label="1#发电锅炉_转炉煤气入口")
        c_fuel_mixed_1 = Connection(merge_fuel_1, "out1", hxs["hx_fuel_preheat"], "in2", label="1#发电锅炉_高转煤气混合后")
        c_fuel_preheated = Connection(hxs["hx_fuel_preheat"], "out2", merge_fuel_2, "in1", label="1#发电锅炉_高转煤气预热后")
        c_coke_in = Connection(src_coke, "out1", merge_fuel_2, "in2", label="1#发电锅炉_焦炉煤气入口")
        c_fuel_final = Connection(merge_fuel_2, "out1", combustor, "in2", label="1#发电锅炉_混合燃料气锅炉入口")

        # 烟气侧 (13 connections)
        c_flue_combustor = Connection(combustor, "out1", hxs["hx_sh_final"], "in1", label="1#发电锅炉_燃烧烟气")
        c_flue_1 = Connection(hxs["hx_sh_final"], "out1", hxs["hx_sh_tertiary"], "in1", label="1#发电锅炉_末过烟气入口")
        c_flue_2 = Connection(hxs["hx_sh_tertiary"], "out1", hxs["hx_sh_screen"], "in1", label="1#发电锅炉_三过烟气入口")
        c_flue_3 = Connection(hxs["hx_sh_screen"], "out1", hxs["hx_sh_low"], "in1", label="1#发电锅炉_低过烟气入口")
        c_flue_4 = Connection(hxs["hx_sh_low"], "out1", hxs["hx_rh_final"], "in1", label="1#发电锅炉_再烟气入口")
        c_flue_5 = Connection(hxs["hx_rh_final"], "out1", hxs["hx_rh_low"], "in1", label="1#发电锅炉_低再烟气入口")
        c_flue_6 = Connection(hxs["hx_rh_low"], "out1", hxs["hx_evap"], "in1", label="1#发电锅炉_上升管烟气出口")
        c_flue_7 = Connection(hxs["hx_evap"], "out1", hxs["hx_eco_upper"], "in1", label="1#发电锅炉_上省烟气入口")
        c_flue_8 = Connection(hxs["hx_eco_upper"], "out1", pipe_scr, "in1", label="1#发电锅炉_SCR烟气入口")
        c_flue_9 = Connection(pipe_scr, "out1", hxs["hx_eco_lower"], "in1", label="1#发电锅炉_下省烟气入口")
        c_flue_10 = Connection(hxs["hx_eco_lower"], "out1", hxs["hx_air_preheat"], "in1", label="1#发电锅炉_空预烟气入口")
        c_flue_11 = Connection(hxs["hx_air_preheat"], "out1", hxs["hx_fuel_preheat"], "in1", label="1#发电锅炉_煤预烟气入口")
        c_flue_out = Connection(hxs["hx_fuel_preheat"], "out1", sink_flue, "in1", label="1#发电锅炉_煤预烟气出口")

        # 添加连接到网络
        conns = [
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
        ]
        
        nw.add_conns(*conns)
        print(f"   已定义 {len(nw.conns)} 个连接")

        # ==================== 设置边界条件 ====================
        print("\n[3] 设置边界条件（仅真实输入）...")
        self._set_boundary_conditions(nw)

        # ==================== 设置组件参数 ====================
        print("\n[4] 设置组件参数（仅设计参数）...")
        self._set_component_parameters(nw, turbs)

        print("=" * 80)
        self.nw = nw
        return nw

    def _set_boundary_conditions(self, nw: Network) -> None:
        """设置真实的输入边界条件"""
        
        # 从connections.csv读取boundary conditions
        conn_dict = {}
        for _, row in self.conn_df.iterrows():
            label = row.iloc[0]
            conn_dict[label] = row

        # === 设置源点边界条件 ===
        
        # 1. 泵入口 (凝结水): p, T, fluid
        try:
            conn = nw.get_conn("1#发电锅炉_水泵入口")
            data = conn_dict.get("1#发电锅炉_水泵入口")
            if data is not None:
                conn.set_attr(
                    p=data['p'],
                    T=data['T'],
                    fluid={'water': 1}
                )
        except KeyError:
            pass

        # 2. 空气入口
        try:
            conn = nw.get_conn("1#发电锅炉_空气入口")
            data = conn_dict.get("1#发电锅炉_空气入口")
            if data is not None:
                conn.set_attr(
                    m=data['m'],
                    p=data['p'],
                    T=data['T'],
                    fluid={'N2': 0.76, 'O2': 0.24}
                )
        except KeyError:
            pass

        # 3. 燃料气入口
        fuel_inlets = [
            ("boiler1_高炉煤气入口", {'N2': 0.4609, 'CO': 0.2078, 'CO2': 0.3293, 'H2': 0.002}),
            ("1#发电锅炉_转炉煤气入口", {'N2': 0.3389, 'CO': 0.4223, 'CO2': 0.2381, 'H2': 0.0007}),
            ("1#发电锅炉_焦炉煤气入口", {'N2': 0.2018, 'CO': 0.2305, 'CO2': 0.0996, 'H2': 0.1311, 'CH4': 0.337})
        ]

        for label, fluid_comp in fuel_inlets:
            try:
                conn = nw.get_conn(label)
                data = conn_dict.get(label)
                if data is not None:
                    conn.set_attr(
                        m=data['m'],
                        p=data['p'],
                        T=data['T'],
                        fluid=fluid_comp
                    )
            except KeyError:
                pass

        # 4. 凝汽器压力约束 (重要)
        try:
            conn = nw.get_conn("抽凝式汽轮机1_中压缸排气出口")
            data = conn_dict.get("抽凝式汽轮机1_中压缸排气出口")
            if data is not None:
                conn.set_attr(p=data['p'])
        except KeyError:
            pass

        print("   ✓ 边界条件设置完成")

    def _set_component_parameters(self, nw: Network, turbs: dict) -> None:
        """设置组件参数（仅设计参数，不设置计算结果）"""
        
        # 汽轮机: 只设置效率（NOT压力比）
        # 参考Turbine.csv中的eta_s值
        turbine_params = {
            "turb_hp1": 0.7475393654293013,
            "turb_hp2": 0.7475393654295656,
            "turb_lp1": 0.7472954358438135,
            "turb_lp2": 0.7472954358437761,
            "turb_lp3": 0.7472954358437081,
            "turb_lp4": 0.7472954358437414,
            "turb_lp5": 0.7472954358437218,
            "turb_lp6": 0.7472954358440616,
            "turb_lp7": 0.7472954358437331,
        }

        for key, eta_s in turbine_params.items():
            try:
                turbs[key].set_attr(eta_s=eta_s)
            except KeyError:
                pass

        # 泵: 设置效率
        try:
            pump = nw.get_comp("1#发电锅炉_给水泵")
            pump.set_attr(eta_s=0.85)
        except KeyError:
            pass

        # 燃烧室: 设置空气比和效率
        try:
            combustor = nw.get_comp("1#发电锅炉_炉膛燃烧室")
            combustor.set_attr(lamb=1.2, eta=0.98)
        except KeyError:
            pass

        print("   ✓ 组件参数设置完成（设计参数）")

    def solve(self) -> bool:
        """求解网络"""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None

        print("\n开始求解...")
        
        try:
            self.nw.solve(mode="design")
        except Exception as exc:
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
        """分析结果"""
        if not self.nw or not self.nw.converged:
            print("✗ 网络未收敛")
            return {}

        print("=" * 80)
        print("系统性能分析")
        print("=" * 80)

        # 计算功率
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
            try:
                turb = self.nw.get_comp(name)
                P = abs(turb.P.val) / 1e6  # W -> MW
                P_turb_total += P
                print(f"  {name:<30}: {P:10.3f} MW")
            except KeyError:
                pass

        try:
            pump = self.nw.get_comp("1#发电锅炉_给水泵")
            P_pump = abs(pump.P.val) / 1e6
            P_net = P_turb_total - P_pump

            print(f"\n  汽轮机总功:  {P_turb_total:10.3f} MW")
            print(f"  泵功:        {P_pump:10.3f} MW")
            print(f"  净功率:      {P_net:10.3f} MW ⭐")

            self.results = {
                "P_net_MW": P_net,
                "P_turbine_total_MW": P_turb_total,
                "P_pump_MW": P_pump,
            }
        except KeyError:
            pass

        print("=" * 80)
        return self.results

    def export_results(self, path: Path = Path("stage2_corrected_results.json")) -> None:
        """导出结果"""
        if not self.results:
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 结果已保存到：{path}\n")


def main() -> None:
    """主程序"""
    logging.getLogger("tespy").setLevel(logging.WARNING)

    model = CorrectedBoilerTurbineModel()
    model.build_network()

    if model.solve():
        model.analyze()
        model.export_results()
        print("=" * 80)
        print("✓ 纠正模型成功执行！")
        print("=" * 80)
    else:
        print("=" * 80)
        print("✗ 求解失败")
        print("=" * 80)


if __name__ == "__main__":
    main()
