#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工程级预测型锅炉-汽轮机系统模型 - 阶段1简化版

本版本简化了系统复杂度，专注于核心预测功能：

阶段1核心改进：
1. ✓ 换热器固定 kA 约束（而非设计模式）
2. ✓ 主蒸汽参数从"输入"变为"输出"（预测模式）
3. ✓ 添加烟气侧模型（作为热源输入）
4. ✓ 增强除氧器（简化版，带加热蒸汽入口）
5. ✓ 优化收敛性

简化措施（阶段2再细化）：
- 暂时不使用Drum组件（避免循环依赖）
- 使用直流式蒸发建模
- 简化除氧器为混合加热器

适用场景：
- 给定燃料/烟气/环境条件，预测电厂输出
- 支持在线实时计算和性能预测
"""

import sys
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


class PredictiveBoilerTurbineSystem:
    """工程级预测型锅炉-汽轮机系统（简化版）."""
    
    def __init__(self, design_params: dict = None):
        """初始化系统参数."""
        defaults = {
            # === 输入参数（烟气侧）===
            'flue_gas_T_in': 1200,       # °C
            'flue_gas_m': 150,           # kg/s
            'flue_gas_p': 1.05,          # bar
            
            # === 固定换热器参数===
            'economizer_kA': 15000,      # kW/K
            'waterwall_kA': 25000,       # kW/K
            'superheater_kA': 8000,      # kW/K
            'reheater_kA': 10000,        # kW/K
            
            # === 循环参数 ===
            'reheat_p': 30,              # bar
            'condenser_p': 0.05,         # bar
            'condenser_ttd': 5,          # K
            'cooling_water_T_in': 20,    # °C
            'cooling_water_p': 1.2,      # bar
            'deaerator_p': 3.0,          # bar
            'extraction_ratio': 0.08,    # 8%
            
            # === 设备效率 ===
            'hp_turbine_eta': 0.88,
            'lp_turbine_eta': 0.86,
            'condensate_pump_eta': 0.75,
            'feedwater_pump_eta': 0.78,
            
            # === 压降系数 ===
            'economizer_pr': 0.98,
            'waterwall_pr': 0.97,
            'superheater_pr': 0.95,
            'reheater_pr': 0.97,
            
            # === 初始估计 ===
            'main_steam_p_init': 150,
            'main_steam_T_init': 600,
            'main_steam_m_init': 100,
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
        print(f"工程级预测型锅炉-汽轮机系统（简化版） - 模式: {mode.upper()}")
        print("=" * 80)
        print("\n系统配置：")
        print("  • 详细锅炉：省煤器 → 水冷壁(蒸发) → 过热器")
        print("  • 再热系统：高压缸 → 再热器 → 低压缸")
        print("  • 凝汽系统：凝汽器 + 循环水")
        print("  • 给水系统：凝结水泵 → 除氧器 → 给水泵")
        print("  • 抽汽系统：汽轮机 → 除氧器加热")
        print("  • 烟气系统：热源输入")
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
        
        # ===================================================================
        # 定义组件
        # ===================================================================
        cc = CycleCloser("循环闭合器")
        
        # --- 锅炉系统（使用HeatExchanger支持kA和烟气侧）---
        economizer = HeatExchanger("省煤器")
        waterwall = HeatExchanger("水冷壁")
        superheater = HeatExchanger("过热器")
        reheater = HeatExchanger("再热器")
        
        # --- 汽轮机系统 ---
        hp_turbine = Turbine("高压缸")
        lp_turbine = Turbine("低压缸")
        extraction_splitter = Splitter("抽汽分流器")
        
        # --- 凝汽系统 ---
        condenser = Condenser("凝汽器")
        condensate_pump = Pump("凝结水泵")
        
        # --- 除氧器系统 ---
        deaerator = Merge("除氧器", num_in=2)
        feedwater_pump = Pump("给水泵")
        
        # --- 烟气系统 ---
        flue_gas_source = Source("烟气入口")
        flue_gas_sink = Sink("烟气出口")
        
        # --- 循环水 ---
        cw_src = Source("循环水入口")
        cw_snk = Sink("循环水出口")
        
        print("[2] 组件定义完成")
        
        # ===================================================================
        # 定义连接
        # ===================================================================
        
        # --- 主蒸汽/工质循环（直流式）---
        c0 = Connection(feedwater_pump, "out1", economizer, "in2", label="给水")
        c1 = Connection(economizer, "out2", waterwall, "in2", label="预热水")
        c2 = Connection(waterwall, "out2", superheater, "in2", label="饱和蒸汽")
        c3 = Connection(superheater, "out2", cc, "in1", label="过热器出口")
        c4 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
        
        # 高压缸 → 抽汽分流器 → 再热器 / 除氧器
        c5 = Connection(hp_turbine, "out1", extraction_splitter, "in1", label="高压缸排汽")
        c6 = Connection(extraction_splitter, "out1", reheater, "in2", label="主流再热")
        c7 = Connection(extraction_splitter, "out2", deaerator, "in1", label="抽汽加热")
        c8 = Connection(reheater, "out2", lp_turbine, "in1", label="再热蒸汽")
        
        # 低压缸 → 凝汽器 → 凝结水泵 → 除氧器
        c9 = Connection(lp_turbine, "out1", condenser, "in1", label="低压缸排汽")
        c10 = Connection(condenser, "out1", condensate_pump, "in1", label="凝结水")
        c11 = Connection(condensate_pump, "out1", deaerator, "in2", label="升压凝结水")
        c12 = Connection(deaerator, "out1", feedwater_pump, "in1", label="除氧后给水")
        
        nw.add_conns(c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12)
        
        # --- 烟气侧连接 ---
        fg1 = Connection(flue_gas_source, "out1", superheater, "in1", label="烟气入炉")
        fg2 = Connection(superheater, "out1", reheater, "in1", label="烟气经过热器")
        fg3 = Connection(reheater, "out1", waterwall, "in1", label="烟气经再热器")
        fg4 = Connection(waterwall, "out1", economizer, "in1", label="烟气经水冷壁")
        fg5 = Connection(economizer, "out1", flue_gas_sink, "in1", label="烟气出口")
        nw.add_conns(fg1, fg2, fg3, fg4, fg5)
        
        # --- 循环水 ---
        cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
        cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
        nw.add_conns(cw1, cw2)
        
        print("[3] 连接建立完成")
        
        # ===================================================================
        # 设置组件参数
        # ===================================================================
        
        if mode == 'design':
            # 设计模式：只设置压降
            economizer.set_attr(pr1=0.98, pr2=self.params['economizer_pr'])
            waterwall.set_attr(pr1=0.98, pr2=self.params['waterwall_pr'])
            superheater.set_attr(pr1=0.98, pr2=self.params['superheater_pr'])
            reheater.set_attr(pr1=0.98, pr2=self.params['reheater_pr'])
        else:
            # 仿真模式：固定 kA
            economizer.set_attr(
                pr1=0.98, pr2=self.params['economizer_pr'],
                kA=self.params['economizer_kA']
            )
            waterwall.set_attr(
                pr1=0.98, pr2=self.params['waterwall_pr'],
                kA=self.params['waterwall_kA']
            )
            superheater.set_attr(
                pr1=0.98, pr2=self.params['superheater_pr'],
                kA=self.params['superheater_kA']
            )
            reheater.set_attr(
                pr1=0.98, pr2=self.params['reheater_pr'],
                kA=self.params['reheater_kA']
            )
        
        hp_turbine.set_attr(
            eta_s=self.params['hp_turbine_eta'],
            pr=self.params['reheat_p'] / self.params['main_steam_p_init']
        )
        lp_turbine.set_attr(eta_s=self.params['lp_turbine_eta'])
        condensate_pump.set_attr(eta_s=self.params['condensate_pump_eta'])
        feedwater_pump.set_attr(eta_s=self.params['feedwater_pump_eta'])
        condenser.set_attr(pr1=1.0, pr2=0.98, ttd_u=self.params['condenser_ttd'])
        
        print("[4] 组件参数设置完成")
        
        # ===================================================================
        # 设置边界条件
        # ===================================================================
        
        c0.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid={"air": 0.77, "O2": 0.1, "CO2": 0.1, "H2O": 0.03})
        cw1.set_attr(fluid={"water": 1})
        
        # 烟气侧输入
        fg1.set_attr(
            T=self.params['flue_gas_T_in'],
            p=self.params['flue_gas_p'],
            m=self.params['flue_gas_m']
        )
        
        # 主蒸汽/工质循环
        if mode == 'design':
            # 设计模式：固定主蒸汽参数
            c4.set_attr(
                p=self.params['main_steam_p_init'],
                T=self.params['main_steam_T_init'],
                m=self.params['main_steam_m_init']
            )
        else:
            # 仿真模式：主蒸汽参数由烟气和换热器决定
            pass  # 不固定主蒸汽参数
        
        # 饱和蒸汽
        c2.set_attr(x=1.0)
        
        # 抽汽比例
        c7.set_attr(m=Ref(c4, self.params['extraction_ratio'], 0))
        
        # 再热蒸汽温度（设计模式）
        if mode == 'design':
            c8.set_attr(T=600)  # 设计点固定再热温度
        # 再热压力由高压缸的pr决定，不在此重复设置
        # c8.set_attr(p=self.params['reheat_p'])
        
        # 凝汽器压力
        c9.set_attr(p=self.params['condenser_p'])
        
        # 除氧器出口温度（近似饱和温度）
        c12.set_attr(T=133)  # 除氧器出口温度，约对应3 bar饱和温度
        
        # 给水泵出口压力 - 由主蒸汽压力和锅炉压降决定，不另外固定
        # c0.set_attr(p=165)
        
        # 循环水
        cw1.set_attr(
            T=self.params['cooling_water_T_in'],
            p=self.params['cooling_water_p']
        )
        
        print("[5] 边界条件设置完成")
        print(f"   烟气: {self.params['flue_gas_T_in']}°C / {self.params['flue_gas_m']} kg/s")
        if mode == 'design':
            print(f"   主蒸汽(固定): {self.params['main_steam_p_init']} bar / "
                  f"{self.params['main_steam_T_init']}°C / {self.params['main_steam_m_init']} kg/s")
        else:
            print(f"   主蒸汽(预测): 由烟气和换热器决定")
        print(f"   抽汽比例: {self.params['extraction_ratio']*100:.1f}%")
        print("=" * 80)
        
        self.nw = nw
        return nw
    
    def solve(self) -> bool:
        """求解模型."""
        print(f"\n开始求解 ({self.mode} 模式)...")
        print("-" * 80)
        
        try:
            self.nw.solve(mode=self.mode)
            
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
    
    def save_design_point(self, filename='boiler_turbine_stage1_design.json'):
        """保存设计点."""
        if self.nw and self.nw.converged:
            self.nw.save(filename)
            print(f"\n✓ 设计点已保存: {filename}")
            
            economizer = self.nw.get_comp("省煤器")
            waterwall = self.nw.get_comp("水冷壁")
            superheater = self.nw.get_comp("过热器")
            reheater = self.nw.get_comp("再热器")
            
            print("\n关键设计参数（用于仿真模式）：")
            print(f"  economizer_kA:  {economizer.kA.val:.1f} kW/K")
            print(f"  waterwall_kA:   {waterwall.kA.val:.1f} kW/K")
            print(f"  superheater_kA: {superheater.kA.val:.1f} kW/K")
            print(f"  reheater_kA:    {reheater.kA.val:.1f} kW/K")
            
            return {
                'economizer_kA': economizer.kA.val,
                'waterwall_kA': waterwall.kA.val,
                'superheater_kA': superheater.kA.val,
                'reheater_kA': reheater.kA.val,
            }
    
    def load_design_point(self, filename='boiler_turbine_stage1_design.json'):
        """加载设计点."""
        if self.nw:
            self.nw.load(filename)
            print(f"\n✓ 设计点已加载: {filename}")
    
    def analyze(self) -> dict:
        """详细分析."""
        if not self.nw or not self.nw.converged:
            print("✗ 网络未求解或未收敛")
            return {}
        
        print("\n" + "=" * 80)
        print("详细热力学分析")
        print("=" * 80)
        
        # 获取组件
        economizer = self.nw.get_comp("省煤器")
        waterwall = self.nw.get_comp("水冷壁")
        superheater = self.nw.get_comp("过热器")
        reheater = self.nw.get_comp("再热器")
        hp_turb = self.nw.get_comp("高压缸")
        lp_turb = self.nw.get_comp("低压缸")
        feedwater_pump = self.nw.get_comp("给水泵")
        condensate_pump = self.nw.get_comp("凝结水泵")
        condenser = self.nw.get_comp("凝汽器")
        
        # 获取连接
        main_steam = self.nw.get_conn("主蒸汽")
        reheat_steam = self.nw.get_conn("再热蒸汽")
        extraction_steam = self.nw.get_conn("抽汽加热")
        lp_exhaust = self.nw.get_conn("低压缸排汽")
        flue_gas_in = self.nw.get_conn("烟气入炉")
        flue_gas_out = self.nw.get_conn("烟气出口")
        
        # 计算
        Q_economizer = abs(economizer.Q.val)
        Q_waterwall = abs(waterwall.Q.val)
        Q_superheater = abs(superheater.Q.val)
        Q_reheater = abs(reheater.Q.val)
        Q_total = Q_economizer + Q_waterwall + Q_superheater + Q_reheater
        
        P_hp = abs(hp_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_lp
        P_pump_total = abs(feedwater_pump.P.val) + abs(condensate_pump.P.val)
        P_net = P_turb_total - P_pump_total
        
        Q_condenser = abs(condenser.Q.val)
        eta_thermal = P_net / Q_total * 100 if Q_total > 0 else 0
        
        print("\n【1. 锅炉系统性能】")
        print("-" * 80)
        print(f"省煤器:       {Q_economizer:10.3f} MW")
        print(f"水冷壁:       {Q_waterwall:10.3f} MW")
        print(f"过热器:       {Q_superheater:10.3f} MW")
        print(f"再热器:       {Q_reheater:10.3f} MW")
        print(f"锅炉总吸热:   {Q_total:10.3f} MW")
        print(f"烟气温降:     {flue_gas_in.T.val - flue_gas_out.T.val:10.2f} K")
        
        print("\n【2. 汽轮机系统性能】")
        print("-" * 80)
        print(f"高压缸出力:   {P_hp:10.3f} MW")
        print(f"低压缸出力:   {P_lp:10.3f} MW")
        print(f"泵耗功:       {P_pump_total:10.3f} MW")
        print(f"净发电功率:   {P_net:10.3f} MW")
        
        print("\n【3. 循环效率】")
        print("-" * 80)
        print(f"循环热效率:   {eta_thermal:10.2f} %")
        print(f"凝汽放热:     {Q_condenser:10.3f} MW")
        
        print("\n【4. 关键状态点】")
        print("-" * 80)
        print(f"主蒸汽:       {main_steam.p.val:.2f} bar / {main_steam.T.val:.2f}°C / {main_steam.m.val:.2f} kg/s")
        print(f"再热蒸汽:     {reheat_steam.p.val:.2f} bar / {reheat_steam.T.val:.2f}°C")
        print(f"抽汽:         {extraction_steam.m.val:.3f} kg/s ({extraction_steam.m.val/main_steam.m.val*100:.1f}%)")
        if hasattr(lp_exhaust, 'x') and lp_exhaust.x.val is not None:
            print(f"排汽干度:     {lp_exhaust.x.val:.4f}")
        print("=" * 80)
        
        self.results = {
            "P_net_MW": P_net,
            "eta_thermal_percent": eta_thermal,
            "main_steam_p_bar": main_steam.p.val,
            "main_steam_T_degC": main_steam.T.val,
            "main_steam_m_kg_s": main_steam.m.val,
            "Q_total_MW": Q_total,
            "flue_gas_T_in": flue_gas_in.T.val,
            "flue_gas_T_out": flue_gas_out.T.val,
        }
        
        return self.results


def main():
    """主函数 - 演示阶段1功能."""
    
    print("\n" + "=" * 80)
    print("工程级预测型锅炉-汽轮机系统 - 阶段1演示（简化版）")
    print("=" * 80)
    print("\n本演示分两步：")
    print("  1. 设计模式：固定主蒸汽参数，反算换热器kA")
    print("  2. 仿真模式：固定换热器kA，预测主蒸汽参数")
    print("=" * 80)
    
    # === 步骤1：设计模式 ===
    print("\n\n### 步骤1：设计模式求解 ###\n")
    
    system = PredictiveBoilerTurbineSystem()
    system.build_network(mode='design')
    
    if system.solve():
        system.analyze()
        design_kA = system.save_design_point()
    else:
        print("\n✗ 设计模式求解失败")
        return
    
    # === 步骤2：仿真模式 ===
    print("\n\n### 步骤2：仿真模式求解（预测模式） ###\n")
    print("改变烟气温度，预测主蒸汽参数变化...")
    
    system2 = PredictiveBoilerTurbineSystem(design_params=design_kA)
    system2.params['flue_gas_T_in'] = 1100  # 从1200降到1100
    
    system2.build_network(mode='offdesign')
    system2.load_design_point()
    
    if system2.solve():
        results = system2.analyze()
        
        print("\n\n### 预测模式对比 ###")
        print("=" * 80)
        print(f"{'参数':<25} {'设计点':<18} {'预测点':<18} {'变化':<18}")
        print("-" * 80)
        print(f"{'烟气温度(°C)':<25} {1200:<18.1f} {1100:<18.1f} {-100:<18.1f}")
        print(f"{'主蒸汽压力(bar)':<25} {system.results['main_steam_p_bar']:<18.2f} "
              f"{results['main_steam_p_bar']:<18.2f} "
              f"{results['main_steam_p_bar']-system.results['main_steam_p_bar']:<18.2f}")
        print(f"{'主蒸汽温度(°C)':<25} {system.results['main_steam_T_degC']:<18.2f} "
              f"{results['main_steam_T_degC']:<18.2f} "
              f"{results['main_steam_T_degC']-system.results['main_steam_T_degC']:<18.2f}")
        print(f"{'主蒸汽流量(kg/s)':<25} {system.results['main_steam_m_kg_s']:<18.2f} "
              f"{results['main_steam_m_kg_s']:<18.2f} "
              f"{results['main_steam_m_kg_s']-system.results['main_steam_m_kg_s']:<18.2f}")
        print(f"{'净功率(MW)':<25} {system.results['P_net_MW']:<18.2f} "
              f"{results['P_net_MW']:<18.2f} "
              f"{results['P_net_MW']-system.results['P_net_MW']:<18.2f}")
        print(f"{'热效率(%)':<25} {system.results['eta_thermal_percent']:<18.2f} "
              f"{results['eta_thermal_percent']:<18.2f} "
              f"{results['eta_thermal_percent']-system.results['eta_thermal_percent']:<18.2f}")
        print("=" * 80)
        
        print("\n✓ 阶段1完成！模型已成功从设计模式转为预测模式。")
        print("\n核心成果：")
        print("  ✓ 换热器固定kA约束")
        print("  ✓ 主蒸汽参数可预测")
        print("  ✓ 烟气侧作为输入")
        print("  ✓ 抽汽除氧系统")
        print("  ✓ 模型收敛稳定")
    else:
        print("\n✗ 仿真模式求解失败")


if __name__ == "__main__":
    main()
