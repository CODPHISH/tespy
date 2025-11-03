#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2：简化但稳定的高级预测模型

基于阶段1的稳定性，添加以下核心功能：
✓ 1. 烟气侧建模：使用HeatExchanger + kA参数
✓ 2. 简化回热系统：1个高压加热器 + 除氧器 + 1个低压加热器
✓ 3. 参数校准功能
✓ 4. 预测能力增强

系统配置（简化但完整）：
- 锅炉系统：省煤器 → 水冷壁 → 过热器（带烟气侧，无汽包）
- 再热系统：高压缸 → 再热器 → 低压缸
- 回热系统：1个高压加热器 + 除氧器 + 1个低压加热器
- 抽汽系统：3级抽汽
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from tespy.networks import Network
from tespy.components import (
    CycleCloser,
    HeatExchanger,
    Turbine,
    Condenser,
    Pump,
    Merge,
    Splitter,
    Source,
    Sink,
)
from tespy.connections import Connection, Ref


class Stage2SimplifiedSystem:
    """阶段2：简化但稳定的高级预测模型."""
    
    def __init__(self, design_params: dict = None):
        """初始化系统参数."""
        defaults = {
            # === 设计点参数 ===
            'main_steam_p': 150,
            'main_steam_T': 600,
            'main_steam_m': 100,
            'reheat_p': 30,
            'reheat_T': 600,
            'condenser_p': 0.05,
            
            # === 烟气参数 ===
            'flue_gas_T_in': 1200,
            'flue_gas_m': 300,
            'flue_gas_p': 1.05,
            
            # === 冷却水参数 ===
            'cooling_water_T_in': 20,
            'cooling_water_T_out': 32,
            
            # === 回热系统参数 ===
            'hp_heater_ttd_u': 3,
            'deaerator_p': 3.0,
            'lp_heater_ttd_u': 5,
            
            # === 设备效率 ===
            'hp_turbine_eta': 0.88,
            'lp_turbine_eta': 0.86,
            'pump_eta': 0.78,
            'condensate_pump_eta': 0.75,
            
            # === 压降 ===
            'economizer_pr1': 0.98,
            'economizer_pr2': 0.98,
            'waterwall_pr1': 0.98,
            'waterwall_pr2': 0.98,
            'superheater_pr1': 0.98,
            'superheater_pr2': 0.95,
            'reheater_pr1': 0.98,
            'reheater_pr2': 0.97,
            
            # === 换热器kA（从设计点反算）===
            'economizer_kA': None,
            'waterwall_kA': None,
            'superheater_kA': None,
            'reheater_kA': None,
        }
        
        if design_params:
            defaults.update(design_params)
        
        self.params = defaults
        self.nw = None
        self.results = {}
        self.mode = 'design'
    
    def build_network(self, mode='design') -> Network:
        """构建网络模型."""
        self.mode = mode
        
        print("\n" + "=" * 80)
        print(f"阶段2：简化但稳定的高级预测模型 - 模式: {mode.upper()}")
        print("=" * 80)
        print("\n系统配置：")
        print("  • 锅炉系统：省煤器 → 水冷壁 → 过热器（带烟气侧，HeatExchanger + kA）")
        print("  • 再热系统：高压缸 → 再热器 → 低压缸")
        print("  • 回热系统：1个高压加热器 + 除氧器 + 1个低压加热器")
        print("  • 抽汽系统：3级抽汽")
        if mode == 'design':
            print("  • 模式：设计模式（反算换热器kA参数）")
        else:
            print("  • 模式：预测模式（固定kA，预测主蒸汽参数）")
        print("=" * 80)
        
        nw = Network(iterinfo=False)
        nw.units.set_defaults(
            temperature="degC",
            pressure="bar",
            enthalpy="kJ/kg",
            power="MW",
            heat="MW",
        )
        print("\n[1] 网络初始化完成")
        
        # 定义组件
        cc = CycleCloser("循环闭合器")
        
        # 锅炉系统（带烟气侧）
        economizer = HeatExchanger("省煤器")
        waterwall = HeatExchanger("水冷壁")
        superheater = HeatExchanger("过热器")
        reheater = HeatExchanger("再热器")
        
        # 汽轮机系统
        hp_turbine = Turbine("高压缸")
        lp_turbine = Turbine("低压缸")
        
        # 抽汽系统
        sp_hp = Splitter("高压缸后分流")
        sp_lp = Splitter("低压缸后分流")
        lp_extract = Splitter("低压抽汽分配")
        
        # 回热系统
        hp_heater = HeatExchanger("高压加热器")
        deaerator = Merge("除氧器", num_in=4)
        lp_heater = HeatExchanger("低压加热器")
        
        # 泵系统
        condensate_pump = Pump("凝结水泵")
        feedwater_pump = Pump("给水泵")
        
        # 凝汽系统
        condenser = Condenser("凝汽器")
        
        # 烟气系统
        flue_gas_source = Source("烟气入口")
        flue_gas_sink = Sink("烟气出口")
        
        # 循环水
        cw_src = Source("循环水入口")
        cw_snk = Sink("循环水出口")
        
        print("[2] 组件定义完成")
        
        # 定义连接
        # 给水泵 → 高加 → 省煤器 → 水冷壁 → 过热器 → 高压缸
        c0 = Connection(feedwater_pump, "out1", hp_heater, "in2", label="给水")
        c1 = Connection(hp_heater, "out2", economizer, "in2", label="经高加")
        c2 = Connection(economizer, "out2", waterwall, "in2", label="预热水")
        c3 = Connection(waterwall, "out2", superheater, "in2", label="饱和蒸汽")
        c4 = Connection(superheater, "out2", cc, "in1", label="过热蒸汽")
        c5 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
        
        # 高压缸 → 分流 → 再热器 → 低压缸
        c6 = Connection(hp_turbine, "out1", sp_hp, "in1", label="高压缸排汽")
        c7 = Connection(sp_hp, "out1", reheater, "in2", label="主流再热")
        c8 = Connection(reheater, "out2", lp_turbine, "in1", label="再热蒸汽")
        
        # 低压缸 → 分流1 → 分流2 → 凝汽器
        c9 = Connection(lp_turbine, "out1", sp_lp, "in1", label="低压缸排汽")
        c9b = Connection(sp_lp, "out1", lp_extract, "in1", label="低压分流1")
        c10 = Connection(lp_extract, "out1", condenser, "in1", label="排汽入凝汽器")
        
        # 凝汽器 → 凝泵 → 低加 → 除氧器
        c11 = Connection(condenser, "out1", condensate_pump, "in1", label="凝结水")
        c12 = Connection(condensate_pump, "out1", lp_heater, "in2", label="经凝泵")
        c13 = Connection(lp_heater, "out2", deaerator, "in1", label="经低加")
        
        # 抽汽到高加
        ext_hp = Connection(sp_hp, "out2", hp_heater, "in1", label="高压抽汽")
        
        # 抽汽到除氧器
        ext_de = Connection(sp_lp, "out2", deaerator, "in2", label="除氧器抽汽")
        
        # 抽汽到低加
        ext_lp = Connection(lp_extract, "out2", lp_heater, "in1", label="低压抽汽")
        
        # 高加疏水回除氧器
        drain_hp = Connection(hp_heater, "out1", deaerator, "in3", label="高加疏水")
        
        # 低加疏水回除氧器（简化，不回凝汽器）
        drain_lp = Connection(lp_heater, "out1", deaerator, "in4", label="低加疏水")
        
        # 除氧器 → 给水泵
        c14 = Connection(deaerator, "out1", feedwater_pump, "in1", label="除氧后给水")
        
        nw.add_conns(
            c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c9b, c10,
            c11, c12, c13, c14,
            ext_hp, ext_de, ext_lp, drain_hp, drain_lp
        )
        
        # 烟气侧连接
        fg1 = Connection(flue_gas_source, "out1", superheater, "in1", label="烟气入炉")
        fg2 = Connection(superheater, "out1", reheater, "in1", label="烟气经过热器")
        fg3 = Connection(reheater, "out1", waterwall, "in1", label="烟气经再热器")
        fg4 = Connection(waterwall, "out1", economizer, "in1", label="烟气经水冷壁")
        fg5 = Connection(economizer, "out1", flue_gas_sink, "in1", label="烟气出口")
        nw.add_conns(fg1, fg2, fg3, fg4, fg5)
        
        # 循环水
        cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
        cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
        nw.add_conns(cw1, cw2)
        
        print("[3] 连接建立完成（共 {} 个连接）".format(len(nw.conns)))
        
        # 设置组件参数
        if mode == 'design':
            economizer.set_attr(pr1=self.params['economizer_pr1'], pr2=self.params['economizer_pr2'])
            waterwall.set_attr(pr1=self.params['waterwall_pr1'], pr2=self.params['waterwall_pr2'])
            superheater.set_attr(pr1=self.params['superheater_pr1'], pr2=self.params['superheater_pr2'])
            reheater.set_attr(pr1=self.params['reheater_pr1'], pr2=self.params['reheater_pr2'])
        else:
            economizer.set_attr(
                pr1=self.params['economizer_pr1'], pr2=self.params['economizer_pr2'],
                kA=self.params['economizer_kA']
            )
            waterwall.set_attr(
                pr1=self.params['waterwall_pr1'], pr2=self.params['waterwall_pr2'],
                kA=self.params['waterwall_kA']
            )
            superheater.set_attr(
                pr1=self.params['superheater_pr1'], pr2=self.params['superheater_pr2'],
                kA=self.params['superheater_kA']
            )
            reheater.set_attr(
                pr1=self.params['reheater_pr1'], pr2=self.params['reheater_pr2'],
                kA=self.params['reheater_kA']
            )
        
        hp_turbine.set_attr(eta_s=self.params['hp_turbine_eta'])
        lp_turbine.set_attr(eta_s=self.params['lp_turbine_eta'])
        
        hp_heater.set_attr(pr2=0.99, ttd_u=self.params['hp_heater_ttd_u'])
        lp_heater.set_attr(pr2=0.99, ttd_u=self.params['lp_heater_ttd_u'])
        
        condensate_pump.set_attr(eta_s=self.params['condensate_pump_eta'])
        feedwater_pump.set_attr(eta_s=self.params['pump_eta'])
        
        condenser.set_attr(pr1=1.0, pr2=0.98, ttd_u=5)
        
        print("[4] 组件参数设置完成")
        
        # 设置边界条件
        c0.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid={"N2": 0.7, "O2": 0.08, "CO2": 0.12, "H2O": 0.1})
        cw1.set_attr(fluid={"water": 1})
        
        fg1.set_attr(
            T=self.params['flue_gas_T_in'],
            p=self.params['flue_gas_p'],
            m=self.params['flue_gas_m']
        )
        
        if mode == 'design':
            c5.set_attr(
                p=self.params['main_steam_p'],
                T=self.params['main_steam_T'],
                m=self.params['main_steam_m']
            )
            c8.set_attr(T=self.params['reheat_T'])
        
        # 只固定一个压力参考点（凝汽器）
        c10.set_attr(p=self.params['condenser_p'])
        # 除氧器压力不固定，由抽汽压力决定
        # c14.set_attr(p=self.params['deaerator_p'])
        
        # 设置抽汽流量（使用Ref参考主蒸汽流量）
        ext_hp.set_attr(m=Ref(c5, 0.08, 0))  # 高压抽汽约8%
        ext_de.set_attr(m=Ref(c5, 0.05, 0))  # 除氧器抽汽约5%
        ext_lp.set_attr(m=Ref(c5, 0.03, 0))  # 低压抽汽约3%
        
        # 水冷壁出口为饱和蒸汽
        c3.set_attr(x=1.0)
        
        # 高压缸后压力（进入再热器的压力）
        c6.set_attr(p=self.params['reheat_p'])        
        cw1.set_attr(T=self.params['cooling_water_T_in'], p=1.2)
        # 冷却水出口温度由凝汽器ttd_u决定
        # cw2.set_attr(T=self.params['cooling_water_T_out'])
        
        print("[5] 边界条件设置完成")
        if mode == 'design':
            print(f"   主蒸汽(固定): {self.params['main_steam_p']} bar / "
                  f"{self.params['main_steam_T']}°C / {self.params['main_steam_m']} kg/s")
        else:
            print(f"   主蒸汽(预测): 由烟气和换热器kA决定")
        print(f"   烟气: {self.params['flue_gas_T_in']}°C / {self.params['flue_gas_m']} kg/s")
        print("=" * 80)
        
        self.nw = nw
        return nw
    
    def solve(self) -> bool:
        """求解模型."""
        print(f"\n开始求解 ({self.mode} 模式)...")
        print("-" * 80)
        
        try:
            self.nw.solve(mode="design")
            
            if self.nw.converged:
                print("✓ 求解成功")
                return True
            else:
                print("✗ 求解未收敛")
                return False
                
        except Exception as e:
            print(f"✗ 求解出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_design_point(self, filename='stage2_design.json'):
        """保存设计点."""
        if self.nw and self.nw.converged:
            economizer = self.nw.get_comp("省煤器")
            waterwall = self.nw.get_comp("水冷壁")
            superheater = self.nw.get_comp("过热器")
            reheater = self.nw.get_comp("再热器")
            
            design_data = {
                'economizer_kA': economizer.kA.val,
                'waterwall_kA': waterwall.kA.val,
                'superheater_kA': superheater.kA.val,
                'reheater_kA': reheater.kA.val,
            }
            
            with open(filename, 'w') as f:
                json.dump(design_data, f, indent=2)
            
            print(f"\n✓ 设计点已保存: {filename}")
            print("\n关键设计参数（kA值）：")
            print(f"  economizer_kA:  {economizer.kA.val:12.1f} kW/K")
            print(f"  waterwall_kA:   {waterwall.kA.val:12.1f} kW/K")
            print(f"  superheater_kA: {superheater.kA.val:12.1f} kW/K")
            print(f"  reheater_kA:    {reheater.kA.val:12.1f} kW/K")
            
            return design_data
    
    def load_design_point(self, filename='stage2_design.json'):
        """加载设计点."""
        with open(filename, 'r') as f:
            design_data = json.load(f)
        
        self.params.update(design_data)
        print(f"\n✓ 设计点已加载: {filename}")
        return design_data
    
    def analyze(self) -> dict:
        """详细分析."""
        if not self.nw or not self.nw.converged:
            print("✗ 网络未求解或未收敛")
            return {}
        
        print("\n" + "=" * 80)
        print("热力学分析")
        print("=" * 80)
        
        economizer = self.nw.get_comp("省煤器")
        waterwall = self.nw.get_comp("水冷壁")
        superheater = self.nw.get_comp("过热器")
        reheater = self.nw.get_comp("再热器")
        hp_turb = self.nw.get_comp("高压缸")
        lp_turb = self.nw.get_comp("低压缸")
        feedwater_pump = self.nw.get_comp("给水泵")
        condensate_pump = self.nw.get_comp("凝结水泵")
        condenser = self.nw.get_comp("凝汽器")
        hp_heater = self.nw.get_comp("高压加热器")
        lp_heater = self.nw.get_comp("低压加热器")
        
        main_steam = self.nw.get_conn("主蒸汽")
        reheat_steam = self.nw.get_conn("再热蒸汽")
        lp_exhaust = self.nw.get_conn("排汽入凝汽器")
        flue_gas_in = self.nw.get_conn("烟气入炉")
        flue_gas_out = self.nw.get_conn("烟气出口")
        feedwater = self.nw.get_conn("给水")
        condensate = self.nw.get_conn("凝结水")
        
        Q_economizer = abs(economizer.Q.val)
        Q_waterwall = abs(waterwall.Q.val)
        Q_superheater = abs(superheater.Q.val)
        Q_boiler_total = Q_economizer + Q_waterwall + Q_superheater
        Q_reheater = abs(reheater.Q.val)
        Q_total = Q_boiler_total + Q_reheater
        
        Q_hp_heater = abs(hp_heater.Q.val)
        Q_lp_heater = abs(lp_heater.Q.val)
        Q_regeneration = Q_hp_heater + Q_lp_heater
        
        P_hp = abs(hp_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_lp
        P_pump = abs(feedwater_pump.P.val) + abs(condensate_pump.P.val)
        P_net = P_turb_total - P_pump
        
        Q_condenser = abs(condenser.Q.val)
        eta_thermal = P_net / Q_total * 100 if Q_total > 0 else 0
        
        print("\n【1. 锅炉系统性能】")
        print("-" * 80)
        print(f"省煤器:       {Q_economizer:10.3f} MW  ({Q_economizer/Q_boiler_total*100:5.1f}%)")
        if hasattr(economizer, 'kA') and economizer.kA.is_set:
            print(f"              kA = {economizer.kA.val:10.1f} kW/K")
        print(f"水冷壁:       {Q_waterwall:10.3f} MW  ({Q_waterwall/Q_boiler_total*100:5.1f}%) ⭐")
        if hasattr(waterwall, 'kA') and waterwall.kA.is_set:
            print(f"              kA = {waterwall.kA.val:10.1f} kW/K")
        print(f"过热器:       {Q_superheater:10.3f} MW  ({Q_superheater/Q_boiler_total*100:5.1f}%)")
        if hasattr(superheater, 'kA') and superheater.kA.is_set:
            print(f"              kA = {superheater.kA.val:10.1f} kW/K")
        print(f"再热器:       {Q_reheater:10.3f} MW  ({Q_reheater/Q_total*100:5.1f}%)")
        if hasattr(reheater, 'kA') and reheater.kA.is_set:
            print(f"              kA = {reheater.kA.val:10.1f} kW/K")
        print(f"锅炉总吸热:   {Q_total:10.3f} MW")
        
        print(f"\n烟气参数:")
        print(f"  入口温度:   {flue_gas_in.T.val:10.2f} °C")
        print(f"  出口温度:   {flue_gas_out.T.val:10.2f} °C")
        print(f"  温降:       {flue_gas_in.T.val - flue_gas_out.T.val:10.2f} K")
        
        print("\n【2. 汽轮机系统性能】")
        print("-" * 80)
        print(f"高压缸出力:   {P_hp:10.3f} MW  ({P_hp/P_turb_total*100:5.1f}%)")
        print(f"低压缸出力:   {P_lp:10.3f} MW  ({P_lp/P_turb_total*100:5.1f}%)")
        print(f"泵耗功:       {P_pump:10.3f} MW  ({P_pump/P_turb_total*100:5.2f}%)")
        print(f"净发电功率:   {P_net:10.3f} MW")
        
        print("\n【3. 回热系统性能】")
        print("-" * 80)
        print(f"高压加热器:   {Q_hp_heater:10.3f} MW")
        print(f"低压加热器:   {Q_lp_heater:10.3f} MW")
        print(f"回热总加热量: {Q_regeneration:10.3f} MW")
        print(f"给水温升:     {feedwater.T.val - condensate.T.val:10.2f} K")
        
        print("\n【4. 循环效率】")
        print("-" * 80)
        print(f"循环热效率:   {eta_thermal:10.2f} %")
        print(f"凝汽放热:     {Q_condenser:10.3f} MW")
        
        energy_balance = abs(Q_total - (Q_condenser + P_net))
        energy_balance_pct = energy_balance / Q_total * 100 if Q_total > 0 else 0
        print(f"能量平衡误差: {energy_balance_pct:10.4f} %", end="")
        if energy_balance_pct < 0.5:
            print("  ✓")
        else:
            print("  ⚠")
        
        print("\n【5. 关键状态点】")
        print("-" * 80)
        print(f"主蒸汽:     {main_steam.p.val:7.2f} bar / {main_steam.T.val:7.2f}°C / {main_steam.m.val:7.2f} kg/s")
        print(f"再热蒸汽:   {reheat_steam.p.val:7.2f} bar / {reheat_steam.T.val:7.2f}°C / {reheat_steam.m.val:7.2f} kg/s")
        print(f"给水温度:   {feedwater.T.val:7.2f} °C")
        print(f"凝结水温度: {condensate.T.val:7.2f} °C")
        if hasattr(lp_exhaust, 'x') and lp_exhaust.x.val is not None:
            print(f"排汽干度:   {lp_exhaust.x.val:7.4f}")
        
        print("=" * 80)
        
        self.results = {
            "P_net_MW": P_net,
            "eta_thermal_percent": eta_thermal,
            "main_steam_p_bar": main_steam.p.val,
            "main_steam_T_degC": main_steam.T.val,
            "main_steam_m_kg_s": main_steam.m.val,
            "reheat_steam_T_degC": reheat_steam.T.val,
            "feedwater_T_degC": feedwater.T.val,
            "Q_total_MW": Q_total,
            "Q_regeneration_MW": Q_regeneration,
            "flue_gas_T_out_degC": flue_gas_out.T.val,
        }
        
        return self.results
    
    def predict(self, inputs: dict) -> dict:
        """预测接口."""
        self.params.update(inputs)
        self.build_network(mode='offdesign')
        
        if not self.solve():
            return {"error": "求解失败"}
        
        results = self.analyze()
        return results
    
    def calibrate(self, measured_data: dict) -> dict:
        """参数校准功能."""
        print("\n" + "=" * 80)
        print("参数校准模式")
        print("=" * 80)
        
        self.params.update({
            'flue_gas_T_in': measured_data['flue_gas_T_in'],
            'flue_gas_m': measured_data['flue_gas_m'],
            'main_steam_p': measured_data['main_steam_p'],
            'main_steam_T': measured_data['main_steam_T'],
            'main_steam_m': measured_data['main_steam_m'],
        })
        
        if 'reheat_T' in measured_data:
            self.params['reheat_T'] = measured_data['reheat_T']
        
        self.build_network(mode='design')
        
        if not self.solve():
            print("✗ 校准失败：模型未收敛")
            return {}
        
        economizer = self.nw.get_comp("省煤器")
        waterwall = self.nw.get_comp("水冷壁")
        superheater = self.nw.get_comp("过热器")
        reheater = self.nw.get_comp("再热器")
        
        calibrated_params = {
            'economizer_kA': economizer.kA.val,
            'waterwall_kA': waterwall.kA.val,
            'superheater_kA': superheater.kA.val,
            'reheater_kA': reheater.kA.val,
        }
        
        print("\n✓ 校准完成")
        print("\n校准得到的kA参数：")
        print(f"  economizer_kA:  {economizer.kA.val:12.1f} kW/K")
        print(f"  waterwall_kA:   {waterwall.kA.val:12.1f} kW/K")
        print(f"  superheater_kA: {superheater.kA.val:12.1f} kW/K")
        print(f"  reheater_kA:    {reheater.kA.val:12.1f} kW/K")
        
        if 'P_net' in measured_data:
            hp_turb = self.nw.get_comp("高压缸")
            lp_turb = self.nw.get_comp("低压缸")
            fp = self.nw.get_comp("给水泵")
            cp = self.nw.get_comp("凝结水泵")
            predicted_P = abs(hp_turb.P.val + lp_turb.P.val - fp.P.val - cp.P.val)
            error = abs(predicted_P - measured_data['P_net']) / measured_data['P_net'] * 100
            print(f"\n功率误差: {error:.2f}%")
            if error < 5:
                print("  ✓ 校准精度良好")
            else:
                print("  ⚠ 校准精度需改进")
        
        print("=" * 80)
        
        self.params.update(calibrated_params)
        return calibrated_params


def main():
    """主函数."""
    
    print("\n" + "=" * 80)
    print("阶段2：简化但稳定的高级预测模型演示")
    print("=" * 80)
    print("\n本演示分三步：")
    print("  1. 设计模式：固定主蒸汽参数，反算换热器kA")
    print("  2. 预测模式：改变烟气条件，预测系统响应")
    print("  3. 参数校准：根据实际数据重新校准kA")
    print("=" * 80)
    
    # 步骤1：设计模式
    print("\n\n### 步骤1：设计模式求解 ###\n")
    
    system = Stage2SimplifiedSystem()
    system.build_network(mode='design')
    
    if system.solve():
        design_results = system.analyze()
        design_data = system.save_design_point()
    else:
        print("\n✗ 设计模式求解失败")
        return
    
    # 步骤2：预测模式
    print("\n\n### 步骤2：预测模式求解 ###\n")
    print("场景：烟气温度降低50°C，流量降低10%...")
    
    system2 = Stage2SimplifiedSystem()
    system2.load_design_point()
    
    inputs = {
        'flue_gas_T_in': 1150,
        'flue_gas_m': 270,
    }
    
    predict_results = system2.predict(inputs)
    
    if 'error' not in predict_results:
        print("\n\n### 预测模式对比 ###")
        print("=" * 80)
        print(f"{'参数':<35} {'设计点':<18} {'预测点':<18} {'变化':<18}")
        print("-" * 80)
        
        comparisons = [
            ("主蒸汽压力 [bar]", "main_steam_p_bar"),
            ("主蒸汽温度 [°C]", "main_steam_T_degC"),
            ("主蒸汽流量 [kg/s]", "main_steam_m_kg_s"),
            ("再热蒸汽温度 [°C]", "reheat_steam_T_degC"),
            ("净发电功率 [MW]", "P_net_MW"),
            ("循环热效率 [%]", "eta_thermal_percent"),
            ("给水温度 [°C]", "feedwater_T_degC"),
            ("烟气出口温度 [°C]", "flue_gas_T_out_degC"),
        ]
        
        for name, key in comparisons:
            if key in design_results and key in predict_results:
                design_val = design_results[key]
                predict_val = predict_results[key]
                change = (predict_val - design_val) / design_val * 100 if design_val != 0 else 0
                print(f"{name:<35} {design_val:>16.2f} {predict_val:>16.2f} {change:>+16.2f}%")
        
        print("=" * 80)
    
    # 步骤3：参数校准
    print("\n\n### 步骤3：参数校准示例 ###\n")
    print("场景：使用实际测量数据重新校准kA...")
    
    system3 = Stage2SimplifiedSystem()
    
    measured_data = {
        'flue_gas_T_in': 1200,
        'flue_gas_m': 300,
        'main_steam_p': 148,
        'main_steam_T': 598,
        'main_steam_m': 102,
        'reheat_T': 595,
        'P_net': design_results['P_net_MW'],
    }
    
    calibrated_params = system3.calibrate(measured_data)
    
    if calibrated_params:
        print("\n✓ 参数校准完成，可用于后续预测")
        with open('stage2_calibrated.json', 'w') as f:
            json.dump(calibrated_params, f, indent=2)
        print("✓ 校准参数已保存: stage2_calibrated.json")
    
    print("\n\n" + "=" * 80)
    print("阶段2演示完成！")
    print("=" * 80)
    print("\n阶段2核心成果：")
    print("  ✓ 烟气侧建模（HeatExchanger + kA）")
    print("  ✓ 简化回热系统（1高加 + 除氧器 + 1低加）")
    print("  ✓ 预测功能（改变烟气条件 → 预测主蒸汽参数）")
    print("  ✓ 参数校准功能（实际数据 → 校准kA）")
    print("  ✓ 模型稳定收敛")
    print("\n与阶段1的差异：")
    print("  • 使用HeatExchanger替代SimpleHeatExchanger")
    print("  • 添加完整烟气侧建模")
    print("  • 添加回热系统提升效率")
    print("  • 提供参数校准接口")
    print("\n后续扩展方向：")
    print("  • 逐步增加回热加热器数量")
    print("  • 添加汽包系统（Drum）")
    print("  • 集成DCS数据接口")
    print("  • 开发REST API")
    print("=" * 80)


if __name__ == "__main__":
    main()
