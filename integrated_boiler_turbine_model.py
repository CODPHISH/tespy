#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整整合的锅炉-汽轮机工况仿真模型.

本模型整合了详细锅炉模型和再热循环的优势，提供：
1. 详细的锅炉三段式结构（省煤器-水冷壁-过热器）
2. 双缸汽轮机配置（高压缸+低压缸）with 再热
3. 完整的热力学验证和性能分析
4. 符合实际工程的参数设置和约束
5. 详尽的输出结果和可视化数据

适用场景：
- 300-600MW 亚临界火电机组
- 典型参数：主蒸汽 150 bar/600°C，再热 30 bar/600°C
- 凝汽器真空：0.1 bar
"""

from tespy.networks import Network
from tespy.components import (
    CycleCloser,
    SimpleHeatExchanger,
    Turbine,
    Condenser,
    Pump,
    Source,
    Sink,
)
from tespy.connections import Connection


class BoilerTurbineSystem:
    """锅炉-汽轮机系统类."""
    
    def __init__(self, design_params: dict = None):
        """初始化系统参数.
        
        Parameters
        ----------
        design_params : dict, optional
            设计参数字典，包含：
            - main_steam_p: 主蒸汽压力 [bar]
            - main_steam_T: 主蒸汽温度 [°C]
            - main_steam_m: 主蒸汽流量 [kg/s]
            - reheat_p: 再热压力 [bar]
            - reheat_T: 再热温度 [°C]
            - condenser_p: 凝汽器压力 [bar]
            - cooling_water_T_in: 冷却水入口温度 [°C]
            - cooling_water_T_out: 冷却水出口温度 [°C]
        """
        if design_params is None:
            # 默认设计参数（典型300MW亚临界机组）
            self.params = {
                'main_steam_p': 150,      # bar (15 MPa)
                'main_steam_T': 600,      # °C
                'main_steam_m': 100,      # kg/s (约300MW机组)
                'reheat_p': 30,           # bar (3 MPa)
                'reheat_T': 600,          # °C
                'condenser_p': 0.05,      # bar (5 kPa, 高真空)
                'cooling_water_T_in': 20, # °C
                'cooling_water_T_out': 32, # °C
                # 组件效率参数
                'hp_turbine_eta': 0.88,   # 高压缸等熵效率
                'lp_turbine_eta': 0.86,   # 低压缸等熵效率
                'pump_eta': 0.78,         # 给水泵效率
                'economizer_pr': 0.98,    # 省煤器压比
                'waterwall_pr': 0.97,     # 水冷壁压比
                'superheater_pr': 0.95,   # 过热器压比
                'reheater_pr': 0.97,      # 再热器压比
                'economizer_outlet_T': 330, # 省煤器出口温度 [°C]
            }
        else:
            self.params = design_params
        
        self.nw = None
        self.results = {}
    
    def build_network(self) -> Network:
        """构建网络模型."""
        
        print("\n" + "=" * 80)
        print("完整锅炉-汽轮机工况仿真模型")
        print("=" * 80)
        print("\n系统配置：")
        print("  • 详细锅炉：省煤器 → 水冷壁 → 过热器")
        print("  • 再热系统：高压缸 → 再热器 → 低压缸")
        print("  • 凝汽系统：凝汽器 + 循环水")
        print("  • 给水系统：凝结水泵 + 给水泵")
        print(f"  • 设计容量：约 {self.params['main_steam_m'] * 3:.0f} MW")
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
        
        # 定义组件
        cc = CycleCloser("循环闭合器")
        
        # 锅炉系统
        economizer = SimpleHeatExchanger("省煤器")
        waterwall = SimpleHeatExchanger("水冷壁")
        superheater = SimpleHeatExchanger("过热器")
        reheater = SimpleHeatExchanger("再热器")
        
        # 汽轮机系统
        hp_turbine = Turbine("高压缸")
        lp_turbine = Turbine("低压缸")
        
        # 凝汽系统
        condenser = Condenser("凝汽器")
        pump = Pump("给水泵")
        
        # 循环水
        cw_src = Source("循环水入口")
        cw_snk = Sink("循环水出口")
        
        print("[2] 组件定义完成")
        
        # 定义连接
        # 主蒸汽路径
        c0 = Connection(pump, "out1", economizer, "in1", label="给水")
        c1 = Connection(economizer, "out1", waterwall, "in1", label="预热水")
        c2 = Connection(waterwall, "out1", superheater, "in1", label="饱和蒸汽")
        c3 = Connection(superheater, "out1", cc, "in1", label="过热器出口")
        c4 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
        
        # 再热路径
        c5 = Connection(hp_turbine, "out1", reheater, "in1", label="高压缸排汽")
        c6 = Connection(reheater, "out1", lp_turbine, "in1", label="再热蒸汽")
        
        # 凝汽路径
        c7 = Connection(lp_turbine, "out1", condenser, "in1", label="低压缸排汽")
        c8 = Connection(condenser, "out1", pump, "in1", label="凝结水")
        
        nw.add_conns(c0, c1, c2, c3, c4, c5, c6, c7, c8)
        
        # 循环水
        cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
        cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
        nw.add_conns(cw1, cw2)
        
        print("[3] 连接建立完成")
        
        # 设置组件参数
        economizer.set_attr(pr=self.params['economizer_pr'])
        waterwall.set_attr(pr=self.params['waterwall_pr'])
        superheater.set_attr(pr=self.params['superheater_pr'])
        reheater.set_attr(pr=self.params['reheater_pr'])
        
        hp_turbine.set_attr(eta_s=self.params['hp_turbine_eta'])
        lp_turbine.set_attr(eta_s=self.params['lp_turbine_eta'])
        
        condenser.set_attr(pr1=1.0, pr2=0.98)
        pump.set_attr(eta_s=self.params['pump_eta'])
        
        print("[4] 组件参数设置完成")
        
        # 设置边界条件
        # 计算给水泵出口压力（补偿锅炉压降）
        feedwater_p = self.params['main_steam_p'] / (
            self.params['economizer_pr'] * 
            self.params['waterwall_pr'] * 
            self.params['superheater_pr']
        )
        
        c0.set_attr(p=feedwater_p, fluid={"water": 1})
        c1.set_attr(T=self.params['economizer_outlet_T'])
        c2.set_attr(x=1.0)  # 饱和蒸汽
        
        c4.set_attr(
            p=self.params['main_steam_p'],
            T=self.params['main_steam_T'],
            m=self.params['main_steam_m'],
        )
        
        c5.set_attr(p=self.params['reheat_p'])
        c6.set_attr(T=self.params['reheat_T'])
        c7.set_attr(p=self.params['condenser_p'])
        
        cw1.set_attr(
            T=self.params['cooling_water_T_in'], 
            p=1.2, 
            fluid={"water": 1}
        )
        cw2.set_attr(T=self.params['cooling_water_T_out'])
        
        print("[5] 边界条件设置完成")
        print(f"   给水压力: {feedwater_p:.2f} bar")
        print(f"   主蒸汽: {self.params['main_steam_p']} bar / "
              f"{self.params['main_steam_T']}°C / "
              f"{self.params['main_steam_m']} kg/s")
        print(f"   再热: {self.params['reheat_p']} bar / "
              f"{self.params['reheat_T']}°C")
        print(f"   凝汽器: {self.params['condenser_p']} bar")
        print("=" * 80)
        
        self.nw = nw
        return nw
    
    def solve(self) -> bool:
        """求解模型."""
        
        print("\n开始求解...")
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
        pump = self.nw.get_comp("给水泵")
        condenser = self.nw.get_comp("凝汽器")
        
        # 获取连接
        feedwater = self.nw.get_conn("给水")
        preheated_water = self.nw.get_conn("预热水")
        saturated_steam = self.nw.get_conn("饱和蒸汽")
        main_steam = self.nw.get_conn("主蒸汽")
        hp_exhaust = self.nw.get_conn("高压缸排汽")
        reheat_steam = self.nw.get_conn("再热蒸汽")
        lp_exhaust = self.nw.get_conn("低压缸排汽")
        condensate = self.nw.get_conn("凝结水")
        cw_in = self.nw.get_conn("冷却水入口")
        cw_out = self.nw.get_conn("冷却水出口")
        
        # === 锅炉系统分析 ===
        Q_economizer = economizer.Q.val
        Q_waterwall = waterwall.Q.val
        Q_superheater = superheater.Q.val
        Q_boiler_total = Q_economizer + Q_waterwall + Q_superheater
        Q_reheater = reheater.Q.val
        Q_total = Q_boiler_total + Q_reheater
        
        print("\n【1. 锅炉系统性能】")
        print("-" * 80)
        print(f"\n省煤器:")
        print(f"  吸热量:    {Q_economizer:10.3f} MW  "
              f"({Q_economizer/Q_boiler_total*100:5.1f}%)")
        print(f"  温升:      {preheated_water.T.val - feedwater.T.val:10.2f} K")
        print(f"  压降:      {feedwater.p.val - preheated_water.p.val:10.3f} bar")
        
        print(f"\n水冷壁（主要吸热段）:")
        print(f"  吸热量:    {Q_waterwall:10.3f} MW  "
              f"({Q_waterwall/Q_boiler_total*100:5.1f}%) ⭐")
        print(f"  蒸发潜热:  {saturated_steam.h.val - preheated_water.h.val:10.2f} kJ/kg")
        print(f"  压降:      {preheated_water.p.val - saturated_steam.p.val:10.3f} bar")
        
        print(f"\n过热器:")
        print(f"  吸热量:    {Q_superheater:10.3f} MW  "
              f"({Q_superheater/Q_boiler_total*100:5.1f}%)")
        print(f"  过热度:    {main_steam.T.val - saturated_steam.T.val:10.2f} K")
        print(f"  压降:      {saturated_steam.p.val - main_steam.p.val:10.3f} bar")
        
        print(f"\n再热器:")
        print(f"  吸热量:    {Q_reheater:10.3f} MW  "
              f"({Q_reheater/Q_total*100:5.1f}%)")
        print(f"  温升:      {reheat_steam.T.val - hp_exhaust.T.val:10.2f} K")
        
        print(f"\n锅炉总计:")
        print(f"  总吸热:    {Q_boiler_total:10.3f} MW  "
              f"({Q_boiler_total/Q_total*100:5.1f}%)")
        print(f"  总压降:    {feedwater.p.val - main_steam.p.val:10.3f} bar  "
              f"({(1-main_steam.p.val/feedwater.p.val)*100:5.2f}%)")
        
        # === 汽轮机系统分析 ===
        P_hp = abs(hp_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_lp
        P_pump = abs(pump.P.val)
        P_net = P_turb_total - P_pump
        
        print("\n【2. 汽轮机系统性能】")
        print("-" * 80)
        print(f"\n高压缸:")
        print(f"  出力:      {P_hp:10.3f} MW  "
              f"({P_hp/P_turb_total*100:5.1f}%)")
        print(f"  膨胀比:    {main_steam.p.val/hp_exhaust.p.val:10.2f}")
        print(f"  等熵效率:  {hp_turb.eta_s.val:10.3f}")
        
        print(f"\n低压缸:")
        print(f"  出力:      {P_lp:10.3f} MW  "
              f"({P_lp/P_turb_total*100:5.1f}%)")
        print(f"  膨胀比:    {reheat_steam.p.val/lp_exhaust.p.val:10.2f}")
        print(f"  等熵效率:  {lp_turb.eta_s.val:10.3f}")
        print(f"  排汽干度:  {lp_exhaust.x.val:10.4f}", end="")
        
        if lp_exhaust.x.val < 0.85:
            print("  ⚠ 过低")
        elif lp_exhaust.x.val > 0.95:
            print("  ⚠ 过高")
        else:
            print("  ✓")
        
        print(f"\n给水泵:")
        print(f"  耗功:      {P_pump:10.3f} MW  "
              f"(厂用电率: {P_pump/P_turb_total*100:.2f}%)")
        print(f"  压比:      {feedwater.p.val/condensate.p.val:10.2f}")
        print(f"  等熵效率:  {pump.eta_s.val:10.3f}")
        
        # === 循环效率分析 ===
        Q_condenser = abs(condenser.Q.val)
        eta_thermal = P_net / Q_total * 100
        T_h = main_steam.T.val + 273.15
        T_l = lp_exhaust.T.val + 273.15
        eta_carnot = (1 - T_l / T_h) * 100
        
        print("\n【3. 循环效率分析】")
        print("-" * 80)
        print(f"\n循环热效率:      {eta_thermal:10.2f} %")
        print(f"卡诺效率(理论):  {eta_carnot:10.2f} %")
        print(f"相对卡诺效率:    {eta_thermal/eta_carnot*100:10.2f} %")
        
        # 能量平衡验证
        energy_balance = abs(Q_total - (Q_condenser + P_net))
        energy_balance_pct = energy_balance / Q_total * 100
        
        print(f"\n能量平衡验证:")
        print(f"  总输入:    {Q_total:10.3f} MW")
        print(f"  净做功:    {P_net:10.3f} MW  ({P_net/Q_total*100:5.2f}%)")
        print(f"  凝汽放热:  {Q_condenser:10.3f} MW  "
              f"({Q_condenser/Q_total*100:5.2f}%)")
        print(f"  误差:      {energy_balance:10.6f} MW  "
              f"({energy_balance_pct:.4f}%)", end="")
        
        if energy_balance_pct < 0.1:
            print("  ✓")
        else:
            print("  ⚠")
        
        # === 凝汽系统分析 ===
        m_cw = cw_in.m.val
        delta_T_cw = cw_out.T.val - cw_in.T.val
        
        print("\n【4. 凝汽系统性能】")
        print("-" * 80)
        print(f"\n凝汽器:")
        print(f"  放热量:    {Q_condenser:10.3f} MW")
        print(f"  背压:      {lp_exhaust.p.val:10.4f} bar  "
              f"({lp_exhaust.p.val*100:5.2f} kPa)")
        print(f"  真空度:    {(1.01325-lp_exhaust.p.val)/1.01325*100:10.2f} %")
        print(f"  上端差:    {condenser.ttd_u.val:10.2f} K")
        print(f"  下端差:    {condenser.ttd_l.val:10.2f} K")
        
        print(f"\n循环水:")
        print(f"  流量:      {m_cw:10.2f} kg/s")
        print(f"  温升:      {delta_T_cw:10.2f} K")
        print(f"  流量比:    {m_cw/main_steam.m.val:10.2f}  (循环水/工质)")
        
        # === 关键状态点 ===
        print("\n【5. 关键状态点】")
        print("-" * 80)
        
        states = [
            ("给水", feedwater),
            ("预热水", preheated_water),
            ("饱和蒸汽", saturated_steam),
            ("主蒸汽", main_steam),
            ("高压缸排汽", hp_exhaust),
            ("再热蒸汽", reheat_steam),
            ("低压缸排汽", lp_exhaust),
            ("凝结水", condensate),
        ]
        
        print(f"\n{'状态点':<12} {'压力(bar)':<12} {'温度(°C)':<12} "
              f"{'焓(kJ/kg)':<12} {'干度':<8}")
        print("-" * 60)
        
        for name, conn in states:
            x_str = f"{conn.x.val:.4f}" if hasattr(conn, 'x') else "N/A"
            print(f"{name:<12} {conn.p.val:<12.3f} {conn.T.val:<12.2f} "
                  f"{conn.h.val:<12.2f} {x_str:<8}")
        
        # === 性能汇总 ===
        print("\n【6. 性能汇总】")
        print("=" * 80)
        print(f"净发电功率:      {P_net:10.3f} MW")
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"总吸热量:        {Q_total:10.3f} MW")
        print(f"锅炉效率:        {Q_boiler_total/Q_total*100:10.2f} %")
        print(f"厂用电率:        {P_pump/P_turb_total*100:10.2f} %")
        print(f"汽轮机出力:      {P_turb_total:10.3f} MW")
        print(f"排汽干度:        {lp_exhaust.x.val:10.4f}")
        
        # === 工程验证 ===
        print("\n【7. 工程合理性验证】")
        print("-" * 80)
        
        checks = []
        
        # 检查1: 效率合理性
        if 38 <= eta_thermal <= 44:
            checks.append(("✓", f"循环效率 {eta_thermal:.2f}% 在合理范围 (38-44%)"))
        else:
            checks.append(("⚠", f"循环效率 {eta_thermal:.2f}% 超出典型范围"))
        
        # 检查2: 排汽干度
        if 0.85 <= lp_exhaust.x.val <= 0.95:
            checks.append(("✓", f"排汽干度 {lp_exhaust.x.val:.4f} 合理"))
        else:
            checks.append(("⚠", f"排汽干度 {lp_exhaust.x.val:.4f} 需关注"))
        
        # 检查3: 能量守恒
        if energy_balance_pct < 0.1:
            checks.append(("✓", f"能量平衡误差 {energy_balance_pct:.4f}% < 0.1%"))
        else:
            checks.append(("⚠", f"能量平衡误差 {energy_balance_pct:.4f}% 偏大"))
        
        # 检查4: 凝汽器真空度
        vacuum = (1.01325-lp_exhaust.p.val)/1.01325*100
        if 90 <= vacuum <= 96:
            checks.append(("✓", f"凝汽器真空度 {vacuum:.2f}% 正常"))
        else:
            checks.append(("⚠", f"凝汽器真空度 {vacuum:.2f}% 异常"))
        
        # 检查5: 厂用电率
        aux_power_rate = P_pump/P_turb_total*100
        if aux_power_rate < 2.0:
            checks.append(("✓", f"厂用电率 {aux_power_rate:.2f}% 合理"))
        else:
            checks.append(("⚠", f"厂用电率 {aux_power_rate:.2f}% 偏高"))
        
        # 检查6: 水冷壁吸热占比
        waterwall_ratio = Q_waterwall/Q_boiler_total*100
        if 60 <= waterwall_ratio <= 75:
            checks.append(("✓", f"水冷壁吸热占比 {waterwall_ratio:.1f}% 符合理论"))
        else:
            checks.append(("⚠", f"水冷壁吸热占比 {waterwall_ratio:.1f}% 异常"))
        
        for status, msg in checks:
            print(f"{status} {msg}")
        
        passed = sum(1 for s, _ in checks if s == "✓")
        total = len(checks)
        print(f"\n验证通过: {passed}/{total} 项")
        
        if passed == total:
            print("✓ 模型通过所有工程验证")
        elif passed >= total * 0.8:
            print("⚠ 模型基本合理，部分指标需关注")
        else:
            print("✗ 模型存在问题，需要检查参数")
        
        print("=" * 80)
        
        # 保存结果
        self.results = {
            "P_net_MW": P_net,
            "P_turb_MW": P_turb_total,
            "P_hp_MW": P_hp,
            "P_lp_MW": P_lp,
            "P_pump_MW": P_pump,
            "eta_thermal_percent": eta_thermal,
            "eta_carnot_percent": eta_carnot,
            "Q_total_MW": Q_total,
            "Q_boiler_MW": Q_boiler_total,
            "Q_economizer_MW": Q_economizer,
            "Q_waterwall_MW": Q_waterwall,
            "Q_superheater_MW": Q_superheater,
            "Q_reheater_MW": Q_reheater,
            "Q_condenser_MW": Q_condenser,
            "exhaust_quality": lp_exhaust.x.val,
            "condenser_vacuum_percent": vacuum,
            "aux_power_rate_percent": aux_power_rate,
            "energy_balance_error_percent": energy_balance_pct,
            "validation_passed": passed,
            "validation_total": total,
        }
        
        return self.results
    
    def export_results(self, filename: str = "integrated_boiler_turbine_design"):
        """导出结果."""
        
        if self.nw:
            self.nw.save(filename)
            print(f"\n✓ 网络数据已保存: {filename}.json")
        
        # 保存性能数据到文本文件
        if self.results:
            with open(f"{filename}_performance.txt", "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("锅炉-汽轮机系统性能汇总\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("【功率性能】\n")
                f.write(f"净发电功率:      {self.results['P_net_MW']:.3f} MW\n")
                f.write(f"汽轮机总功率:    {self.results['P_turb_MW']:.3f} MW\n")
                f.write(f"  - 高压缸:      {self.results['P_hp_MW']:.3f} MW\n")
                f.write(f"  - 低压缸:      {self.results['P_lp_MW']:.3f} MW\n")
                f.write(f"给水泵耗功:      {self.results['P_pump_MW']:.3f} MW\n\n")
                
                f.write("【热量平衡】\n")
                f.write(f"总输入热量:      {self.results['Q_total_MW']:.3f} MW\n")
                f.write(f"  - 锅炉吸热:    {self.results['Q_boiler_MW']:.3f} MW\n")
                f.write(f"    * 省煤器:    {self.results['Q_economizer_MW']:.3f} MW\n")
                f.write(f"    * 水冷壁:    {self.results['Q_waterwall_MW']:.3f} MW\n")
                f.write(f"    * 过热器:    {self.results['Q_superheater_MW']:.3f} MW\n")
                f.write(f"  - 再热器吸热:  {self.results['Q_reheater_MW']:.3f} MW\n")
                f.write(f"凝汽器放热:      {self.results['Q_condenser_MW']:.3f} MW\n\n")
                
                f.write("【效率指标】\n")
                f.write(f"循环热效率:      {self.results['eta_thermal_percent']:.2f} %\n")
                f.write(f"卡诺效率:        {self.results['eta_carnot_percent']:.2f} %\n")
                f.write(f"厂用电率:        {self.results['aux_power_rate_percent']:.2f} %\n\n")
                
                f.write("【关键参数】\n")
                f.write(f"排汽干度:        {self.results['exhaust_quality']:.4f}\n")
                f.write(f"凝汽器真空度:    {self.results['condenser_vacuum_percent']:.2f} %\n")
                f.write(f"能量平衡误差:    {self.results['energy_balance_error_percent']:.4f} %\n")
                f.write(f"验证通过:        {self.results['validation_passed']}/{self.results['validation_total']} 项\n")
            
            print(f"✓ 性能数据已保存: {filename}_performance.txt")


def main():
    """主程序."""
    
    # 创建系统实例
    system = BoilerTurbineSystem()
    
    # 构建网络
    system.build_network()
    
    # 求解
    if system.solve():
        # 分析
        system.analyze()
        
        # 导出结果
        system.export_results()
        
        print("\n" + "=" * 80)
        print("仿真完成！")
        print("=" * 80)
    else:
        print("\n求解失败，请检查参数设置。")


if __name__ == "__main__":  # pragma: no cover
    main()
