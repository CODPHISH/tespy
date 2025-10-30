#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工程级预测型锅炉-汽轮机系统模型 - 阶段1：结构完善与仿真化

本模型从设计型仿真改造为工程型预测模型：

阶段1核心改进：
1. 换热器固定 kA 或 ttd 约束（而非设计模式）
2. 主蒸汽参数从"输入"变为"输出"（预测模式）
3. 添加汽包（Drum）模型实现汽水分离
4. 增强除氧器（带加热蒸汽入口）
5. 添加烟气侧模型（作为热源输入）
6. 优化收敛性

适用场景：
- 给定燃料/烟气/环境条件，预测电厂输出
- 支持在线实时计算和性能预测
- 为后续参数校准、控制集成奠定基础
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
    SimpleHeatExchanger,
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


class PredictiveBoilerTurbineSystem:
    """工程级预测型锅炉-汽轮机系统."""
    
    def __init__(self, design_params: dict = None):
        """初始化系统参数.
        
        Parameters
        ----------
        design_params : dict, optional
            设计参数字典，包含：
            
            **预测模式输入（烟气/燃料侧）：**
            - flue_gas_T_in: 烟气入口温度 [°C]
            - flue_gas_m: 烟气质量流量 [kg/s]
            
            **固定设计参数（换热器）：**
            - economizer_kA: 省煤器传热系数×面积 [kW/K]
            - waterwall_kA: 水冷壁传热系数×面积 [kW/K]
            - superheater_kA: 过热器传热系数×面积 [kW/K]
            - reheater_kA: 再热器传热系数×面积 [kW/K]
            
            **其他边界条件：**
            - reheat_p: 再热压力 [bar]
            - condenser_p: 凝汽器压力 [bar]
            - condenser_ttd: 凝汽器端差 [K]
            - cooling_water_T_in: 冷却水入口温度 [°C]
            - deaerator_p: 除氧器压力 [bar]
            - extraction_ratio: 抽汽比例 (0-1)
            
            **设备效率：**
            - hp_turbine_eta: 高压缸等熵效率
            - lp_turbine_eta: 低压缸等熵效率
            - pump_eta: 泵效率
            - condensate_pump_eta: 凝结水泵效率
        """
        # 默认参数（基于典型300MW机组）
        defaults = {
            # === 输入参数（烟气侧）===
            'flue_gas_T_in': 1200,       # °C, 锅炉炉膛出口烟温
            'flue_gas_m': 150,           # kg/s, 烟气流量
            'flue_gas_p': 1.05,          # bar, 烟气压力
            
            # === 固定换热器参数（从设计点反算得到）===
            # 注意：首次运行时这些值需要从设计模式反算
            # 这里给出初始估计值
            'economizer_kA': 15000,      # kW/K (估计)
            'waterwall_kA': 25000,       # kW/K (估计，主要吸热段)
            'superheater_kA': 8000,      # kW/K (估计)
            'reheater_kA': 10000,        # kW/K (估计)
            
            # === 循环参数 ===
            'reheat_p': 30,              # bar
            'condenser_p': 0.05,         # bar (高真空)
            'condenser_ttd': 5,          # K (端差)
            'cooling_water_T_in': 20,    # °C
            'cooling_water_p': 1.2,      # bar
            'deaerator_p': 3.0,          # bar (0.3 MPa)
            'extraction_ratio': 0.08,    # 抽汽比例 8%
            
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
            'deaerator_pr': 0.99,
            
            # === 初始估计（用于求解器初值）===
            'main_steam_p_init': 150,    # bar
            'main_steam_T_init': 600,    # °C
            'main_steam_m_init': 100,    # kg/s
        }
        
        if design_params:
            defaults.update(design_params)
        
        self.params = defaults
        self.nw = None
        self.results = {}
        self.mode = 'design'  # 'design' 或 'offdesign'
    
    def build_network(self, mode='design') -> Network:
        """构建网络模型.
        
        Parameters
        ----------
        mode : str
            'design' - 设计模式（用于首次求解，反算换热器参数）
            'offdesign' - 仿真模式（固定换热器参数，预测主蒸汽）
        """
        self.mode = mode
        
        print("\n" + "=" * 80)
        print(f"工程级预测型锅炉-汽轮机系统 - 模式: {mode.upper()}")
        print("=" * 80)
        print("\n系统配置：")
        print("  • 详细锅炉：省煤器 → 汽包 → 水冷壁 → 汽包 → 过热器")
        print("  • 再热系统：高压缸 → 再热器 → 低压缸")
        print("  • 凝汽系统：凝汽器 + 循环水")
        print("  • 给水系统：凝结水泵 → 除氧器 → 给水泵")
        print("  • 抽汽系统：汽轮机 → 除氧器加热")
        print("  • 烟气系统：热源输入")
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
        
        # --- 锅炉系统 ---
        # 使用 HeatExchanger 以支持 kA 参数和烟气侧建模
        economizer = HeatExchanger("省煤器")
        waterwall = HeatExchanger("水冷壁")
        superheater = HeatExchanger("过热器")
        reheater = HeatExchanger("再热器")
        
        # 汽包（汽水分离）
        drum = Drum("汽包")
        
        # --- 汽轮机系统 ---
        hp_turbine = Turbine("高压缸")
        lp_turbine = Turbine("低压缸")
        extraction_splitter = Splitter("抽汽分流器")
        
        # --- 凝汽系统 ---
        condenser = Condenser("凝汽器")
        condensate_pump = Pump("凝结水泵")
        
        # --- 除氧器系统 ---
        deaerator = Merge("除氧器")  # 合并凝结水和抽汽
        feedwater_pump = Pump("给水泵")
        
        # --- 烟气系统（热源） ---
        flue_gas_source = Source("烟气入口")
        flue_gas_sink = Sink("烟气出口")
        
        # --- 循环水 ---
        cw_src = Source("循环水入口")
        cw_snk = Sink("循环水出口")
        
        print("[2] 组件定义完成")
        
        # ===================================================================
        # 定义连接
        # ===================================================================
        
        # --- 主蒸汽/工质循环 ---
        # 给水泵 → 省煤器 → 汽包(in1)
        c0 = Connection(feedwater_pump, "out1", economizer, "in2", label="给水")
        c1 = Connection(economizer, "out2", drum, "in1", label="预热水")
        
        # 汽包(out1) → 水冷壁 → 汽包(in2) [循环]
        c2 = Connection(drum, "out1", waterwall, "in2", label="下降管水")
        c3 = Connection(waterwall, "out2", drum, "in2", label="上升管汽水")
        
        # 汽包(out2) → 过热器 → 高压缸
        c4 = Connection(drum, "out2", superheater, "in2", label="饱和蒸汽")
        c5 = Connection(superheater, "out2", cc, "in1", label="过热器出口")
        c6 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
        
        # 高压缸 → 抽汽分流器
        c7 = Connection(hp_turbine, "out1", extraction_splitter, "in1", label="高压缸排汽")
        
        # 抽汽分流器 → 再热器 → 低压缸
        c8 = Connection(extraction_splitter, "out1", reheater, "in2", label="主流再热")
        c9 = Connection(reheater, "out2", lp_turbine, "in1", label="再热蒸汽")
        
        # 抽汽分流器 → 除氧器（抽汽）
        c10 = Connection(extraction_splitter, "out2", deaerator, "in1", label="抽汽加热")
        
        # 低压缸 → 凝汽器 → 凝结水泵
        c11 = Connection(lp_turbine, "out1", condenser, "in1", label="低压缸排汽")
        c12 = Connection(condenser, "out1", condensate_pump, "in1", label="凝结水")
        
        # 凝结水泵 → 除氧器 → 给水泵
        c13 = Connection(condensate_pump, "out1", deaerator, "in2", label="升压凝结水")
        c14 = Connection(deaerator, "out1", feedwater_pump, "in1", label="除氧后给水")
        
        nw.add_conns(c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14)
        
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
        
        print("[3] 连接建立完成")
        
        # ===================================================================
        # 设置组件参数
        # ===================================================================
        
        # --- 换热器参数 ---
        if mode == 'design':
            # 设计模式：只设置压降，kA由求解器计算
            economizer.set_attr(pr1=0.98, pr2=self.params['economizer_pr'])
            waterwall.set_attr(pr1=0.98)
            superheater.set_attr(pr1=0.98, pr2=self.params['superheater_pr'])
            reheater.set_attr(pr1=0.98, pr2=self.params['reheater_pr'])
        else:
            # 仿真模式：固定 kA（预测模式）
            economizer.set_attr(
                pr1=0.98, pr2=self.params['economizer_pr'],
                kA=self.params['economizer_kA']
            )
            waterwall.set_attr(
                pr1=0.98,
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
        
        # --- 汽轮机 ---
        hp_turbine.set_attr(eta_s=self.params['hp_turbine_eta'])
        lp_turbine.set_attr(eta_s=self.params['lp_turbine_eta'])
        
        # --- 泵 ---
        condensate_pump.set_attr(eta_s=self.params['condensate_pump_eta'])
        feedwater_pump.set_attr(eta_s=self.params['feedwater_pump_eta'])
        
        # --- 凝汽器 ---
        condenser.set_attr(pr1=1.0, pr2=0.98, ttd_u=self.params['condenser_ttd'])
        
        # --- 除氧器 ---
        # Merge组件没有pr参数，压力由连接决定
        # deaerator.set_attr(...)  # 无需设置
        
        print("[4] 组件参数设置完成")
        
        # ===================================================================
        # 设置边界条件
        # ===================================================================
        
        # --- 流体定义 ---
        c0.set_attr(fluid={"water": 1})
        fg1.set_attr(fluid={"air": 0.77, "O2": 0.1, "CO2": 0.1, "H2O": 0.03})
        cw1.set_attr(fluid={"water": 1})
        
        # --- 烟气侧输入（预测模式的输入） ---
        fg1.set_attr(
            T=self.params['flue_gas_T_in'],
            p=self.params['flue_gas_p'],
            m=self.params['flue_gas_m']
        )
        
        # --- 主蒸汽/工质循环 ---
        if mode == 'design':
            # 设计模式：固定主蒸汽参数（用于反算kA）
            c6.set_attr(
                p=self.params['main_steam_p_init'],
                T=self.params['main_steam_T_init'],
                m=self.params['main_steam_m_init']
            )
        else:
            # 仿真模式：主蒸汽参数由烟气和换热器决定（预测）
            # 只给初值，不固定
            c6.set_attr(
                p0=self.params['main_steam_p_init'],
                T0=self.params['main_steam_T_init'],
                m0=self.params['main_steam_m_init']
            )
        
        # 饱和蒸汽（汽包出口）
        c4.set_attr(x=1.0)  # 干度=1（饱和蒸汽）
        
        # 抽汽比例
        c10.set_attr(m=Ref(c6, self.params['extraction_ratio'], 0))
        
        # 再热压力
        c9.set_attr(p=self.params['reheat_p'])
        
        # 凝汽器压力
        c11.set_attr(p=self.params['condenser_p'])
        
        # 除氧器压力
        c14.set_attr(p=self.params['deaerator_p'])
        
        # --- 循环水 ---
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
        print(f"   凝汽器: {self.params['condenser_p']} bar")
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
    
    def save_design_point(self, filename='boiler_turbine_design.json'):
        """保存设计点（用于后续仿真模式）."""
        if self.nw and self.nw.converged:
            self.nw.save(filename)
            print(f"\n✓ 设计点已保存: {filename}")
            
            # 提取并显示关键设计参数
            economizer = self.nw.get_comp("省煤器")
            waterwall = self.nw.get_comp("水冷壁")
            superheater = self.nw.get_comp("过热器")
            reheater = self.nw.get_comp("再热器")
            
            print("\n关键设计参数（用于仿真模式）：")
            print(f"  economizer_kA:  {economizer.kA.val:.1f} kW/K")
            print(f"  waterwall_kA:   {waterwall.kA.val:.1f} kW/K")
            print(f"  superheater_kA: {superheater.kA.val:.1f} kW/K")
            print(f"  reheater_kA:    {reheater.kA.val:.1f} kW/K")
    
    def load_design_point(self, filename='boiler_turbine_design.json'):
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
        drum = self.nw.get_comp("汽包")
        hp_turb = self.nw.get_comp("高压缸")
        lp_turb = self.nw.get_comp("低压缸")
        feedwater_pump = self.nw.get_comp("给水泵")
        condensate_pump = self.nw.get_comp("凝结水泵")
        condenser = self.nw.get_comp("凝汽器")
        deaerator = self.nw.get_comp("除氧器")
        
        # 获取连接
        feedwater = self.nw.get_conn("给水")
        preheated_water = self.nw.get_conn("预热水")
        saturated_steam = self.nw.get_conn("饱和蒸汽")
        main_steam = self.nw.get_conn("主蒸汽")
        hp_exhaust = self.nw.get_conn("高压缸排汽")
        extraction_steam = self.nw.get_conn("抽汽加热")
        reheat_steam = self.nw.get_conn("再热蒸汽")
        lp_exhaust = self.nw.get_conn("低压缸排汽")
        condensate = self.nw.get_conn("凝结水")
        flue_gas_in = self.nw.get_conn("烟气入炉")
        flue_gas_out = self.nw.get_conn("烟气出口")
        
        # === 锅炉系统分析 ===
        Q_economizer = economizer.Q.val
        Q_waterwall = waterwall.Q.val
        Q_superheater = superheater.Q.val
        Q_boiler_total = abs(Q_economizer) + abs(Q_waterwall) + abs(Q_superheater)
        Q_reheater = reheater.Q.val
        Q_total = Q_boiler_total + abs(Q_reheater)
        
        print("\n【1. 锅炉系统性能】")
        print("-" * 80)
        print(f"\n省煤器:")
        print(f"  吸热量:    {abs(Q_economizer):10.3f} MW  "
              f"({abs(Q_economizer)/Q_boiler_total*100:5.1f}%)")
        if hasattr(economizer, 'kA') and economizer.kA.is_set:
            print(f"  kA:        {economizer.kA.val:10.1f} kW/K")
        print(f"  温升:      {preheated_water.T.val - feedwater.T.val:10.2f} K")
        
        print(f"\n水冷壁（主要吸热段）:")
        print(f"  吸热量:    {abs(Q_waterwall):10.3f} MW  "
              f"({abs(Q_waterwall)/Q_boiler_total*100:5.1f}%) ⭐")
        if hasattr(waterwall, 'kA') and waterwall.kA.is_set:
            print(f"  kA:        {waterwall.kA.val:10.1f} kW/K")
        
        print(f"\n过热器:")
        print(f"  吸热量:    {abs(Q_superheater):10.3f} MW  "
              f"({abs(Q_superheater)/Q_boiler_total*100:5.1f}%)")
        if hasattr(superheater, 'kA') and superheater.kA.is_set:
            print(f"  kA:        {superheater.kA.val:10.1f} kW/K")
        print(f"  过热度:    {main_steam.T.val - saturated_steam.T.val:10.2f} K")
        
        print(f"\n再热器:")
        print(f"  吸热量:    {abs(Q_reheater):10.3f} MW  "
              f"({abs(Q_reheater)/Q_total*100:5.1f}%)")
        if hasattr(reheater, 'kA') and reheater.kA.is_set:
            print(f"  kA:        {reheater.kA.val:10.1f} kW/K")
        
        print(f"\n烟气:")
        print(f"  入口温度:  {flue_gas_in.T.val:10.2f} °C")
        print(f"  出口温度:  {flue_gas_out.T.val:10.2f} °C")
        print(f"  温降:      {flue_gas_in.T.val - flue_gas_out.T.val:10.2f} K")
        print(f"  放热:      {Q_total:10.3f} MW")
        
        # === 汽轮机系统分析 ===
        P_hp = abs(hp_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_lp
        P_feedwater_pump = abs(feedwater_pump.P.val)
        P_condensate_pump = abs(condensate_pump.P.val)
        P_pump_total = P_feedwater_pump + P_condensate_pump
        P_net = P_turb_total - P_pump_total
        
        print("\n【2. 汽轮机系统性能】")
        print("-" * 80)
        print(f"\n高压缸:")
        print(f"  出力:      {P_hp:10.3f} MW  ({P_hp/P_turb_total*100:5.1f}%)")
        print(f"  膨胀比:    {main_steam.p.val/hp_exhaust.p.val:10.2f}")
        print(f"  抽汽量:    {extraction_steam.m.val:10.3f} kg/s  "
              f"({extraction_steam.m.val/main_steam.m.val*100:5.1f}%)")
        
        print(f"\n低压缸:")
        print(f"  出力:      {P_lp:10.3f} MW  ({P_lp/P_turb_total*100:5.1f}%)")
        print(f"  膨胀比:    {reheat_steam.p.val/lp_exhaust.p.val:10.2f}")
        if hasattr(lp_exhaust, 'x') and lp_exhaust.x.val is not None:
            print(f"  排汽干度:  {lp_exhaust.x.val:10.4f}", end="")
            if lp_exhaust.x.val < 0.85:
                print("  ⚠ 过低")
            elif lp_exhaust.x.val > 0.98:
                print("  ⚠ 过高")
            else:
                print("  ✓")
        
        print(f"\n泵:")
        print(f"  给水泵:    {P_feedwater_pump:10.3f} MW")
        print(f"  凝结水泵:  {P_condensate_pump:10.3f} MW")
        print(f"  总计:      {P_pump_total:10.3f} MW  "
              f"(厂用电率: {P_pump_total/P_turb_total*100:.2f}%)")
        
        # === 循环效率分析 ===
        Q_condenser = abs(condenser.Q.val)
        eta_thermal = P_net / Q_total * 100 if Q_total > 0 else 0
        
        print("\n【3. 循环效率分析】")
        print("-" * 80)
        print(f"\n循环热效率:      {eta_thermal:10.2f} %")
        print(f"净发电功率:      {P_net:10.3f} MW")
        print(f"总吸热:          {Q_total:10.3f} MW")
        print(f"凝汽放热:        {Q_condenser:10.3f} MW")
        
        # 能量平衡
        energy_balance = abs(Q_total - (Q_condenser + P_net))
        energy_balance_pct = energy_balance / Q_total * 100 if Q_total > 0 else 0
        
        print(f"\n能量平衡验证:")
        print(f"  误差:      {energy_balance:10.6f} MW  ({energy_balance_pct:.4f}%)", end="")
        if energy_balance_pct < 0.1:
            print("  ✓")
        else:
            print("  ⚠")
        
        # === 关键状态点 ===
        print("\n【4. 关键状态点】")
        print("-" * 80)
        
        states = [
            ("主蒸汽", main_steam),
            ("再热蒸汽", reheat_steam),
            ("抽汽", extraction_steam),
            ("排汽", lp_exhaust),
            ("凝结水", condensate),
            ("给水", feedwater),
        ]
        
        print(f"\n{'状态点':<12} {'压力(bar)':<12} {'温度(°C)':<12} "
              f"{'流量(kg/s)':<12} {'焓(kJ/kg)':<12}")
        print("-" * 60)
        
        for name, conn in states:
            print(f"{name:<12} {conn.p.val:<12.3f} {conn.T.val:<12.2f} "
                  f"{conn.m.val:<12.3f} {conn.h.val:<12.2f}")
        
        # === 性能汇总 ===
        print("\n【5. 性能汇总】")
        print("=" * 80)
        print(f"净发电功率:      {P_net:10.3f} MW")
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"主蒸汽参数:      {main_steam.p.val:.2f} bar / {main_steam.T.val:.2f}°C / "
              f"{main_steam.m.val:.2f} kg/s")
        print(f"抽汽比例:        {extraction_steam.m.val/main_steam.m.val*100:10.2f} %")
        print(f"厂用电率:        {P_pump_total/P_turb_total*100:10.2f} %")
        if hasattr(lp_exhaust, 'x') and lp_exhaust.x.val is not None:
            print(f"排汽干度:        {lp_exhaust.x.val:10.4f}")
        print("=" * 80)
        
        # 保存结果
        self.results = {
            "P_net_MW": P_net,
            "eta_thermal_percent": eta_thermal,
            "main_steam_p_bar": main_steam.p.val,
            "main_steam_T_degC": main_steam.T.val,
            "main_steam_m_kg_s": main_steam.m.val,
            "extraction_ratio": extraction_steam.m.val/main_steam.m.val,
            "Q_total_MW": Q_total,
            "Q_economizer_MW": abs(Q_economizer),
            "Q_waterwall_MW": abs(Q_waterwall),
            "Q_superheater_MW": abs(Q_superheater),
            "Q_reheater_MW": abs(Q_reheater),
            "Q_condenser_MW": Q_condenser,
            "flue_gas_T_in": flue_gas_in.T.val,
            "flue_gas_T_out": flue_gas_out.T.val,
            "energy_balance_error_percent": energy_balance_pct,
        }
        
        return self.results


def main():
    """主函数 - 演示阶段1功能."""
    
    print("\n" + "=" * 80)
    print("工程级预测型锅炉-汽轮机系统 - 阶段1演示")
    print("=" * 80)
    print("\n本演示分两步：")
    print("  1. 设计模式：固定主蒸汽参数，反算换热器kA")
    print("  2. 仿真模式：固定换热器kA，预测主蒸汽参数")
    print("=" * 80)
    
    # === 步骤1：设计模式求解 ===
    print("\n\n### 步骤1：设计模式求解 ###\n")
    
    system = PredictiveBoilerTurbineSystem()
    system.build_network(mode='design')
    
    if system.solve():
        system.analyze()
        system.save_design_point('boiler_turbine_stage1_design.json')
    else:
        print("\n✗ 设计模式求解失败，无法继续")
        return
    
    # 提取设计参数
    economizer = system.nw.get_comp("省煤器")
    waterwall = system.nw.get_comp("水冷壁")
    superheater = system.nw.get_comp("过热器")
    reheater = system.nw.get_comp("再热器")
    
    design_kA = {
        'economizer_kA': economizer.kA.val,
        'waterwall_kA': waterwall.kA.val,
        'superheater_kA': superheater.kA.val,
        'reheater_kA': reheater.kA.val,
    }
    
    # === 步骤2：仿真模式求解（预测） ===
    print("\n\n### 步骤2：仿真模式求解（预测模式） ###\n")
    print("现在改变烟气温度，预测主蒸汽参数变化...")
    
    # 创建新系统，使用设计的kA值
    system2 = PredictiveBoilerTurbineSystem(design_params=design_kA)
    
    # 改变输入条件（例如降低烟气温度）
    system2.params['flue_gas_T_in'] = 1100  # 从1200降到1100
    
    system2.build_network(mode='offdesign')
    system2.load_design_point('boiler_turbine_stage1_design.json')
    
    if system2.solve():
        results = system2.analyze()
        
        print("\n\n### 预测模式对比 ###")
        print("=" * 80)
        print(f"{'参数':<20} {'设计点':<20} {'预测点':<20} {'变化':<20}")
        print("-" * 80)
        print(f"{'烟气温度(°C)':<20} {1200:<20.1f} {1100:<20.1f} {-100:<20.1f}")
        print(f"{'主蒸汽压力(bar)':<20} {system.results['main_steam_p_bar']:<20.2f} "
              f"{results['main_steam_p_bar']:<20.2f} "
              f"{results['main_steam_p_bar']-system.results['main_steam_p_bar']:<20.2f}")
        print(f"{'主蒸汽温度(°C)':<20} {system.results['main_steam_T_degC']:<20.2f} "
              f"{results['main_steam_T_degC']:<20.2f} "
              f"{results['main_steam_T_degC']-system.results['main_steam_T_degC']:<20.2f}")
        print(f"{'主蒸汽流量(kg/s)':<20} {system.results['main_steam_m_kg_s']:<20.2f} "
              f"{results['main_steam_m_kg_s']:<20.2f} "
              f"{results['main_steam_m_kg_s']-system.results['main_steam_m_kg_s']:<20.2f}")
        print(f"{'净功率(MW)':<20} {system.results['P_net_MW']:<20.2f} "
              f"{results['P_net_MW']:<20.2f} "
              f"{results['P_net_MW']-system.results['P_net_MW']:<20.2f}")
        print(f"{'热效率(%)':<20} {system.results['eta_thermal_percent']:<20.2f} "
              f"{results['eta_thermal_percent']:<20.2f} "
              f"{results['eta_thermal_percent']-system.results['eta_thermal_percent']:<20.2f}")
        print("=" * 80)
        
        print("\n✓ 阶段1完成！模型已成功从设计模式转为预测模式。")
        print("\n下一步改进方向（阶段2）：")
        print("  • 添加多级抽汽回热系统（高压加热器 + 低压加热器）")
        print("  • 改进汽包和水循环建模")
        print("  • 增加更多传感器点和工况参数")
        print("  • 引入给水泵、凝结水泵分级建模")
    else:
        print("\n✗ 仿真模式求解失败")


if __name__ == "__main__":
    main()
