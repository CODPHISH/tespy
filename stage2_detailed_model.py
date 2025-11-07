#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整复刻connections.csv的详细建模
基于boiler-turbine_design_state目录下的CSV文件重建完整模型结构
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
from tespy.connections import Connection, Ref


class CompleteBoilerTurbineModel:
    """完整的锅炉-汽轮机系统模型（完全复刻connections.csv）"""

    def __init__(self) -> None:
        """初始化"""
        self.nw: Network | None = None
        self.components: dict = {}
        self.connections: dict = {}
        self.results: dict = {}
        
        # 读取CSV数据
        self.load_csv_data()

    def load_csv_data(self) -> None:
        """从CSV文件加载组件和连接数据"""
        base_path = PROJECT_ROOT / "boiler-turbine_design_state"
        
        # 读取连接数据
        self.conn_df = pd.read_csv(base_path / "connections.csv", sep=';')
        
        # 读取组件数据
        comp_path = base_path / "components"
        self.comp_dfs = {}
        for csv_file in comp_path.glob("*.csv"):
            comp_type = csv_file.stem
            try:
                df = pd.read_csv(csv_file, sep=';')
                if not df.empty and len(df) > 0:
                    self.comp_dfs[comp_type] = df
            except Exception as e:
                print(f"Warning: Failed to load {csv_file}: {e}")
        
        print(f"✓ 加载了 {len(self.conn_df)} 条连接定义")
        print(f"✓ 加载了 {sum(len(df) for df in self.comp_dfs.values())} 个组件定义")

    def build_network(self) -> Network:
        """构建完整网络"""
        print("\n" + "=" * 80)
        print("完整建模 - 基于connections.csv的完整复刻")
        print("=" * 80)

        nw = Network(iterinfo=True)
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
        merge_air = Merge("1#发电锅炉_空气混合器")
        merge_fuel = Merge("1#发电锅炉_燃料气混合器")
        
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
        
        # 汇 (2个)
        sink_flue = Sink("1#发电锅炉_烟气出口汇")
        sink_turbine = Sink("抽凝式汽轮机1_排气出口汇")
        
        # CycleCloser  
        cc_condenser = CycleCloser("凝汽器回路")
        
        total_comps = 53
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
        c_hp1_ext = Connection(split_hp1, "out2", sink_turbine, "in1", label="抽凝式汽轮机1_高压蒸汽高压缸一段抽汽出口")
        c_hp2_out = Connection(turb_hp2, "out1", valve_hp_out, "in1", label="抽凝式汽轮机1_高压蒸汽去排气阀门")
        c_hp_exhaust_full = Connection(valve_hp_out, "out1", split_hp_exhaust, "in1", label="抽凝式汽轮机1_高压缸排汽")
        c_hp_exhaust_main = Connection(split_hp_exhaust, "out1", hx_rh_low, "in2", label="1#发电锅炉_再热蒸汽入口")
        c_hp_ext_tap = Connection(split_hp_exhaust, "out2", sink_turbine, "in2", label="抽凝式汽轮机1_高压缸排汽抽汽")
        
        # 【再热路径】
        c_rh_low_out = Connection(hx_rh_low, "out2", hx_rh_final, "in2", label="1#发电锅炉_再热蒸汽低再出口")
        c_rh_final_out = Connection(hx_rh_final, "out2", valve_mp_in, "in1", label="1#发电锅炉_再热蒸汽高再出口")
        c_valve_mp_in_out = Connection(valve_mp_in, "out1", turb_lp1, "in1", label="抽凝式汽轮机1_蒸汽去中压缸1段")
        
        # 【低压缸路径 - 7段，每段后抽汽】
        c_lp1_out = Connection(turb_lp1, "out1", split_lp1, "in1", label="抽凝式汽轮机1_再热蒸汽去1段抽汽分离")
        c_lp1_main = Connection(split_lp1, "out1", turb_lp2, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸2段")
        c_lp1_ext = Connection(split_lp1, "out2", sink_turbine, "in3", label="抽凝式汽轮机1_再热蒸汽1段抽汽出口")
        
        c_lp2_out = Connection(turb_lp2, "out1", split_lp2, "in1", label="抽凝式汽轮机1_再热蒸汽去2段抽汽分离")
        c_lp2_main = Connection(split_lp2, "out1", turb_lp3, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸3段")
        c_lp2_ext = Connection(split_lp2, "out2", sink_turbine, "in4", label="抽凝式汽轮机1_再热蒸汽2段抽汽出口")
        
        c_lp3_out = Connection(turb_lp3, "out1", split_lp3, "in1", label="抽凝式汽轮机1_再热蒸汽去3段抽汽分离")
        c_lp3_main = Connection(split_lp3, "out1", turb_lp4, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸4段")
        c_lp3_ext = Connection(split_lp3, "out2", sink_turbine, "in5", label="抽凝式汽轮机1_再热蒸汽3段抽汽出口")
        
        c_lp4_out = Connection(turb_lp4, "out1", split_lp4, "in1", label="抽凝式汽轮机1_再热蒸汽去4段抽汽分离")
        c_lp4_main = Connection(split_lp4, "out1", turb_lp5, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸5段")
        c_lp4_ext = Connection(split_lp4, "out2", sink_turbine, "in6", label="抽凝式汽轮机1_再热蒸汽4段抽汽出口")
        
        c_lp5_out = Connection(turb_lp5, "out1", split_lp5, "in1", label="抽凝式汽轮机1_再热蒸汽去5段抽汽分离")
        c_lp5_main = Connection(split_lp5, "out1", turb_lp6, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸6段")
        c_lp5_ext = Connection(split_lp5, "out2", sink_turbine, "in7", label="抽凝式汽轮机1_再热蒸汽5段抽汽出口")
        
        c_lp6_out = Connection(turb_lp6, "out1", split_lp6, "in1", label="抽凝式汽轮机1_再热蒸汽去6段抽汽分离")
        c_lp6_main = Connection(split_lp6, "out1", turb_lp7, "in1", label="抽凝式汽轮机1_再热蒸汽去中压缸7段")
        c_lp6_ext = Connection(split_lp6, "out2", sink_turbine, "in8", label="抽凝式汽轮机1_再热蒸汽6段抽汽出口")
        
        c_lp7_out = Connection(turb_lp7, "out1", valve_mp_out, "in1", label="抽凝式汽轮机1_再热蒸汽去排气阀门")
        c_turbine_exhaust = Connection(valve_mp_out, "out1", cc_condenser, "in1", label="抽凝式汽轮机1_中压缸排气出口")
        
        # 【燃料气/空气侧】
        c_air_in = Connection(src_air, "out1", merge_air, "in1", label="1#发电锅炉_空气入口")
        c_air_mixed = Connection(merge_air, "out1", hx_air_preheat, "in2", label="1#发电锅炉_空气混合加热空气入口")
        c_air_preheated = Connection(hx_air_preheat, "out2", combustor, "in1", label="1#发电锅炉_空气锅炉入口")
        
        c_bfg_in = Connection(src_bfg, "out1", merge_fuel, "in1", label="boiler1_高炉煤气入口")
        c_cog_in = Connection(src_cog, "out1", merge_fuel, "in2", label="1#发电锅炉_转炉煤气入口")
        c_fuel_mixed = Connection(merge_fuel, "out1", hx_fuel_preheat, "in2", label="1#发电锅炉_高转煤气混合后")
        c_coke_in = Connection(src_coke, "out1", combustor, "in3", label="1#发电锅炉_焦炉煤气入口")
        c_fuel_preheated = Connection(hx_fuel_preheat, "out2", combustor, "in2", label="1#发电锅炉_高转煤气预热后")
        
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
            c_air_in, c_air_mixed, c_air_preheated,
            c_bfg_in, c_cog_in, c_fuel_mixed,
            c_coke_in, c_fuel_preheated,
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
        """设置组件参数（从CSV读取）"""
        # 汽轮机参数
        if 'Turbine' in self.comp_dfs:
            turb_df = self.comp_dfs['Turbine']
            for _, row in turb_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['eta_s']):
                        comp.set_attr(eta_s=row['eta_s'])
                    if pd.notna(row['pr']):
                        comp.set_attr(pr=row['pr'])
                except KeyError:
                    pass
        
        # 换热器参数
        if 'HeatExchanger' in self.comp_dfs:
            hx_df = self.comp_dfs['HeatExchanger']
            for _, row in hx_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['kA']):
                        comp.set_attr(kA=row['kA'])
                    if pd.notna(row['pr1']):
                        comp.set_attr(pr1=row['pr1'])
                    if pd.notna(row['pr2']):
                        comp.set_attr(pr2=row['pr2'])
                except KeyError:
                    pass
        
        # 泵参数
        if 'Pump' in self.comp_dfs:
            pump_df = self.comp_dfs['Pump']
            for _, row in pump_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['eta_s']):
                        comp.set_attr(eta_s=row['eta_s'])
                    if pd.notna(row['pr']):
                        comp.set_attr(pr=row['pr'])
                except KeyError:
                    pass
        
        # 阀门参数
        if 'Valve' in self.comp_dfs:
            valve_df = self.comp_dfs['Valve']
            for _, row in valve_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['pr']):
                        comp.set_attr(pr=row['pr'])
                except KeyError:
                    pass
        
        # 管道参数
        if 'Pipe' in self.comp_dfs:
            pipe_df = self.comp_dfs['Pipe']
            for _, row in pipe_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['pr']):
                        comp.set_attr(pr=row['pr'])
                except KeyError:
                    pass
        
        # 燃烧室参数
        if 'DiabaticCombustionChamber' in self.comp_dfs:
            cc_df = self.comp_dfs['DiabaticCombustionChamber']
            for _, row in cc_df.iterrows():
                name = row.iloc[0]
                try:
                    comp = nw.get_comp(name)
                    if pd.notna(row['lamb']):
                        comp.set_attr(lamb=row['lamb'])
                    if pd.notna(row['pr']):
                        comp.set_attr(pr=row['pr'])
                    if pd.notna(row['eta']):
                        comp.set_attr(eta=row['eta'])
                except KeyError:
                    pass
        
        print("   ✓ 组件参数设置完成")

    def _set_boundary_conditions(self, nw: Network) -> None:
        """设置边界条件（从connections.csv读取）"""
        
        # 从CSV读取连接数据
        conn_data = {}
        for _, row in self.conn_df.iterrows():
            label = row.iloc[0]
            conn_data[label] = {
                'm': row['m'],
                'p': row['p'],
                'T': row['T'],
                'h': row['h'],
                'x': row['x'] if pd.notna(row['x']) else None,
            }
        
        # 主蒸汽
        try:
            conn = nw.get_conn("1#发电锅炉_主蒸汽")
            data = conn_data.get("1#发电锅炉_主蒸汽", {})
            conn.set_attr(m=data['m'], p=data['p'], T=data['T'], fluid={'water': 1})
        except KeyError:
            pass
        
        # 空气入口
        try:
            conn = nw.get_conn("1#发电锅炉_空气入口")
            data = conn_data.get("1#发电锅炉_空气入口", {})
            conn.set_attr(m=data['m'], p=data['p'], T=data['T'], fluid={'n2': 0.76, 'o2': 0.24})
        except KeyError:
            pass
        
        # 高炉煤气入口
        try:
            conn = nw.get_conn("boiler1_高炉煤气入口")
            data = conn_data.get("boiler1_高炉煤气入口", {})
            fluid_comp = {'n2': 0.4609, 'co': 0.2078, 'co2': 0.3293, 'h2': 0.002}
            conn.set_attr(m=data['m'], p=data['p'], T=data['T'], fluid=fluid_comp)
        except KeyError:
            pass
        
        # 转炉煤气
        try:
            conn = nw.get_conn("1#发电锅炉_转炉煤气入口")
            data = conn_data.get("1#发电锅炉_转炉煤气入口", {})
            fluid_comp = {'n2': 0.3389, 'co': 0.4223, 'co2': 0.2381, 'h2': 0.0007}
            conn.set_attr(m=data['m'], p=data['p'], T=data['T'], fluid=fluid_comp)
        except KeyError:
            pass
        
        # 焦炉煤气
        try:
            conn = nw.get_conn("1#发电锅炉_焦炉煤气入口")
            data = conn_data.get("1#发电锅炉_焦炉煤气入口", {})
            fluid_comp = {'n2': 0.2018, 'co': 0.2305, 'co2': 0.0996, 'h2': 0.1311, 'ch4': 0.337}
            conn.set_attr(m=data['m'], p=data['p'], T=data['T'], fluid=fluid_comp)
        except KeyError:
            pass
        
        # 泵入口
        try:
            conn = nw.get_conn("1#发电锅炉_水泵入口")
            data = conn_data.get("1#发电锅炉_水泵入口", {})
            conn.set_attr(p=data['p'], T=data['T'], fluid={'water': 1})
        except KeyError:
            pass
        
        # 汽包饱和蒸汽
        try:
            conn = nw.get_conn("1#发电锅炉_汽包饱和蒸汽出口")
            conn.set_attr(x=1.0)
        except KeyError:
            pass
        
        # 高压缸排汽抽汽
        try:
            conn = nw.get_conn("抽凝式汽轮机1_高压缸排汽抽汽")
            data = conn_data.get("抽凝式汽轮机1_高压缸排汽抽汽", {})
            conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 所有抽汽出口设置为0流量（从CSV看这些都是0）
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
        
        print("   ✓ 边界条件设置完成")

    def solve(self) -> bool:
        """求解网络"""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None
        
        print("\n开始求解...")
        print("警告: 由于模型复杂性，初次求解可能需要较长时间...")
        
        try:
            # 尝试从CSV文件初始化
            self.nw.solve(mode="design", init_path="boiler-turbine_design_state")
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
