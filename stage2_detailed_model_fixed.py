#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复循环依赖的简化版本
基于最小约束原则，只保留必要的边界条件
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


class FixedBoilerTurbineModel:
    """修复循环依赖的简化锅炉-汽轮机系统模型"""

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
        """构建网络"""
        print("\n" + "=" * 80)
        print("修复版本 - 最小约束原则")
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
        
        # 简化组件集合 - 只保留主要组件
        pump = Pump("1#发电锅炉_给水泵")
        drum = Drum("1#发电锅炉_汽包")
        
        # 简化的换热器
        hx_evap = HeatExchanger("1#发电锅炉_蒸发器上升管")
        hx_sh_final = HeatExchanger("1#发电锅炉_末级过热器")
        hx_eco = HeatExchanger("1#发电锅炉_上级省煤器")
        
        # 简化的汽轮机
        turb_hp = Turbine("抽凝式汽轮机1_高压缸")
        turb_lp = Turbine("抽凝式汽轮机1_低压缸")
        
        # 关键阀门
        valve_in = Valve("1#发电锅炉_进水阀")
        valve_hp = Valve("抽凝式汽轮机1_高压缸进气阀")
        
        # 源和汇
        src_air = Source("1#发电锅炉_空气源")
        src_bfg = Source("boiler1_高炉煤气源")
        src_cog = Source("1#发电锅炉_转炉煤气源")
        src_coke = Source("1#发电锅炉_焦炉煤气源")
        
        sink_flue = Sink("1#发电锅炉_烟气出口汇")
        sink_hp_ext = Sink("抽凝式汽轮机1_高压缸抽汽出口汇")
        sink_lp_ext = Sink("抽凝式汽轮机1_低压缸抽汽出口汇")
        
        cc_condenser = CycleCloser("凝汽器回路")
        
        # 燃烧系统和混合器
        combustor = DiabaticCombustionChamber("1#发电锅炉_炉膛燃烧室")
        merge_fuel1 = Merge("1#发电锅炉_燃料气混合器1")  # 高炉+转炉
        merge_fuel2 = Merge("1#发电锅炉_燃料气混合器2")  # 混合+焦炉
        split_hp = Splitter("抽凝式汽轮机1_高压缸抽汽分离")
        
        print(f"   已定义 16 个组件（简化版本）")
        
        # ==================== 连接定义 ====================
        print("\n[2] 定义连接...")
        
        # 水/蒸汽主循环
        c_pump_in = Connection(cc_condenser, "out1", pump, "in1", label="1#发电锅炉_水泵入口")
        c_pump_out = Connection(pump, "out1", valve_in, "in1", label="1#发电锅炉_水泵出口")
        c_valve_out = Connection(valve_in, "out1", hx_eco, "in2", label="1#发电锅炉_水侧省煤器入口")
        c_eco_out = Connection(hx_eco, "out2", drum, "in1", label="1#发电锅炉_汽包给水入口")
        c_drum_down = Connection(drum, "out1", hx_evap, "in2", label="1#发电锅炉_下降管入口")
        c_evap_out = Connection(hx_evap, "out2", drum, "in2", label="1#发电锅炉_上升管出口")
        c_drum_steam = Connection(drum, "out2", hx_sh_final, "in2", label="1#发电锅炉_汽包饱和蒸汽出口")
        c_sh_out = Connection(hx_sh_final, "out2", valve_hp, "in1", label="1#发电锅炉_主蒸汽")
        
        # 汽轮机系统
        c_valve_hp_out = Connection(valve_hp, "out1", turb_hp, "in1", label="抽凝式汽轮机1_高压蒸汽入口")
        c_turb_hp_out = Connection(turb_hp, "out1", split_hp, "in1", label="抽凝式汽轮机1_高压缸排汽")
        c_hp_main = Connection(split_hp, "out1", turb_lp, "in1", label="抽凝式汽轮机1_再热蒸汽")
        c_hp_ext = Connection(split_hp, "out2", sink_hp_ext, "in1", label="抽凝式汽轮机1_高压缸抽汽出口")
        c_turb_lp_out = Connection(turb_lp, "out1", cc_condenser, "in1", label="抽凝式汽轮机1_低压缸排汽")
        
        # 燃料系统
        c_bfg_in = Connection(src_bfg, "out1", merge_fuel1, "in1", label="boiler1_高炉煤气入口")
        c_cog_in = Connection(src_cog, "out1", merge_fuel1, "in2", label="1#发电锅炉_转炉煤气入口")
        c_mix1_out = Connection(merge_fuel1, "out1", merge_fuel2, "in1", label="1#发电锅炉_高转混合气")
        c_coke_in = Connection(src_coke, "out1", merge_fuel2, "in2", label="1#发电锅炉_焦炉煤气入口")
        c_fuel_out = Connection(merge_fuel2, "out1", combustor, "in2", label="1#发电锅炉_混合燃料气")
        c_air_in = Connection(src_air, "out1", combustor, "in1", label="1#发电锅炉_空气入口")
        # 烟气最终从蒸发器出来到出口
        c_flue_out = Connection(hx_evap, "out1", sink_flue, "in1", label="1#发电锅炉_烟气出口")
        
        # 烟气加热（简化）- 修复连接
        c_flue_hx1 = Connection(combustor, "out1", hx_sh_final, "in1", label="1#发电锅炉_末过烟气")
        c_flue_hx2 = Connection(hx_sh_final, "out1", hx_eco, "in1", label="1#发电锅炉_省煤器烟气")
        c_flue_hx3 = Connection(hx_eco, "out1", hx_evap, "in1", label="1#发电锅炉_蒸发器烟气")
        
        # 添加连接到网络
        nw.add_conns(
            c_pump_in, c_pump_out, c_valve_out, c_eco_out, c_drum_down, c_evap_out,
            c_drum_steam, c_sh_out,
            c_valve_hp_out, c_turb_hp_out, c_hp_main, c_hp_ext, c_turb_lp_out,
            c_bfg_in, c_cog_in, c_mix1_out, c_coke_in, c_fuel_out, c_air_in, c_flue_out,
            c_flue_hx1, c_flue_hx2, c_flue_hx3,
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
        """设置最少的组件参数"""
        # 只设置必要的效率参数
        try:
            pump = nw.get_comp("1#发电锅炉_给水泵")
            pump.set_attr(eta_s=0.8, pr=1.5)
        except KeyError:
            pass
        
        try:
            turb_hp = nw.get_comp("抽凝式汽轮机1_高压缸")
            turb_hp.set_attr(eta_s=0.85, pr=0.4)  # 添加关键pr
        except KeyError:
            pass
        
        try:
            turb_lp = nw.get_comp("抽凝式汽轮机1_低压缸")
            turb_lp.set_attr(eta_s=0.85, pr=0.3)  # 添加pr
        except KeyError:
            pass
        
        try:
            combustor = nw.get_comp("1#发电锅炉_炉膛燃烧室")
            combustor.set_attr(lamb=1.2, eta=0.98)
        except KeyError:
            pass
        
        try:
            valve_in = nw.get_comp("1#发电锅炉_进水阀")
            valve_in.set_attr(pr=0.98)  # 添加阀门压降
        except KeyError:
            pass
        
        try:
            valve_hp = nw.get_comp("抽凝式汽轮机1_高压缸进气阀")
            # valve_hp.set_attr(pr=0.99)  # 移除阀门压降
        except KeyError:
            pass
        
        # 换热器设置kA，减少压力约束
        hx_params = {
            "1#发电锅炉_蒸发器上升管": {"kA": 100000, "pr1": 0.97},  # 只保留pr1
            "1#发电锅炉_末级过热器": {"kA": 50000},  # 移除pr2
            "1#发电锅炉_上级省煤器": {"kA": 190000}  # 移除pr2
        }
        
        for name, params in hx_params.items():
            try:
                hx = nw.get_comp(name)
                for param, value in params.items():
                    hx.set_attr(**{param: value})
            except KeyError:
                pass
        
        print("   ✓ 组件参数设置完成（增加必要参数）")

    def _set_boundary_conditions(self, nw: Network) -> None:
        """设置最少的边界条件"""
        
        # 从CSV读取连接数据作为参考
        conn_data = {}
        for _, row in self.conn_df.iterrows():
            label = row.iloc[0]
            conn_data[label] = {
                'm': row['m'],
                'p': row['p'],
                'T': row['T'],
            }
        
        # === 只设置最关键的边界条件 ===
        
        # 1. 泵入口：固定压力和温度（循环起点）
        try:
            conn = nw.get_conn("1#发电锅炉_水泵入口")
            data = conn_data.get("1#发电锅炉_水泵入口", {})
            conn.set_attr(p=data['p'], T=data['T'] - 10, fluid={'water': 1})  # 降温避免饱和
        except KeyError:
            pass
        
        # 2. 主蒸汽：只固定压力（关键控制点）
        try:
            conn = nw.get_conn("1#发电锅炉_主蒸汽")
            data = conn_data.get("1#发电锅炉_主蒸汽", {})
            conn.set_attr(p=data['p'])  # 移除m约束
        except KeyError:
            pass
        
        # 3. 燃料气入口：固定流量和组分
        fuel_data = [
            ("boiler1_高炉煤气入口", {'N2': 0.4609, 'CO': 0.2078, 'CO2': 0.3293, 'H2': 0.002}),
            ("1#发电锅炉_转炉煤气入口", {'N2': 0.3389, 'CO': 0.4223, 'CO2': 0.2381, 'H2': 0.0007}),
            ("1#发电锅炉_焦炉煤气入口", {'N2': 0.2018, 'CO': 0.2305, 'CO2': 0.0996, 'H2': 0.1311, 'CH4': 0.337})
        ]
        
        for label, fluid_comp in fuel_data:
            try:
                conn = nw.get_conn(label)
                data = conn_data.get(label, {})
                conn.set_attr(m=data['m'], fluid=fluid_comp)
            except KeyError:
                pass
        
        # 3a. 增加燃料混合气流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_高转混合气")
            data = conn_data.get("1#发电锅炉_高转混合气", {})
            if data['m'] > 0:
                conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 3b. 增加最终燃料气流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_混合燃料气")
            data = conn_data.get("1#发电锅炉_混合燃料气", {})
            if data['m'] > 0:
                conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 3c. 增加高压缸抽汽流量约束
        try:
            conn = nw.get_conn("抽凝式汽轮机1_高压缸抽汽出口")
            data = conn_data.get("抽凝式汽轮机1_高压缸抽汽出口", {})
            if data['m'] > 0:
                conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 4. 空气入口：固定流量和组分
        try:
            conn = nw.get_conn("1#发电锅炉_空气入口")
            data = conn_data.get("1#发电锅炉_空气入口", {})
            conn.set_attr(m=data['m'], fluid={'N2': 0.76, 'O2': 0.24})
        except KeyError:
            pass
        
        # 4a. 增加烟气流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_烟气出口")
            data = conn_data.get("1#发电锅炉_烟气出口", {})
            conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 4b. 增加汽包水位约束（质量平衡）
        try:
            conn = nw.get_conn("1#发电锅炉_汽包饱和蒸汽出口")
            data = conn_data.get("1#发电锅炉_汽包饱和蒸汽出口", {})
            conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 4c. 增加汽包给水流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_汽包给水入口")
            data = conn_data.get("1#发电锅炉_汽包给水入口", {})
            conn.set_attr(m=data['m'])
        except KeyError:
            pass
        
        # 4d. 移除下降管流量约束（避免循环）
        # try:
        #     conn = nw.get_conn("1#发电锅炉_下降管入口")
        #     data = conn_data.get("1#发电锅炉_下降管入口", {})
        #     conn.set_attr(m=data['m'])
        # except KeyError:
        #     pass
        
        # 5. 低压缸排汽：固定压力（冷凝压力）
        try:
            conn = nw.get_conn("抽凝式汽轮机1_低压缸排汽")
            data = conn_data.get("抽凝式汽轮机1_低压缸排汽", {})
            conn.set_attr(p=data['p'])
        except KeyError:
            pass
        
        # 6. 增加温度和流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_主蒸汽")
            data = conn_data.get("1#发电锅炉_主蒸汽", {})
            conn.set_attr(T=data['T'])  # 添加温度约束
        except KeyError:
            pass
        
        # 7. 增加一个质量流量约束
        try:
            conn = nw.get_conn("1#发电锅炉_水泵入口")
            data = conn_data.get("1#发电锅炉_水泵入口", {})
            conn.set_attr(m=data['m'])  # 添加质量流量约束
        except KeyError:
            pass
        
        print("   ✓ 边界条件设置完成（增加关键约束）")

    def solve(self) -> bool:
        """求解网络"""
        if self.nw is None:
            self.build_network()
        assert self.nw is not None
        
        print("\n开始求解...")
        print("使用简化模型，应该能够收敛...")
        
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
        
        # 计算主要功率
        try:
            turb_hp = self.nw.get_comp("抽凝式汽轮机1_高压缸")
            P_hp = abs(turb_hp.P.val) / 1e6
            
            turb_lp = self.nw.get_comp("抽凝式汽轮机1_低压缸")
            P_lp = abs(turb_lp.P.val) / 1e6
            
            pump = self.nw.get_comp("1#发电锅炉_给水泵")
            P_pump = abs(pump.P.val) / 1e6
            
            P_net = P_hp + P_lp - P_pump
            
            print(f"\n  高压缸功率:  {P_hp:10.3f} MW")
            print(f"  低压缸功率:  {P_lp:10.3f} MW")
            print(f"  泵功:        {P_pump:10.3f} MW")
            print(f"  净功率:      {P_net:10.3f} MW ⭐")
            
            self.results = {
                "P_net_MW": P_net,
                "P_hp_MW": P_hp,
                "P_lp_MW": P_lp,
                "P_pump_MW": P_pump,
            }
        except Exception as e:
            print(f"分析失败: {e}")
            self.results = {}
        
        return self.results

    def export(self, path: Path = Path("stage2_fixed_results.json")) -> None:
        """导出结果"""
        if not self.results:
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 结果已保存到：{path}\n")


def main() -> None:
    """主程序"""
    logging.getLogger("tespy").setLevel(logging.WARNING)

    model = FixedBoilerTurbineModel()
    model.build_network()

    if model.solve():
        model.analyze()
        model.export()
        print("=" * 80)
        print("✓ 循环依赖已修复，模型成功求解！")
        print("=" * 80)
    else:
        print("=" * 80)
        print("✗ 求解失败，需要进一步调试")
        print("=" * 80)


if __name__ == "__main__":
    main()