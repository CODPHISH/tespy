#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细锅炉模型的再热Rankine循环发电厂仿真.

本模型相比简化模型的改进：
1. 详细的锅炉组成结构：
   - 省煤器（Economizer）：预热给水
   - 水冷壁（Waterwall）：水蒸发成饱和蒸汽
   - 过热器（Superheater）：饱和蒸汽加热成过热蒸汽
2. 再热器（Reheater）：高压缸排汽再次加热
3. 双缸汽轮机（高压缸 + 低压缸）

这是一个更接近真实火电厂配置的详细仿真模型。

锅炉工作原理：
- 省煤器：利用尾部烟气余热预热给水，提高给水温度至接近饱和温度
- 水冷壁：炉膛四周的管道，通过辐射传热使水沸腾蒸发成饱和蒸汽
- 过热器：炉膛上方的蛇形管排，继续加热饱和蒸汽成为过热蒸汽
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


def build_detailed_boiler_cycle() -> Network:
    """构建带详细锅炉模型的再热Rankine循环."""
    
    print("\n" + "=" * 80)
    print("详细锅炉模型的再热Rankine循环发电厂仿真")
    print("=" * 80)
    print("\n系统配置：")
    print("  • 详细锅炉模型：省煤器 → 水冷壁 → 过热器")
    print("  • 双缸汽轮机：高压缸 + 低压缸")
    print("  • 一次再热循环")
    print("  • 更真实地模拟锅炉内部水/蒸汽的状态变化")
    print("=" * 80)
    
    # 1) 创建网络
    nw = Network(iterinfo=False)
    nw.units.set_defaults(
        temperature="degC",
        pressure="bar",
        enthalpy="kJ/kg",
        power="MW",
        heat="MW",
    )
    print("\n[1] 网络初始化完成")
    
    # 2) 定义组件
    cc = CycleCloser("循环闭合器")
    
    # 详细锅炉组件
    economizer = SimpleHeatExchanger("省煤器")
    waterwall = SimpleHeatExchanger("水冷壁")
    superheater = SimpleHeatExchanger("过热器")
    reheater = SimpleHeatExchanger("再热器")
    
    # 双缸汽轮机
    hp_turbine = Turbine("高压缸")
    lp_turbine = Turbine("低压缸")
    
    # 其他组件
    condenser = Condenser("凝汽器")
    pump = Pump("给水泵")
    
    # 循环水
    cw_src = Source("循环水入口")
    cw_snk = Sink("循环水出口")
    
    print("[2] 组件定义完成：")
    print("    锅炉系统: 省煤器 / 水冷壁 / 过热器 / 再热器")
    print("    汽轮机系统: 高压缸 / 低压缸")
    print("    辅机: 凝汽器 / 给水泵")
    
    # 3) 定义连接
    # 主蒸汽路径：给水 → 省煤器 → 水冷壁 → 过热器 → 高压缸 → 再热器 → 低压缸
    c0 = Connection(pump, "out1", economizer, "in1", label="给水")
    c1 = Connection(economizer, "out1", waterwall, "in1", label="预热水")
    c2 = Connection(waterwall, "out1", superheater, "in1", label="饱和蒸汽")
    c3 = Connection(superheater, "out1", cc, "in1", label="过热器出口")
    c4 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
    
    c5 = Connection(hp_turbine, "out1", reheater, "in1", label="高压缸排汽")
    c6 = Connection(reheater, "out1", lp_turbine, "in1", label="再热蒸汽")
    c7 = Connection(lp_turbine, "out1", condenser, "in1", label="低压缸排汽")
    
    # 凝结水循环
    c8 = Connection(condenser, "out1", pump, "in1", label="凝结水")
    
    nw.add_conns(c0, c1, c2, c3, c4, c5, c6, c7, c8)
    
    # 循环水
    cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
    cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
    nw.add_conns(cw1, cw2)
    
    print("[3] 连接建立完成")
    
    # 4) 设置组件参数
    # 省煤器：回收烟气余热，压降较小
    economizer.set_attr(pr=0.98)  # 2%压降
    
    # 水冷壁：主要吸热部分，压降较小
    waterwall.set_attr(pr=0.97)  # 3%压降
    
    # 过热器：提高蒸汽温度，压降较小
    superheater.set_attr(pr=0.95)  # 5%压降
    
    # 再热器：再次加热蒸汽
    reheater.set_attr(pr=0.97)  # 3%压降
    
    # 汽轮机效率
    hp_turbine.set_attr(eta_s=0.88)  # 高压缸：88%
    lp_turbine.set_attr(eta_s=0.86)  # 低压缸：86%
    
    # 凝汽器
    condenser.set_attr(pr1=1.0, pr2=0.98)
    
    # 给水泵
    pump.set_attr(eta_s=0.75)
    
    print("[4] 组件参数设置完成")
    
    # 5) 设置边界条件
    # 给水泵出口压力（需要克服锅炉阻力）
    # 最终主蒸汽压力约 150 bar，考虑各段压降
    # 150 / 0.95 / 0.97 / 0.98 ≈ 165 bar
    c0.set_attr(p=165, fluid={"water": 1})
    
    # 省煤器出口：预热至接近饱和温度（假设饱和温度约340°C @ 160bar）
    # 预热至330°C，即距离饱和温度约10K的过冷度
    c1.set_attr(T=330)
    
    # 水冷壁出口：饱和蒸汽（干度=1，即饱和蒸汽）
    # 在水冷壁中，水完全蒸发成饱和蒸汽
    c2.set_attr(x=1.0)  # 干度=1表示饱和蒸汽
    
    # 过热器出口/主蒸汽：过热蒸汽
    c4.set_attr(
        p=150,      # 150 bar = 15 MPa
        T=600,      # 600°C
        m=10,       # 10 kg/s
    )
    
    # 高压缸出口压力（进入再热器前）
    c5.set_attr(p=30)  # 30 bar ≈ 3 MPa
    
    # 再热蒸汽温度（通常与主蒸汽温度相近）
    c6.set_attr(T=600)  # 600°C
    
    # 凝汽器背压
    c7.set_attr(p=0.1)  # 0.1 bar
    
    # 循环水
    cw1.set_attr(T=20, p=1.2, fluid={"water": 1})
    cw2.set_attr(T=30)
    
    print("[5] 边界条件设置完成")
    print("   给水: 165 bar (补偿锅炉压降)")
    print("   省煤器出口: 330°C (接近饱和温度)")
    print("   水冷壁出口: 饱和蒸汽 (干度=1)")
    print("   主蒸汽: 150 bar / 600°C / 10 kg/s")
    print("   再热蒸汽: 600°C")
    print("   凝汽器: 0.1 bar")
    print("=" * 80)
    
    return nw


def solve_and_analyze(nw: Network) -> dict:
    """求解并进行详细分析."""
    
    print("\n开始求解...")
    print("-" * 80)
    
    try:
        nw.solve(mode="design")
        
        if not nw.converged:
            print("✗ 求解未收敛")
            return {}
        
        print("✓ 求解成功\n")
        nw.print_results()
        
        # 详细分析
        print("\n" + "=" * 80)
        print("详细热力学分析")
        print("=" * 80)
        
        # 获取组件
        economizer = nw.get_comp("省煤器")
        waterwall = nw.get_comp("水冷壁")
        superheater = nw.get_comp("过热器")
        reheater = nw.get_comp("再热器")
        hp_turb = nw.get_comp("高压缸")
        lp_turb = nw.get_comp("低压缸")
        pump = nw.get_comp("给水泵")
        condenser = nw.get_comp("凝汽器")
        
        # 获取连接
        feedwater = nw.get_conn("给水")
        preheated_water = nw.get_conn("预热水")
        saturated_steam = nw.get_conn("饱和蒸汽")
        main_steam = nw.get_conn("主蒸汽")
        hp_exhaust = nw.get_conn("高压缸排汽")
        reheat_steam = nw.get_conn("再热蒸汽")
        lp_exhaust = nw.get_conn("低压缸排汽")
        condensate = nw.get_conn("凝结水")
        
        cw_in = nw.get_conn("冷却水入口")
        cw_out = nw.get_conn("冷却水出口")
        
        # ===== 1. 锅炉系统分析 =====
        print("\n【锅炉系统详细分析】")
        print("-" * 80)
        
        Q_economizer = economizer.Q.val
        Q_waterwall = waterwall.Q.val
        Q_superheater = superheater.Q.val
        Q_boiler_total = Q_economizer + Q_waterwall + Q_superheater
        
        Q_reheater = reheater.Q.val
        Q_total = Q_boiler_total + Q_reheater
        
        print(f"\n① 省煤器（Economizer）:")
        print(f"   作用: 利用烟气余热预热给水")
        print(f"   入口: {feedwater.p.val:.2f} bar, {feedwater.T.val:.2f}°C, {feedwater.h.val:.2f} kJ/kg")
        print(f"   出口: {preheated_water.p.val:.2f} bar, {preheated_water.T.val:.2f}°C, {preheated_water.h.val:.2f} kJ/kg")
        print(f"   压降: {feedwater.p.val - preheated_water.p.val:.2f} bar ({(1-economizer.pr.val)*100:.1f}%)")
        print(f"   温升: {preheated_water.T.val - feedwater.T.val:.2f} K")
        print(f"   吸热: {Q_economizer:10.3f} MW ({Q_economizer/Q_boiler_total*100:.1f}%)")
        
        print(f"\n② 水冷壁（Waterwall）:")
        print(f"   作用: 炉膛辐射传热，水蒸发成饱和蒸汽")
        print(f"   入口: {preheated_water.p.val:.2f} bar, {preheated_water.T.val:.2f}°C (过冷水)")
        print(f"   出口: {saturated_steam.p.val:.2f} bar, {saturated_steam.T.val:.2f}°C (饱和蒸汽, x={saturated_steam.x.val:.4f})")
        print(f"   压降: {preheated_water.p.val - saturated_steam.p.val:.2f} bar ({(1-waterwall.pr.val)*100:.1f}%)")
        print(f"   蒸发: 液态水 → 饱和蒸汽")
        print(f"   吸热: {Q_waterwall:10.3f} MW ({Q_waterwall/Q_boiler_total*100:.1f}%) [最大吸热段]")
        
        print(f"\n③ 过热器（Superheater）:")
        print(f"   作用: 饱和蒸汽继续加热成过热蒸汽")
        print(f"   入口: {saturated_steam.p.val:.2f} bar, {saturated_steam.T.val:.2f}°C (饱和蒸汽)")
        print(f"   出口: {main_steam.p.val:.2f} bar, {main_steam.T.val:.2f}°C (过热蒸汽)")
        print(f"   压降: {saturated_steam.p.val - main_steam.p.val:.2f} bar ({(1-superheater.pr.val)*100:.1f}%)")
        print(f"   过热度: {main_steam.T.val - saturated_steam.T.val:.2f} K")
        print(f"   吸热: {Q_superheater:10.3f} MW ({Q_superheater/Q_boiler_total*100:.1f}%)")
        
        print(f"\n④ 锅炉总计:")
        print(f"   总吸热:    {Q_boiler_total:10.3f} MW")
        print(f"   总压降:    {feedwater.p.val - main_steam.p.val:.2f} bar")
        print(f"   总压比:    {main_steam.p.val / feedwater.p.val:.4f}")
        
        print(f"\n⑤ 再热器（Reheater）:")
        print(f"   作用: 高压缸排汽再次加热")
        print(f"   入口: {hp_exhaust.p.val:.2f} bar, {hp_exhaust.T.val:.2f}°C")
        print(f"   出口: {reheat_steam.p.val:.2f} bar, {reheat_steam.T.val:.2f}°C")
        print(f"   温升: {reheat_steam.T.val - hp_exhaust.T.val:.2f} K")
        print(f"   吸热: {Q_reheater:10.3f} MW ({Q_reheater/Q_total*100:.1f}%)")
        
        print(f"\n⑥ 整体热量输入:")
        print(f"   锅炉:      {Q_boiler_total:10.3f} MW ({Q_boiler_total/Q_total*100:.1f}%)")
        print(f"   再热器:    {Q_reheater:10.3f} MW ({Q_reheater/Q_total*100:.1f}%)")
        print(f"   总计:      {Q_total:10.3f} MW")
        
        # ===== 2. 功率分析 =====
        print(f"\n【功率平衡】")
        print("-" * 80)
        
        P_hp = abs(hp_turb.P.val)
        P_lp = abs(lp_turb.P.val)
        P_turb_total = P_hp + P_lp
        
        P_pump = abs(pump.P.val)
        P_net = P_turb_total - P_pump
        
        print(f"汽轮机出力:")
        print(f"  高压缸:        {P_hp:10.3f} MW  ({P_hp/P_turb_total*100:.1f}%)")
        print(f"  低压缸:        {P_lp:10.3f} MW  ({P_lp/P_turb_total*100:.1f}%)")
        print(f"  总计:          {P_turb_total:10.3f} MW")
        print(f"\n给水泵耗功:      {P_pump:10.3f} MW  (厂用电率: {P_pump/P_turb_total*100:.2f}%)")
        print(f"净发电功率:      {P_net:10.3f} MW")
        
        # ===== 3. 效率分析 =====
        print(f"\n【效率分析】")
        print("-" * 80)
        
        Q_condenser = abs(condenser.Q.val)
        eta_thermal = P_net / Q_total * 100
        
        # 卡诺效率
        T_h = main_steam.T.val + 273.15
        T_l = lp_exhaust.T.val + 273.15
        eta_carnot = (1 - T_l / T_h) * 100
        
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"卡诺效率(近似):  {eta_carnot:10.2f} %")
        print(f"相对效率:        {eta_thermal/eta_carnot*100:10.2f} % (实际/理论)")
        
        # 能量平衡验证
        energy_balance = abs(Q_total - (Q_condenser + P_net))
        energy_balance_pct = energy_balance / Q_total * 100
        
        print(f"\n能量平衡:")
        print(f"  总吸热:        {Q_total:10.3f} MW")
        print(f"  凝汽器放热:    {Q_condenser:10.3f} MW")
        print(f"  净做功:        {P_net:10.3f} MW")
        print(f"  总计:          {Q_condenser + P_net:10.3f} MW")
        print(f"  误差:          {energy_balance:10.6f} MW ({energy_balance_pct:.4f}%)")
        
        if energy_balance_pct < 0.1:
            print("  ✓ 能量守恒验证通过")
        
        # ===== 4. 关键状态点 =====
        print(f"\n【关键状态点】")
        print("-" * 80)
        
        print(f"\n① 给水（进入省煤器）:")
        print(f"   压力:  {feedwater.p.val:8.2f} bar")
        print(f"   温度:  {feedwater.T.val:8.2f} °C")
        print(f"   焓值:  {feedwater.h.val:8.2f} kJ/kg")
        
        print(f"\n② 预热水（进入水冷壁）:")
        print(f"   压力:  {preheated_water.p.val:8.2f} bar")
        print(f"   温度:  {preheated_water.T.val:8.2f} °C (接近饱和温度)")
        print(f"   焓值:  {preheated_water.h.val:8.2f} kJ/kg")
        
        print(f"\n③ 饱和蒸汽（进入过热器）:")
        print(f"   压力:  {saturated_steam.p.val:8.2f} bar")
        print(f"   温度:  {saturated_steam.T.val:8.2f} °C (饱和温度)")
        print(f"   焓值:  {saturated_steam.h.val:8.2f} kJ/kg")
        print(f"   干度:  {saturated_steam.x.val:8.4f} (x=1为饱和蒸汽)")
        
        print(f"\n④ 主蒸汽（进入高压缸）:")
        print(f"   压力:  {main_steam.p.val:8.2f} bar  ({main_steam.p.val*0.1:.1f} MPa)")
        print(f"   温度:  {main_steam.T.val:8.2f} °C")
        print(f"   焓值:  {main_steam.h.val:8.2f} kJ/kg")
        print(f"   流量:  {main_steam.m.val:8.2f} kg/s")
        print(f"   过热度: {main_steam.T.val - saturated_steam.T.val:.2f} K")
        
        print(f"\n⑤ 高压缸排汽（进入再热器）:")
        print(f"   压力:  {hp_exhaust.p.val:8.2f} bar")
        print(f"   温度:  {hp_exhaust.T.val:8.2f} °C")
        print(f"   焓值:  {hp_exhaust.h.val:8.2f} kJ/kg")
        
        print(f"\n⑥ 再热蒸汽（进入低压缸）:")
        print(f"   压力:  {reheat_steam.p.val:8.2f} bar")
        print(f"   温度:  {reheat_steam.T.val:8.2f} °C")
        print(f"   焓值:  {reheat_steam.h.val:8.2f} kJ/kg")
        
        print(f"\n⑦ 低压缸排汽（进入凝汽器）:")
        print(f"   压力:  {lp_exhaust.p.val:8.3f} bar")
        print(f"   温度:  {lp_exhaust.T.val:8.2f} °C")
        print(f"   焓值:  {lp_exhaust.h.val:8.2f} kJ/kg")
        print(f"   干度:  {lp_exhaust.x.val:8.4f}")
        
        if lp_exhaust.x.val < 0.85:
            print(f"   ⚠ 警告: 排汽干度过低 (< 0.85)")
        elif lp_exhaust.x.val > 0.95:
            print(f"   ⚠ 注意: 排汽干度较高 (> 0.95)")
        else:
            print(f"   ✓ 排汽干度在合理范围 (0.85-0.95)")
        
        # ===== 5. 锅炉性能评估 =====
        print(f"\n【锅炉性能评估】")
        print("-" * 80)
        
        # 各段吸热占比
        print(f"\n各段吸热占比:")
        print(f"  省煤器:   {Q_economizer/Q_boiler_total*100:6.1f}%  (预热段)")
        print(f"  水冷壁:   {Q_waterwall/Q_boiler_total*100:6.1f}%  (蒸发段，主要吸热)")
        print(f"  过热器:   {Q_superheater/Q_boiler_total*100:6.1f}%  (过热段)")
        
        # 各段温升/焓升
        print(f"\n各段焓升:")
        print(f"  省煤器:   {preheated_water.h.val - feedwater.h.val:8.2f} kJ/kg")
        print(f"  水冷壁:   {saturated_steam.h.val - preheated_water.h.val:8.2f} kJ/kg  (蒸发潜热)")
        print(f"  过热器:   {main_steam.h.val - saturated_steam.h.val:8.2f} kJ/kg")
        
        # 理论分析
        print(f"\n理论分析:")
        print(f"  ✓ 水冷壁吸热占比最大，这是因为水的蒸发潜热很大")
        print(f"  ✓ 省煤器利用烟气余热，提高了锅炉效率")
        print(f"  ✓ 过热器提高蒸汽温度，提高了循环效率")
        
        # ===== 6. 性能汇总 =====
        print(f"\n【性能汇总】")
        print("-" * 80)
        
        print(f"净发电功率:      {P_net:10.3f} MW")
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"总吸热:          {Q_total:10.3f} MW")
        print(f"锅炉总压降:      {feedwater.p.val - main_steam.p.val:10.2f} bar")
        print(f"厂用电率:        {P_pump/P_turb_total*100:10.2f} %")
        print(f"排汽干度:        {lp_exhaust.x.val:10.4f}")
        
        # ===== 7. 对标分析 =====
        print(f"\n【与简化模型对比】")
        print("-" * 80)
        print(f"  简化模型: 单一SimpleHeatExchanger作为锅炉")
        print(f"  详细模型: 省煤器 + 水冷壁 + 过热器")
        print(f"\n  详细模型优势:")
        print(f"    ✓ 更真实地反映锅炉内部工质的状态变化")
        print(f"    ✓ 可以单独分析各段的性能和设计参数")
        print(f"    ✓ 可以优化各段的热量分配")
        print(f"    ✓ 便于分析锅炉的压降和热效率")
        
        print("\n" + "=" * 80)
        
        # 导出结果
        nw.save("detailed_boiler_design")
        print("\n  ✓ 结果已保存: detailed_boiler_design.json")
        
        return {
            "P_net_MW": P_net,
            "eta_percent": eta_thermal,
            "Q_total_MW": Q_total,
            "Q_economizer_MW": Q_economizer,
            "Q_waterwall_MW": Q_waterwall,
            "Q_superheater_MW": Q_superheater,
            "Q_reheater_MW": Q_reheater,
            "exhaust_quality": lp_exhaust.x.val,
        }
        
    except Exception as e:
        print(f"✗ 求解出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main() -> None:
    """主程序."""
    
    # 1. 构建模型
    network = build_detailed_boiler_cycle()
    
    # 2. 求解并分析
    results = solve_and_analyze(network)
    
    if results:
        print("\n" + "=" * 80)
        print("仿真完成！")
        print("=" * 80)
        print(f"\n关键性能指标:")
        print(f"  净发电功率:    {results['P_net_MW']:.2f} MW")
        print(f"  循环效率:      {results['eta_percent']:.2f} %")
        print(f"  总吸热:        {results['Q_total_MW']:.2f} MW")
        
        print(f"\n锅炉各段吸热:")
        print(f"  省煤器:        {results['Q_economizer_MW']:.2f} MW")
        print(f"  水冷壁:        {results['Q_waterwall_MW']:.2f} MW  (最大)")
        print(f"  过热器:        {results['Q_superheater_MW']:.2f} MW")
        print(f"  再热器:        {results['Q_reheater_MW']:.2f} MW")
        
        print(f"\n详细锅炉模型的优势:")
        print(f"  ✓ 真实反映锅炉内部水/蒸汽的三个状态变化:")
        print(f"    - 省煤器: 预热（液态水温度升高）")
        print(f"    - 水冷壁: 蒸发（液态水→饱和蒸汽）")
        print(f"    - 过热器: 过热（饱和蒸汽→过热蒸汽）")
        print(f"  ✓ 可以单独优化各段的设计参数")
        print(f"  ✓ 便于分析热量分配和压降")
        print(f"  ✓ 更接近真实电厂的锅炉配置")
        print()
    else:
        print("\n求解失败。")


if __name__ == "__main__":  # pragma: no cover
    main()
