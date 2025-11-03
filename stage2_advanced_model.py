#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2：高级工程预测型锅炉-汽轮机系统模型

核心改进（阶段2完成项）：
✓ 1. 烟气侧建模：使用HeatExchanger + kA参数
✓ 2. 多级回热系统：3级高压加热器 + 除氧器 + 3级低压加热器
✓ 3. 参数校准功能：根据实际数据自动校准kA
✓ 4. 工程完善：汽包系统、多级泵、抽汽系统
✓ 5. 预测能力增强：主蒸汽压力/温度可预测

系统配置：
- 锅炉系统：省煤器 → 汽包 → 水冷壁 → 汽包 → 过热器（带烟气侧）
- 再热系统：高压缸 → 再热器 → 中压缸 → 低压缸
- 回热系统：3级高压加热器 + 除氧器 + 3级低压加热器
- 抽汽系统：7级抽汽用于回热加热
- 凝汽系统：凝汽器 + 循环水

适用场景：
- 给定烟气条件（温度、流量、成分），预测电厂输出
- 在线性能监测和优化
- 参数校准和模型适应
- 变工况分析和诊断
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
    Drum,
)
from tespy.connections import Connection, Ref


class AdvancedBoilerTurbineSystem:
    """阶段2：高级工程预测型锅炉-汽轮机系统."""
    
    def __init__(self, design_params: dict = None):
        """初始化系统参数.
        
        Parameters
        ----------
        design_params : dict, optional
            设计参数字典
        """
        defaults = {
            # === 设计点参数（用于首次design求解）===
            'main_steam_p': 150,           # bar
            'main_steam_T': 600,           # °C
            'main_steam_m': 100,           # kg/s
            'reheat_p': 30,                # bar
            'reheat_T': 600,               # °C
            'condenser_p': 0.05,           # bar
            
            # === 烟气参数 ===
            'flue_gas_T_in': 1200,         # °C
            'flue_gas_m': 300,             # kg/s
            'flue_gas_p': 1.05,            # bar
            
            # === 冷却水参数 ===
            'cooling_water_T_in': 20,      # °C
            'cooling_water_T_out': 32,     # °C
            
            # === 回热系统参数 ===
            'hp_heater1_p': 80,            # bar - 高压加热器1
            'hp_heater2_p': 50,            # bar - 高压加热器2
            'hp_heater3_p': 35,            # bar - 高压加热器3
            'deaerator_p': 3.0,            # bar - 除氧器
            'lp_heater1_p': 1.5,           # bar - 低压加热器1
            'lp_heater2_p': 0.5,           # bar - 低压加热器2
            'lp_heater3_p': 0.15,          # bar - 低压加热器3
            
            # === 设备效率 ===
            'hp_turbine_eta': 0.88,
            'ip_turbine_eta': 0.90,
            'lp_turbine_eta': 0.86,
            'condensate_pump_eta': 0.75,
            'feedwater_pump_eta': 0.78,
            'booster_pump_eta': 0.76,
            
            # === 压降系数 ===
            'economizer_pr1': 0.98,        # 烟气侧
            'economizer_pr2': 0.98,        # 水侧
            'waterwall_pr1': 0.98,
            'superheater_pr1': 0.98,
            'superheater_pr2': 0.95,
            'reheater_pr1': 0.98,
            'reheater_pr2': 0.97,
            'heater_pr_hot': 0.98,         # 加热器蒸汽侧
            'heater_pr_cold': 0.99,        # 加热器水侧
            
            # === 加热器端差 ===
            'hp_heater_ttd_u': 3,          # K - 上端差
            'lp_heater_ttd_u': 5,          # K - 上端差
            'condenser_ttd_u': 5,          # K - 凝汽器端差
            
            # === 换热器kA（从设计点反算，初值为None）===
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
        """构建网络模型.
        
        Parameters
        ----------
        mode : str
            'design' - 设计模式（固定主蒸汽参数，反算kA）
            'offdesign' - 仿真模式（固定kA，预测主蒸汽参数）
        """
        self.mode = mode
        
        print("\n" + "=" * 80)
        print(f"阶段2：高级工程预测型锅炉-汽轮机系统 - 模式: {mode.upper()}")
        print("=" * 80)
        print("\n系统配置：")
        print("  • 锅炉系统：省煤器 → 汽包 → 水冷壁 → 汽包 → 过热器")
        print("  • 再热系统：高压缸 → 再热器 → 中压缸 → 低压缸")
        print("  • 回热系统：3级高压加热器 + 除氧器 + 3级低压加热器")
        print("  • 烟气系统：完整烟气侧建模（HeatExchanger + kA）")
        print("  • 抽汽系统：7级抽汽用于回热加热")
        if mode == 'design':
            print("  • 模式：设计模式（反算换热器kA参数）")
        else:
            print("  • 模式：预测模式（固定kA，预测主蒸汽参数）")
        print("=" * 80)
        
        # 创建网络
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
        
        # 锅炉系统（带烟气侧）
        economizer = HeatExchanger("省煤器")
        drum = Drum("汽包")
        waterwall = HeatExchanger("水冷壁")
        superheater = HeatExchanger("过热器")
        reheater = HeatExchanger("再热器")
        
        # 汽轮机系统（高中低压三缸）
        hp_turbine = Turbine("高压缸")
        ip_turbine = Turbine("中压缸")
        lp_turbine = Turbine("低压缸")
        
        # 抽汽分流器（7级抽汽）
        sp1 = Splitter("抽汽1-高加1")   # 高压缸后
        sp2 = Splitter("抽汽2-高加2")
        sp3 = Splitter("抽汽3-高加3")
        sp4 = Splitter("抽汽4-除氧器")  # 中压缸后
        sp5 = Splitter("抽汽5-低加1")   # 低压缸中部
        sp6 = Splitter("抽汽6-低加2")
        sp7 = Splitter("抽汽7-低加3")
        
        # 高压加热器（3级）
        hp_heater1 = HeatExchanger("高压加热器1")
        hp_heater2 = HeatExchanger("高压加热器2")
        hp_heater3 = HeatExchanger("高压加热器3")
        
        # 除氧器（混合式加热器，3个入口：抽汽、高加疏水、凝结水）
        deaerator = Merge("除氧器", num_in=3)
        
        # 低压加热器（3级）
        lp_heater1 = HeatExchanger("低压加热器1")
        lp_heater2 = HeatExchanger("低压加热器2")
        lp_heater3 = HeatExchanger("低压加热器3")
        
        # 疏水泵和回收系统
        hp_drain_merge1 = Merge("高加1疏水")
        hp_drain_merge2 = Merge("高加2疏水")
        
        lp_drain_merge1 = Merge("低加1疏水")
        lp_drain_merge2 = Merge("低加2疏水")
        
        # 泵系统
        condensate_pump = Pump("凝结水泵")
        booster_pump = Pump("升压泵")
        feedwater_pump = Pump("给水泵")
        
        # 凝汽系统
        condenser_mix = Merge("凝汽器入口混合", num_in=2)
        condenser = Condenser("凝汽器")
        
        # 烟气系统
        flue_gas_source = Source("烟气入口")
        flue_gas_sink = Sink("烟气出口")
        
        # 循环水
        cw_src = Source("循环水入口")
        cw_snk = Sink("循环水出口")
        
        print("[2] 组件定义完成")
        
        # ===================================================================
        # 定义连接
        # ===================================================================
        
        # --- 主蒸汽/工质循环 ---
        # 给水泵 → 高加1 → 高加2 → 高加3 → 省煤器 → 汽包
        c0 = Connection(feedwater_pump, "out1", hp_heater1, "in2", label="给水主路")
        c1 = Connection(hp_heater1, "out2", hp_heater2, "in2", label="经高加1")
        c2 = Connection(hp_heater2, "out2", hp_heater3, "in2", label="经高加2")
        c3 = Connection(hp_heater3, "out2", economizer, "in2", label="经高加3")
        c4 = Connection(economizer, "out2", drum, "in1", label="预热水")
        
        # 汽包循环：汽包 → 水冷壁 → 汽包
        c5 = Connection(drum, "out1", waterwall, "in2", label="下降管")
        c6 = Connection(waterwall, "out2", drum, "in2", label="上升管")
        
        # 汽包 → 过热器 → 高压缸
        c7 = Connection(drum, "out2", superheater, "in2", label="饱和蒸汽")
        c8 = Connection(superheater, "out2", cc, "in1", label="过热蒸汽")
        c9 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
        
        # 高压缸 → 抽汽1 → 抽汽2 → 抽汽3 → 再热器
        c10 = Connection(hp_turbine, "out1", sp1, "in1", label="高压缸排汽")
        c11 = Connection(sp1, "out1", sp2, "in1", label="经抽汽1")
        c12 = Connection(sp2, "out1", sp3, "in1", label="经抽汽2")
        c13 = Connection(sp3, "out1", reheater, "in2", label="主流再热")
        
        # 再热器 → 中压缸 → 抽汽4
        c14 = Connection(reheater, "out2", ip_turbine, "in1", label="再热蒸汽")
        c15 = Connection(ip_turbine, "out1", sp4, "in1", label="中压缸排汽")
        
        # 抽汽4 → 低压缸 → 抽汽5 → 抽汽6 → 抽汽7 → 凝汽器
        c16 = Connection(sp4, "out1", lp_turbine, "in1", label="入低压缸")
        c17 = Connection(lp_turbine, "out1", sp5, "in1", label="低压缸中段1")
        c18 = Connection(sp5, "out1", sp6, "in1", label="低压缸中段2")
        c19 = Connection(sp6, "out1", sp7, "in1", label="低压缸中段3")
        c20 = Connection(sp7, "out1", condenser_mix, "in1", label="低压缸排汽")
        
        # 抽汽到各加热器
        ext1 = Connection(sp1, "out2", hp_heater1, "in1", label="抽汽到高加1")
        ext2 = Connection(sp2, "out2", hp_heater2, "in1", label="抽汽到高加2")
        ext3 = Connection(sp3, "out2", hp_heater3, "in1", label="抽汽到高加3")
        ext4 = Connection(sp4, "out2", deaerator, "in1", label="抽汽到除氧器")
        ext5 = Connection(sp5, "out2", lp_heater1, "in1", label="抽汽到低加1")
        ext6 = Connection(sp6, "out2", lp_heater2, "in1", label="抽汽到低加2")
        ext7 = Connection(sp7, "out2", lp_heater3, "in1", label="抽汽到低加3")
        
        # 高压加热器疏水系统（逐级回流）
        hpd1 = Connection(hp_heater1, "out1", hp_drain_merge1, "in1", label="高加1疏水")
        hpd2 = Connection(hp_heater2, "out1", hp_drain_merge1, "in2", label="高加2疏水")
        hpd3 = Connection(hp_drain_merge1, "out1", hp_drain_merge2, "in1", label="高压疏水合并1")
        hpd4 = Connection(hp_heater3, "out1", hp_drain_merge2, "in2", label="高加3疏水")
        hpd5 = Connection(hp_drain_merge2, "out1", deaerator, "in2", label="疏水入除氧器")
        
        # 凝汽器 → 凝结水泵 → 低加3 → 低加2 → 低加1 → 升压泵 → 除氧器
        c21 = Connection(condenser, "out1", condensate_pump, "in1", label="凝结水")
        c22 = Connection(condensate_pump, "out1", lp_heater3, "in2", label="经凝泵")
        c23 = Connection(lp_heater3, "out2", lp_heater2, "in2", label="经低加3")
        c24 = Connection(lp_heater2, "out2", lp_heater1, "in2", label="经低加2")
        c25 = Connection(lp_heater1, "out2", booster_pump, "in1", label="经低加1")
        c26 = Connection(booster_pump, "out1", deaerator, "in3", label="入除氧器")
        
        # 低压加热器疏水系统（逐级回流到凝汽器）
        lpd1 = Connection(lp_heater1, "out1", lp_drain_merge1, "in1", label="低加1疏水")
        lpd2 = Connection(lp_heater2, "out1", lp_drain_merge1, "in2", label="低加2疏水")
        lpd3 = Connection(lp_drain_merge1, "out1", lp_drain_merge2, "in1", label="低压疏水合并1")
        lpd4 = Connection(lp_heater3, "out1", lp_drain_merge2, "in2", label="低加3疏水")
        lpd5 = Connection(lp_drain_merge2, "out1", condenser_mix, "in2", label="疏水回凝汽器")
        
        # 凝汽器混合 → 凝汽器
        c20b = Connection(condenser_mix, "out1", condenser, "in1", label="凝汽器入口")
        
        # 除氧器 → 给水泵
        c27 = Connection(deaerator, "out1", feedwater_pump, "in1", label="除氧后给水")
        
        nw.add_conns(
            c0, c1, c2, c3, c4, c5, c6, c7, c8, c9,
            c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c20b,
            c21, c22, c23, c24, c25, c26, c27,
            ext1, ext2, ext3, ext4, ext5, ext6, ext7,
            hpd1, hpd2, hpd3, hpd4, hpd5,
            lpd1, lpd2, lpd3, lpd4, lpd5
        )
        
        # --- 烟气侧连接 ---
        # 烟气路径：Source → 过热器 → 再热器 → 水冷壁 → 省煤器 → Sink
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
        
        print("[3] 连接建立完成（共 {} 个连接）".format(len(nw.conns)))
        
        # ===================================================================
        # 设置组件参数
        # ===================================================================
        
        # --- 锅炉换热器 ---
        if mode == 'design':
            economizer.set_attr(
                pr1=self.params['economizer_pr1'],
                pr2=self.params['economizer_pr2']
            )
            waterwall.set_attr(pr1=self.params['waterwall_pr1'])
            superheater.set_attr(
                pr1=self.params['superheater_pr1'],
                pr2=self.params['superheater_pr2']
            )
            reheater.set_attr(
                pr1=self.params['reheater_pr1'],
                pr2=self.params['reheater_pr2']
            )
        else:
            # 仿真模式：固定kA
            economizer.set_attr(
                pr1=self.params['economizer_pr1'],
                pr2=self.params['economizer_pr2'],
                kA=self.params['economizer_kA']
            )
            waterwall.set_attr(
                pr1=self.params['waterwall_pr1'],
                kA=self.params['waterwall_kA']
            )
            superheater.set_attr(
                pr1=self.params['superheater_pr1'],
                pr2=self.params['superheater_pr2'],
                kA=self.params['superheater_kA']
            )
            reheater.set_attr(
                pr1=self.params['reheater_pr1'],
                pr2=self.params['reheater_pr2'],
                kA=self.params['reheater_kA']
            )
        
        # --- 汽轮机 ---
        hp_turbine.set_attr(eta_s=self.params['hp_turbine_eta'])
        ip_turbine.set_attr(eta_s=self.params['ip_turbine_eta'])
        lp_turbine.set_attr(eta_s=self.params['lp_turbine_eta'])
        
        # --- 回热加热器 ---
        hp_heater1.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['hp_heater_ttd_u']
        )
        hp_heater2.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['hp_heater_ttd_u']
        )
        hp_heater3.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['hp_heater_ttd_u']
        )
        
        lp_heater1.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['lp_heater_ttd_u']
        )
        lp_heater2.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['lp_heater_ttd_u']
        )
        lp_heater3.set_attr(
            pr2=self.params['heater_pr_cold'],
            ttd_u=self.params['lp_heater_ttd_u']
        )
        
        # --- 泵 ---
        condensate_pump.set_attr(eta_s=self.params['condensate_pump_eta'])
        booster_pump.set_attr(eta_s=self.params['booster_pump_eta'])
        feedwater_pump.set_attr(eta_s=self.params['feedwater_pump_eta'])
        
        # --- 凝汽器 ---
        condenser.set_attr(pr1=1.0, pr2=0.98, ttd_u=self.params['condenser_ttd_u'])
        
        print("[4] 组件参数设置完成")
        
        # ===================================================================
        # 设置边界条件
        # ===================================================================
        
        # --- 流体定义 ---
        c0.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid={"N2": 0.7, "O2": 0.08, "CO2": 0.12, "H2O": 0.1})
        cw1.set_attr(fluid={"water": 1})
        
        # --- 烟气侧输入 ---
        fg1.set_attr(
            T=self.params['flue_gas_T_in'],
            p=self.params['flue_gas_p'],
            m=self.params['flue_gas_m']
        )
        
        # --- 主蒸汽参数 ---
        if mode == 'design':
            # 设计模式：固定主蒸汽参数
            c9.set_attr(
                p=self.params['main_steam_p'],
                T=self.params['main_steam_T'],
                m=self.params['main_steam_m']
            )
            c14.set_attr(T=self.params['reheat_T'])
        else:
            # 仿真模式：主蒸汽参数由烟气决定
            pass
        
        # --- 汽包出口（饱和蒸汽）---
        c7.set_attr(x=1.0)
        
        # --- 抽汽压力 ---
        ext1.set_attr(p0=self.params['hp_heater1_p'])
        ext2.set_attr(p0=self.params['hp_heater2_p'])
        ext3.set_attr(p0=self.params['hp_heater3_p'])
        ext4.set_attr(p0=self.params['deaerator_p'])
        ext5.set_attr(p0=self.params['lp_heater1_p'])
        ext6.set_attr(p0=self.params['lp_heater2_p'])
        ext7.set_attr(p0=self.params['lp_heater3_p'])
        
        # --- 凝汽器压力 ---
        c20.set_attr(p=self.params['condenser_p'])
        
        # --- 除氧器压力 ---
        c27.set_attr(p=self.params['deaerator_p'])
        
        # --- 循环水 ---
        cw1.set_attr(
            T=self.params['cooling_water_T_in'],
            p=1.2
        )
        cw2.set_attr(T=self.params['cooling_water_T_out'])
        
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
        
        # 获取组件
        economizer = self.nw.get_comp("省煤器")
        waterwall = self.nw.get_comp("水冷壁")
        superheater = self.nw.get_comp("过热器")
        reheater = self.nw.get_comp("再热器")
        hp_turb = self.nw.get_comp("高压缸")
        ip_turb = self.nw.get_comp("中压缸")
        lp_turb = self.nw.get_comp("低压缸")
        feedwater_pump = self.nw.get_comp("给水泵")
        booster_pump = self.nw.get_comp("升压泵")
        condensate_pump = self.nw.get_comp("凝结水泵")
        condenser = self.nw.get_comp("凝汽器")
        
        hp_heater1 = self.nw.get_comp("高压加热器1")
        hp_heater2 = self.nw.get_comp("高压加热器2")
        hp_heater3 = self.nw.get_comp("高压加热器3")
        lp_heater1 = self.nw.get_comp("低压加热器1")
        lp_heater2 = self.nw.get_comp("低压加热器2")
        lp_heater3 = self.nw.get_comp("低压加热器3")
        
        # 获取连接
        main_steam = self.nw.get_conn("主蒸汽")
        reheat_steam = self.nw.get_conn("再热蒸汽")
        lp_exhaust = self.nw.get_conn("低压缸排汽")
        flue_gas_in = self.nw.get_conn("烟气入炉")
        flue_gas_out = self.nw.get_conn("烟气出口")
        feedwater = self.nw.get_conn("给水主路")
        condensate = self.nw.get_conn("凝结水")
        
        # 计算
        Q_economizer = abs(economizer.Q.val)
        Q_waterwall = abs(waterwall.Q.val)
        Q_superheater = abs(superheater.Q.val)
        Q_boiler_total = Q_economizer + Q_waterwall + Q_superheater
        Q_reheater = abs(reheater.Q.val)
        Q_total = Q_boiler_total + Q_reheater
        
        Q_hp_heater1 = abs(hp_heater1.Q.val)
        Q_hp_heater2 = abs(hp_heater2.Q.val)
        Q_hp_heater3 = abs(hp_heater3.Q.val)
        Q_lp_heater1 = abs(lp_heater1.Q.val)
        Q_lp_heater2 = abs(lp_heater2.Q.val)
        Q_lp_heater3 = abs(lp_heater3.Q.val)
        Q_regeneration = Q_hp_heater1 + Q_hp_heater2 + Q_hp_heater3 + Q_lp_heater1 + Q_lp_heater2 + Q_lp_heater3
        
        P_hp = abs(hp_turb.P.val)
        P_ip = abs(ip_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_ip + P_lp
        P_pump = abs(feedwater_pump.P.val) + abs(booster_pump.P.val) + abs(condensate_pump.P.val)
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
        print(f"中压缸出力:   {P_ip:10.3f} MW  ({P_ip/P_turb_total*100:5.1f}%)")
        print(f"低压缸出力:   {P_lp:10.3f} MW  ({P_lp/P_turb_total*100:5.1f}%)")
        print(f"泵耗功:       {P_pump:10.3f} MW  ({P_pump/P_turb_total*100:5.2f}%)")
        print(f"净发电功率:   {P_net:10.3f} MW")
        
        print("\n【3. 回热系统性能】")
        print("-" * 80)
        print(f"高压加热器1:  {Q_hp_heater1:10.3f} MW")
        print(f"高压加热器2:  {Q_hp_heater2:10.3f} MW")
        print(f"高压加热器3:  {Q_hp_heater3:10.3f} MW")
        print(f"低压加热器1:  {Q_lp_heater1:10.3f} MW")
        print(f"低压加热器2:  {Q_lp_heater2:10.3f} MW")
        print(f"低压加热器3:  {Q_lp_heater3:10.3f} MW")
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
        print(f"主蒸汽:   {main_steam.p.val:7.2f} bar / {main_steam.T.val:7.2f}°C / {main_steam.m.val:7.2f} kg/s")
        print(f"再热蒸汽: {reheat_steam.p.val:7.2f} bar / {reheat_steam.T.val:7.2f}°C / {reheat_steam.m.val:7.2f} kg/s")
        print(f"给水温度: {feedwater.T.val:7.2f} °C")
        print(f"凝结水温度: {condensate.T.val:7.2f} °C")
        if hasattr(lp_exhaust, 'x') and lp_exhaust.x.val is not None:
            print(f"排汽干度: {lp_exhaust.x.val:7.4f}")
        
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
        """预测接口.
        
        Parameters
        ----------
        inputs : dict
            输入参数，包含：
            - flue_gas_T_in: 烟气入口温度 [°C]
            - flue_gas_m: 烟气流量 [kg/s]
            - condenser_p: 凝汽器压力 [bar] (可选)
            - cooling_water_T_in: 冷却水温度 [°C] (可选)
        
        Returns
        -------
        outputs : dict
            预测结果
        """
        # 更新参数
        self.params.update(inputs)
        
        # 构建网络
        self.build_network(mode='offdesign')
        
        # 求解
        if not self.solve():
            return {"error": "求解失败"}
        
        # 分析
        results = self.analyze()
        
        return results
    
    def calibrate(self, measured_data: dict) -> dict:
        """参数校准功能.
        
        Parameters
        ----------
        measured_data : dict
            实际测量数据，包含：
            - flue_gas_T_in: 烟气入口温度 [°C]
            - flue_gas_m: 烟气流量 [kg/s]
            - main_steam_p: 主蒸汽压力 [bar]
            - main_steam_T: 主蒸汽温度 [°C]
            - main_steam_m: 主蒸汽流量 [kg/s]
            - reheat_T: 再热蒸汽温度 [°C] (可选)
            - P_net: 净发电功率 [MW] (可选)
        
        Returns
        -------
        calibrated_params : dict
            校准后的kA参数
        """
        print("\n" + "=" * 80)
        print("参数校准模式")
        print("=" * 80)
        
        # 更新参数
        self.params.update({
            'flue_gas_T_in': measured_data['flue_gas_T_in'],
            'flue_gas_m': measured_data['flue_gas_m'],
            'main_steam_p': measured_data['main_steam_p'],
            'main_steam_T': measured_data['main_steam_T'],
            'main_steam_m': measured_data['main_steam_m'],
        })
        
        if 'reheat_T' in measured_data:
            self.params['reheat_T'] = measured_data['reheat_T']
        
        # 运行设计模式反算kA
        self.build_network(mode='design')
        
        if not self.solve():
            print("✗ 校准失败：模型未收敛")
            return {}
        
        # 提取kA值
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
        
        # 验证校准效果
        if 'P_net' in measured_data:
            predicted_P = abs(self.nw.get_comp("高压缸").P.val + 
                            self.nw.get_comp("中压缸").P.val + 
                            self.nw.get_comp("低压缸").P.val -
                            self.nw.get_comp("给水泵").P.val -
                            self.nw.get_comp("升压泵").P.val -
                            self.nw.get_comp("凝结水泵").P.val)
            error = abs(predicted_P - measured_data['P_net']) / measured_data['P_net'] * 100
            print(f"\n功率误差: {error:.2f}%")
            if error < 5:
                print("  ✓ 校准精度良好")
            else:
                print("  ⚠ 校准精度需改进")
        
        print("=" * 80)
        
        # 更新参数
        self.params.update(calibrated_params)
        
        return calibrated_params


def main():
    """主函数 - 演示阶段2功能."""
    
    print("\n" + "=" * 80)
    print("阶段2：高级工程预测型锅炉-汽轮机系统演示")
    print("=" * 80)
    print("\n本演示分三步：")
    print("  1. 设计模式：固定主蒸汽参数，反算换热器kA")
    print("  2. 预测模式：改变烟气条件，预测系统响应")
    print("  3. 参数校准：根据实际数据重新校准kA")
    print("=" * 80)
    
    # === 步骤1：设计模式 ===
    print("\n\n### 步骤1：设计模式求解 ###\n")
    
    system = AdvancedBoilerTurbineSystem()
    system.build_network(mode='design')
    
    if system.solve():
        design_results = system.analyze()
        design_data = system.save_design_point()
    else:
        print("\n✗ 设计模式求解失败")
        return
    
    # === 步骤2：预测模式 ===
    print("\n\n### 步骤2：预测模式求解 ###\n")
    print("场景：烟气温度降低50°C，流量降低10%...")
    
    system2 = AdvancedBoilerTurbineSystem()
    
    # 加载设计点kA
    system2.load_design_point()
    
    # 改变烟气条件
    inputs = {
        'flue_gas_T_in': 1150,  # 降低50°C
        'flue_gas_m': 270,      # 降低10%
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
    
    # === 步骤3：参数校准（可选）===
    print("\n\n### 步骤3：参数校准示例 ###\n")
    print("场景：使用实际测量数据重新校准kA...")
    
    system3 = AdvancedBoilerTurbineSystem()
    
    # 模拟实际测量数据（基于设计点稍有偏差）
    measured_data = {
        'flue_gas_T_in': 1200,
        'flue_gas_m': 300,
        'main_steam_p': 148,    # 实际测量值与设计值略有偏差
        'main_steam_T': 598,
        'main_steam_m': 102,
        'reheat_T': 595,
        'P_net': design_results['P_net_MW'],
    }
    
    calibrated_params = system3.calibrate(measured_data)
    
    if calibrated_params:
        print("\n✓ 参数校准完成，可用于后续预测")
        
        # 保存校准后的参数
        with open('stage2_calibrated.json', 'w') as f:
            json.dump(calibrated_params, f, indent=2)
        print("✓ 校准参数已保存: stage2_calibrated.json")
    
    print("\n\n" + "=" * 80)
    print("阶段2演示完成！")
    print("=" * 80)
    print("\n阶段2核心成果：")
    print("  ✓ 烟气侧建模（HeatExchanger + kA）")
    print("  ✓ 多级回热系统（7级抽汽 + 6个加热器）")
    print("  ✓ 预测功能（改变烟气条件 → 预测主蒸汽参数）")
    print("  ✓ 参数校准功能（实际数据 → 校准kA）")
    print("  ✓ 工程完善（汽包、多级泵、完整循环）")
    print("\n下一步：")
    print("  • 集成DCS数据接口")
    print("  • 开发REST API")
    print("  • 实现在线监控和报警")
    print("  • 添加动态响应建模")
    print("=" * 80)


if __name__ == "__main__":
    main()
