#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""再热Rankine循环发电厂仿真模型.

相比基础模型的改进：
1. 双缸汽轮机（高压缸 + 低压缸）
2. 一次再热循环
3. 效率提升约2-4%
4. 排汽干度显著改善

这是一个典型的300-600MW亚临界火电机组配置。
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


def build_reheat_cycle() -> Network:
    """构建再热Rankine循环."""
    
    print("\n" + "=" * 78)
    print("再热Rankine循环发电厂仿真（含详细对比分析）")
    print("=" * 78)
    print("\n系统配置：")
    print("  • 双缸汽轮机（高压缸 + 低压缸）")
    print("  • 一次再热循环")
    print("  • 与简单循环对比效率提升")
    print("=" * 78)
    
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
    boiler = SimpleHeatExchanger("锅炉")
    reheater = SimpleHeatExchanger("再热器")
    
    # 双缸汽轮机
    hp_turbine = Turbine("高压缸")
    lp_turbine = Turbine("低压缸")
    
    condenser = Condenser("凝汽器")
    pump = Pump("给水泵")
    
    # 循环水
    cw_src = Source("循环水入口")
    cw_snk = Sink("循环水出口")
    
    print("[2] 组件定义完成：锅炉/再热器/高压缸/低压缸/凝汽器/给水泵")
    
    # 3) 定义连接
    # 主蒸汽路径：锅炉 → 高压缸 → 再热器 → 低压缸
    c0 = Connection(boiler, "out1", cc, "in1", label="锅炉出口")
    c1 = Connection(cc, "out1", hp_turbine, "in1", label="主蒸汽")
    c2 = Connection(hp_turbine, "out1", reheater, "in1", label="高压缸排汽")
    c3 = Connection(reheater, "out1", lp_turbine, "in1", label="再热蒸汽")
    c4 = Connection(lp_turbine, "out1", condenser, "in1", label="低压缸排汽")
    
    # 凝结水循环
    c5 = Connection(condenser, "out1", pump, "in1", label="凝结水")
    c6 = Connection(pump, "out1", boiler, "in1", label="给水")
    
    nw.add_conns(c0, c1, c2, c3, c4, c5, c6)
    
    # 循环水
    cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
    cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
    nw.add_conns(cw1, cw2)
    
    print("[3] 连接建立完成")
    
    # 4) 设置组件参数
    # 锅炉和再热器
    boiler.set_attr(pr=0.95)  # 5%压降
    reheater.set_attr(pr=0.97)  # 3%压降
    
    # 汽轮机效率（考虑不同缸段特性）
    hp_turbine.set_attr(eta_s=0.88)  # 高压缸：88%
    lp_turbine.set_attr(eta_s=0.86)  # 低压缸：86%（湿蒸汽区效率略低）
    
    # 凝汽器
    condenser.set_attr(pr1=1.0, pr2=0.98)
    
    # 给水泵
    pump.set_attr(eta_s=0.75)
    
    print("[4] 组件参数设置完成")
    
    # 5) 设置边界条件（与基础模型相同，便于对比）
    # 主蒸汽参数
    c1.set_attr(
        p=150,      # 150 bar = 15 MPa
        T=600,      # 600°C
        m=10,       # 10 kg/s
        fluid={"water": 1}
    )
    
    # 高压缸出口压力（进入再热器前）
    c2.set_attr(p=30)  # 30 bar ≈ 3 MPa（典型再热压力）
    
    # 再热蒸汽温度（通常与主蒸汽温度相近）
    c3.set_attr(T=600)  # 600°C
    
    # 凝汽器背压
    c4.set_attr(p=0.1)  # 0.1 bar
    
    # 循环水（与基础模型相同）
    cw1.set_attr(T=20, p=1.2, fluid={"water": 1})
    cw2.set_attr(T=30)
    
    print("[5] 边界条件设置完成")
    print("   主蒸汽: 150 bar / 600°C / 10 kg/s（与基础模型相同）")
    print("   再热蒸汽: 600°C")
    print("   凝汽器: 0.1 bar")
    print("   循环水: 20°C → 30°C")
    print("=" * 78)
    
    return nw


def solve_and_analyze(nw: Network) -> dict:
    """求解并进行详细分析."""
    
    print("\n开始求解...")
    print("-" * 78)
    
    try:
        nw.solve(mode="design")
        
        if not nw.converged:
            print("✗ 求解未收敛")
            return {}
        
        print("✓ 求解成功\n")
        nw.print_results()
        
        # 详细分析
        print("\n" + "=" * 78)
        print("详细热力学分析与对比")
        print("=" * 78)
        
        # 获取组件
        boiler = nw.get_comp("锅炉")
        reheater = nw.get_comp("再热器")
        hp_turb = nw.get_comp("高压缸")
        lp_turb = nw.get_comp("低压缸")
        pump = nw.get_comp("给水泵")
        condenser = nw.get_comp("凝汽器")
        
        # 获取连接
        main_steam = nw.get_conn("主蒸汽")
        hp_exhaust = nw.get_conn("高压缸排汽")
        reheat_steam = nw.get_conn("再热蒸汽")
        lp_exhaust = nw.get_conn("低压缸排汽")
        feedwater = nw.get_conn("给水")
        
        cw_in = nw.get_conn("冷却水入口")
        cw_out = nw.get_conn("冷却水出口")
        
        # ===== 1. 功率分析 =====
        print("\n【功率平衡】")
        print("-" * 78)
        
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
        
        # ===== 2. 热量分析 =====
        print(f"\n【热量平衡】")
        print("-" * 78)
        
        Q_boiler = boiler.Q.val
        Q_reheater = reheater.Q.val
        Q_total = Q_boiler + Q_reheater
        
        Q_condenser = abs(condenser.Q.val)
        
        print(f"热量输入:")
        print(f"  锅炉吸热:      {Q_boiler:10.3f} MW  ({Q_boiler/Q_total*100:.1f}%)")
        print(f"  再热器吸热:    {Q_reheater:10.3f} MW  ({Q_reheater/Q_total*100:.1f}%)")
        print(f"  总吸热:        {Q_total:10.3f} MW")
        print(f"\n热量输出:")
        print(f"  凝汽器放热:    {Q_condenser:10.3f} MW")
        print(f"  净做功:        {P_net:10.3f} MW")
        print(f"  总计:          {Q_condenser + P_net:10.3f} MW")
        
        # 能量平衡验证
        energy_balance = abs(Q_total - (Q_condenser + P_net))
        energy_balance_pct = energy_balance / Q_total * 100
        
        print(f"\n能量平衡误差:    {energy_balance:10.6f} MW ({energy_balance_pct:.4f}%)")
        
        if energy_balance_pct < 0.1:
            print("  ✓ 能量守恒验证通过")
        
        # ===== 3. 效率分析 =====
        print(f"\n【效率分析】")
        print("-" * 78)
        
        eta_thermal = P_net / Q_total * 100
        
        # 卡诺效率
        T_h = main_steam.T.val + 273.15
        T_l = lp_exhaust.T.val + 273.15
        eta_carnot = (1 - T_l / T_h) * 100
        
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"卡诺效率(近似):  {eta_carnot:10.2f} %")
        print(f"相对效率:        {eta_thermal/eta_carnot*100:10.2f} % (实际/理论)")
        
        # 与基础模型对比（基础模型实测 38.55%）
        eta_simple = 38.55
        eta_improvement_abs = eta_thermal - eta_simple
        eta_improvement_rel = eta_improvement_abs / eta_simple * 100
        
        print(f"\n与简单循环对比:")
        print(f"  简单循环效率:  {eta_simple:.2f}%  (基础模型实测)")
        print(f"  再热循环效率:  {eta_thermal:.2f}%")
        print(f"  绝对提升:      {eta_improvement_abs:+.2f}%")
        print(f"  相对提升:      {eta_improvement_rel:+.1f}%")
        
        if 2 <= eta_improvement_abs <= 4:
            print(f"  ✓ 效率提升符合理论预期（2-4%）")
        elif eta_improvement_abs > 4:
            print(f"  ⚠ 效率提升超出典型范围，建议检查参数")
        else:
            print(f"  ⚠ 效率提升低于预期，可能需要优化再热参数")
        
        # ===== 4. 关键状态点 =====
        print(f"\n【关键状态点】")
        print("-" * 78)
        
        print(f"\n① 主蒸汽（进入高压缸）:")
        print(f"   压力:  {main_steam.p.val:8.2f} bar  ({main_steam.p.val*0.1:.1f} MPa)")
        print(f"   温度:  {main_steam.T.val:8.2f} °C")
        print(f"   焓值:  {main_steam.h.val:8.2f} kJ/kg")
        print(f"   流量:  {main_steam.m.val:8.2f} kg/s")
        
        print(f"\n② 高压缸排汽（进入再热器）:")
        print(f"   压力:  {hp_exhaust.p.val:8.2f} bar  ({hp_exhaust.p.val*0.1:.2f} MPa)")
        print(f"   温度:  {hp_exhaust.T.val:8.2f} °C")
        print(f"   焓值:  {hp_exhaust.h.val:8.2f} kJ/kg")
        
        # 高压缸膨胀比
        expansion_ratio_hp = main_steam.p.val / hp_exhaust.p.val
        print(f"   高压缸膨胀比: {expansion_ratio_hp:.2f}")
        
        print(f"\n③ 再热蒸汽（进入低压缸）:")
        print(f"   压力:  {reheat_steam.p.val:8.2f} bar")
        print(f"   温度:  {reheat_steam.T.val:8.2f} °C")
        print(f"   焓值:  {reheat_steam.h.val:8.2f} kJ/kg")
        
        # 再热温升
        reheat_temp_rise = reheat_steam.T.val - hp_exhaust.T.val
        print(f"   再热温升: {reheat_temp_rise:.2f} K")
        
        print(f"\n④ 低压缸排汽（进入凝汽器）:")
        print(f"   压力:  {lp_exhaust.p.val:8.3f} bar  ({lp_exhaust.p.val*100:.1f} kPa)")
        print(f"   温度:  {lp_exhaust.T.val:8.2f} °C")
        print(f"   焓值:  {lp_exhaust.h.val:8.2f} kJ/kg")
        print(f"   干度:  {lp_exhaust.x.val:8.4f}")
        
        # 低压缸膨胀比
        expansion_ratio_lp = reheat_steam.p.val / lp_exhaust.p.val
        print(f"   低压缸膨胀比: {expansion_ratio_lp:.2f}")
        
        # 排汽干度检查
        if lp_exhaust.x.val < 0.85:
            print(f"   ⚠ 警告: 排汽干度过低 (< 0.85)，可能导致叶片水蚀")
        elif lp_exhaust.x.val > 0.95:
            print(f"   ⚠ 注意: 排汽干度较高 (> 0.95)")
        else:
            print(f"   ✓ 排汽干度在合理范围 (0.85-0.95)")
        
        print(f"\n⑤ 给水（进入锅炉）:")
        print(f"   压力:  {feedwater.p.val:8.2f} bar")
        print(f"   温度:  {feedwater.T.val:8.2f} °C")
        print(f"   焓值:  {feedwater.h.val:8.2f} kJ/kg")
        
        # ===== 5. 循环水分析 =====
        print(f"\n【循环水系统】")
        print("-" * 78)
        
        m_cw = cw_in.m.val
        T_cw_in = cw_in.T.val
        T_cw_out = cw_out.T.val
        delta_T_cw = T_cw_out - T_cw_in
        
        print(f"循环水流量:      {m_cw:10.2f} kg/s")
        print(f"入口温度:        {T_cw_in:10.2f} °C")
        print(f"出口温度:        {T_cw_out:10.2f} °C")
        print(f"温升:            {delta_T_cw:10.2f} K")
        
        # ===== 6. 再热效果评估 =====
        print(f"\n【再热效果评估】")
        print("-" * 78)
        
        # 高压缸和低压缸功率分配
        power_distribution = P_hp / (P_hp + P_lp) * 100
        print(f"高压缸功率占比:  {power_distribution:.1f}%")
        print(f"低压缸功率占比:  {100 - power_distribution:.1f}%")
        
        # 再热器热量占比
        reheat_heat_ratio = Q_reheater / Q_total * 100
        print(f"再热器吸热占比:  {reheat_heat_ratio:.1f}%")
        
        # 排汽干度改善（与简单循环对比）
        # 简单循环排汽干度约 0.865（基础模型实测）
        x_simple = 0.8655
        x_reheat = lp_exhaust.x.val
        x_improvement = x_reheat - x_simple
        
        print(f"\n排汽干度改善:")
        print(f"  简单循环:      {x_simple:.4f}")
        print(f"  再热循环:      {x_reheat:.4f}")
        print(f"  改善:          {x_improvement:+.4f}")
        
        if x_improvement > 0.01:
            print(f"  ✓ 排汽干度显著改善，减少叶片水蚀风险")
        
        # ===== 7. 性能汇总 =====
        print(f"\n【性能汇总】")
        print("-" * 78)
        
        print(f"净发电功率:      {P_net:10.3f} MW")
        print(f"循环热效率:      {eta_thermal:10.2f} %")
        print(f"总吸热:          {Q_total:10.3f} MW")
        print(f"厂用电率:        {P_pump/P_turb_total*100:10.2f} %")
        print(f"排汽干度:        {lp_exhaust.x.val:10.4f}")
        print(f"效率提升:        {eta_improvement_abs:+10.2f} % (vs 简单循环)")
        
        # ===== 8. 对标分析 =====
        print(f"\n【对标分析】")
        print("-" * 78)
        print(f"  项目                    本模型      典型值")
        print(f"  循环形式                再热       再热")
        print(f"  主蒸汽压力              {main_steam.p.val:.0f} bar     140-180 bar")
        print(f"  主蒸汽温度              {main_steam.T.val:.0f}°C       535-565°C")
        print(f"  再热温度                {reheat_steam.T.val:.0f}°C       535-565°C")
        print(f"  凝汽器真空              {(1.01325-lp_exhaust.p.val)*100:.1f} kPa   -90 to -95 kPa")
        print(f"  循环热效率              {eta_thermal:.1f}%        40-44%")
        print(f"  排汽干度                {lp_exhaust.x.val:.3f}      0.88-0.94")
        print(f"  效率提升                {eta_improvement_abs:+.1f}%        +2 to +4%")
        
        if 40 <= eta_thermal <= 44:
            print(f"\n  ✓ 本模型效率 {eta_thermal:.2f}% 在典型再热机组范围内")
        elif 38 <= eta_thermal < 40:
            print(f"\n  ⚠ 效率 {eta_thermal:.2f}% 略低于典型再热机组")
        else:
            print(f"\n  ✓ 效率 {eta_thermal:.2f}% 表现良好")
        
        print("\n" + "=" * 78)
        
        # 导出结果
        nw.save("reheat_cycle_design")
        print("\n  ✓ 结果已保存: reheat_cycle_design.json")
        
        return {
            "P_net_MW": P_net,
            "eta_percent": eta_thermal,
            "eta_improvement": eta_improvement_abs,
            "exhaust_quality": lp_exhaust.x.val,
            "Q_total_MW": Q_total,
        }
        
    except Exception as e:
        print(f"✗ 求解出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main() -> None:
    """主程序."""
    
    # 1. 构建模型
    network = build_reheat_cycle()
    
    # 2. 求解并分析
    results = solve_and_analyze(network)
    
    if results:
        print("\n" + "=" * 78)
        print("仿真完成！")
        print("=" * 78)
        print(f"\n关键性能指标:")
        print(f"  净发电功率:    {results['P_net_MW']:.2f} MW")
        print(f"  循环效率:      {results['eta_percent']:.2f} %")
        print(f"  效率提升:      {results['eta_improvement']:+.2f} % (相比简单循环)")
        print(f"  排汽干度:      {results['exhaust_quality']:.4f}")
        print(f"\n再热循环的优势:")
        print(f"  ✓ 循环效率提高 {results['eta_improvement']:.2f}%")
        print(f"  ✓ 排汽干度改善，减少叶片水蚀")
        print(f"  ✓ 适用于中大型火电机组")
        print()
    else:
        print("\n求解失败。")


if __name__ == "__main__":  # pragma: no cover
    main()
