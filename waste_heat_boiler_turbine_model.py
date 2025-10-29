#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""余热锅炉-汽轮机 Rankine 循环仿真模型（含详细分析）.

本脚本基于 TESPy 构建了一个典型的蒸汽动力循环系统，
并增加了详细的热力学分析和验证功能。

系统组成：
1. 锅炉（蒸汽发生器）
2. 汽轮机（膨胀做功）
3. 凝汽器（冷凝成液态）
4. 给水泵（增压）
5. 循环水系统

运行过程：
1. 构建网络并定义组件
2. 设置边界条件
3. 求解设计工况
4. 进行详细的热力学分析和验证
5. 输出结果并保存

作者：基于 TESPy 官方教程改编
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


def build_rankine_system() -> Network:
    """构建并返回 Rankine 循环网络对象."""

    print("\n" + "=" * 76)
    print("TESPy 余热锅炉-汽轮机 Rankine 循环仿真（含详细分析）")
    print("=" * 76)

    # 1) 创建网络
    nw = Network(iterinfo=False)
    nw.units.set_defaults(
        temperature="degC",
        pressure="bar",
        enthalpy="kJ/kg",
        power="MW",
        heat="MW",
    )
    print("[1] 网络初始化完成 (单位: °C, bar, kJ/kg, MW)")

    # 2) 定义组件
    cc = CycleCloser("循环闭合器")
    boiler = SimpleHeatExchanger("锅炉")
    turbine = Turbine("汽轮机")
    condenser = Condenser("凝汽器")
    pump = Pump("给水泵")

    cw_src = Source("循环水入口")
    cw_snk = Sink("循环水出口")
    print("[2] 组件定义完成：锅炉 / 汽轮机 / 凝汽器 / 给水泵 / 循环水")

    # 3) 定义连接
    c1 = Connection(cc, "out1", turbine, "in1", label="主蒸汽")
    c2 = Connection(turbine, "out1", condenser, "in1", label="排汽")
    c3 = Connection(condenser, "out1", pump, "in1", label="凝结水")
    c4 = Connection(pump, "out1", boiler, "in1", label="给水")
    c0 = Connection(boiler, "out1", cc, "in1", label="锅炉出口")

    nw.add_conns(c1, c2, c3, c4, c0)

    cw1 = Connection(cw_src, "out1", condenser, "in2", label="冷却水入口")
    cw2 = Connection(condenser, "out2", cw_snk, "in1", label="冷却水出口")
    nw.add_conns(cw1, cw2)
    print("[3] 连接建立完成")

    # 4) 设置组件参数
    boiler.set_attr(pr=0.90)  # 锅炉压降10%（典型值5-15%）
    turbine.set_attr(eta_s=0.90)  # 汽轮机等熵效率90%（典型值85-92%）
    condenser.set_attr(pr1=1.0, pr2=0.98)  # 凝汽器压降（蒸汽侧无，冷却水侧2%）
    pump.set_attr(eta_s=0.75)  # 给水泵效率75%（典型值70-85%）
    print("[4] 组件参数设置完成")

    # 5) 设置连接参数（设计点）
    # 主蒸汽：150 bar (15 MPa), 600°C - 典型亚临界参数
    c1.set_attr(T=600, p=150, m=10, fluid={"water": 1})
    
    # 凝汽器背压：0.1 bar (10 kPa) - 对应约46°C饱和温度
    c2.set_attr(p=0.1)

    # 循环水：20°C入口，30°C出口（温升10K）
    cw1.set_attr(T=20, p=1.2, fluid={"water": 1})
    cw2.set_attr(T=30)
    
    print("[5] 边界条件设置完成")
    print("   主蒸汽: 150 bar / 600°C / 10 kg/s (亚临界参数)")
    print("   凝汽器: 0.1 bar (高真空，约46°C饱和)")
    print("   循环水: 20°C → 30°C (温升10K)")
    print("=" * 76)

    return nw


def solve_design_case(nw: Network) -> None:
    """求解设计工况并打印主要结果."""

    print("\n开始求解设计工况 ...")
    print("-" * 76)
    nw.solve(mode="design")
    
    if nw.converged:
        print("✓ 求解收敛成功\n")
        nw.print_results()
    else:
        print("✗ 求解未收敛")
    
    print("求解完成。")


def detailed_analysis(nw: Network) -> None:
    """详细的热力学分析和验证."""
    
    print("\n" + "=" * 76)
    print("详细热力学分析与验证")
    print("=" * 76)
    
    # 获取组件
    turbine = nw.get_comp("汽轮机")
    pump = nw.get_comp("给水泵")
    boiler = nw.get_comp("锅炉")
    condenser = nw.get_comp("凝汽器")
    
    # 获取关键连接
    main_steam = nw.get_conn("主蒸汽")
    exhaust = nw.get_conn("排汽")
    condensate = nw.get_conn("凝结水")
    feedwater = nw.get_conn("给水")
    
    cw_in = nw.get_conn("冷却水入口")
    cw_out = nw.get_conn("冷却水出口")
    
    # ===== 1. 功率分析 =====
    print("\n【功率平衡】")
    print("-" * 76)
    
    P_turb = abs(turbine.P.val)  # MW
    P_pump = abs(pump.P.val)  # MW
    P_net = P_turb - P_pump
    
    print(f"汽轮机出力:    {P_turb:10.3f} MW")
    print(f"给水泵耗功:    {P_pump:10.3f} MW  (厂用电率: {P_pump/P_turb*100:.2f}%)")
    print(f"净发电功率:    {P_net:10.3f} MW")
    
    # ===== 2. 热量分析 =====
    print(f"\n【热量平衡】")
    print("-" * 76)
    
    Q_boiler = boiler.Q.val  # MW
    Q_condenser = abs(condenser.Q.val)  # MW
    
    print(f"锅炉吸热:      {Q_boiler:10.3f} MW")
    print(f"凝汽器放热:    {Q_condenser:10.3f} MW")
    
    # 能量平衡验证
    energy_in = Q_boiler
    energy_out = P_net + Q_condenser
    energy_balance_error = abs(energy_in - energy_out)
    energy_balance_pct = energy_balance_error / energy_in * 100
    
    print(f"\n能量输入:      {energy_in:10.3f} MW")
    print(f"能量输出:      {energy_out:10.3f} MW  (净功 + 凝汽器放热)")
    print(f"平衡误差:      {energy_balance_error:10.6f} MW  ({energy_balance_pct:.4f}%)")
    
    if energy_balance_pct < 0.01:
        print("  ✓ 能量守恒验证通过（误差 < 0.01%）")
    else:
        print(f"  ⚠ 能量平衡误差: {energy_balance_pct:.4f}%")
    
    # ===== 3. 效率分析 =====
    print(f"\n【效率分析】")
    print("-" * 76)
    
    eta_thermal = P_net / Q_boiler * 100  # 循环热效率
    
    # 理论卡诺效率（近似）
    T_h = main_steam.T.val + 273.15  # K
    T_l = exhaust.T.val + 273.15  # K
    eta_carnot = (1 - T_l / T_h) * 100
    
    print(f"循环热效率:    {eta_thermal:10.2f} %")
    print(f"卡诺效率(近似): {eta_carnot:10.2f} %  (基于最高/最低温度)")
    print(f"相对效率:      {eta_thermal/eta_carnot*100:10.2f} %  (实际/卡诺)")
    
    # 与典型值对比
    print(f"\n对标分析:")
    print(f"  典型亚临界机组热效率: 35-42%")
    if 35 <= eta_thermal <= 42:
        print(f"  ✓ 本模型效率 {eta_thermal:.2f}% 在合理范围内")
    elif eta_thermal < 35:
        print(f"  ⚠ 效率偏低，可能需要优化参数或增加回热")
    else:
        print(f"  ⚠ 效率偏高，请检查模型设置")
    
    # ===== 4. 关键状态点分析 =====
    print(f"\n【关键状态点】")
    print("-" * 76)
    
    print(f"\n① 主蒸汽（锅炉出口 → 汽轮机入口）:")
    print(f"   压力:  {main_steam.p.val:8.2f} bar  ({main_steam.p.val*0.1:.1f} MPa)")
    print(f"   温度:  {main_steam.T.val:8.2f} °C")
    print(f"   焓值:  {main_steam.h.val:8.2f} kJ/kg")
    print(f"   流量:  {main_steam.m.val:8.2f} kg/s")
    
    print(f"\n② 汽轮机排汽（进入凝汽器）:")
    print(f"   压力:  {exhaust.p.val:8.3f} bar  ({exhaust.p.val*100:.1f} kPa)")
    print(f"   温度:  {exhaust.T.val:8.2f} °C")
    print(f"   焓值:  {exhaust.h.val:8.2f} kJ/kg")
    print(f"   干度:  {exhaust.x.val:8.4f}")
    
    # 排汽干度检查
    if exhaust.x.val < 0.85:
        print(f"   ⚠ 警告: 排汽干度过低 (< 0.85)，可能导致末级叶片水蚀")
    elif exhaust.x.val > 0.95:
        print(f"   ⚠ 注意: 排汽干度较高 (> 0.95)，凝汽器负荷较大")
    else:
        print(f"   ✓ 排汽干度在合理范围 (0.85-0.95)")
    
    print(f"\n③ 凝结水（凝汽器出口）:")
    print(f"   压力:  {condensate.p.val:8.3f} bar")
    print(f"   温度:  {condensate.T.val:8.2f} °C")
    print(f"   焓值:  {condensate.h.val:8.2f} kJ/kg")
    
    print(f"\n④ 给水（进入锅炉）:")
    print(f"   压力:  {feedwater.p.val:8.2f} bar")
    print(f"   温度:  {feedwater.T.val:8.2f} °C")
    print(f"   焓值:  {feedwater.h.val:8.2f} kJ/kg")
    
    # ===== 5. 循环水分析 =====
    print(f"\n【循环水系统】")
    print("-" * 76)
    
    m_cw = cw_in.m.val  # kg/s
    T_cw_in = cw_in.T.val  # °C
    T_cw_out = cw_out.T.val  # °C
    delta_T_cw = T_cw_out - T_cw_in  # K
    
    print(f"循环水流量:    {m_cw:10.2f} kg/s")
    print(f"入口温度:      {T_cw_in:10.2f} °C")
    print(f"出口温度:      {T_cw_out:10.2f} °C")
    print(f"温升:          {delta_T_cw:10.2f} K")
    
    # 凝汽器端差
    ttd_u = condenser.ttd_u.val  # 上端差
    ttd_l = condenser.ttd_l.val  # 下端差
    
    print(f"\n凝汽器端差:")
    print(f"  上端差(TTD_u): {ttd_u:8.2f} K  (饱和温度 - 冷却水出口温度)")
    print(f"  下端差(TTD_l): {ttd_l:8.2f} K  (凝结水温度 - 冷却水入口温度)")
    
    # ===== 6. 热力学第一/第二定律验证 =====
    print(f"\n【热力学合理性检查】")
    print("-" * 76)
    
    checks_passed = 0
    checks_total = 0
    
    # 检查1: 能量守恒
    checks_total += 1
    if energy_balance_pct < 0.1:
        print("✓ 能量守恒满足（误差 < 0.1%）")
        checks_passed += 1
    else:
        print(f"✗ 能量平衡误差 {energy_balance_pct:.3f}% 较大")
    
    # 检查2: 汽轮机做功过程温度/压力下降
    checks_total += 1
    if main_steam.T.val > exhaust.T.val and main_steam.p.val > exhaust.p.val:
        print("✓ 汽轮机膨胀过程温度和压力单调下降")
        checks_passed += 1
    else:
        print("✗ 汽轮机状态变化异常")
    
    # 检查3: 排汽干度合理
    checks_total += 1
    if 0.80 <= exhaust.x.val <= 0.96:
        print(f"✓ 排汽干度合理: x = {exhaust.x.val:.4f}")
        checks_passed += 1
    else:
        print(f"⚠ 排汽干度需关注: x = {exhaust.x.val:.4f}")
    
    # 检查4: 效率合理
    checks_total += 1
    if 30 <= eta_thermal <= 45:
        print(f"✓ 循环效率在合理范围: η = {eta_thermal:.2f}%")
        checks_passed += 1
    else:
        print(f"⚠ 循环效率异常: η = {eta_thermal:.2f}%")
    
    # 检查5: 循环水温升合理
    checks_total += 1
    if 5 <= delta_T_cw <= 15:
        print(f"✓ 循环水温升合理: ΔT = {delta_T_cw:.1f} K")
        checks_passed += 1
    else:
        print(f"⚠ 循环水温升异常: ΔT = {delta_T_cw:.1f} K")
    
    print(f"\n验证结果: {checks_passed}/{checks_total} 项通过")
    
    if checks_passed == checks_total:
        print("✓ 模型通过所有热力学验证")
    elif checks_passed >= checks_total * 0.8:
        print("⚠ 模型基本合理，部分指标需关注")
    else:
        print("✗ 模型存在较多问题，建议检查参数设置")
    
    # ===== 7. 性能汇总 =====
    print(f"\n【性能汇总】")
    print("-" * 76)
    
    print(f"净发电功率:    {P_net:10.3f} MW")
    print(f"循环热效率:    {eta_thermal:10.2f} %")
    print(f"总吸热:        {Q_boiler:10.3f} MW")
    print(f"总放热:        {Q_condenser:10.3f} MW")
    print(f"厂用电率:      {P_pump/P_turb*100:10.2f} %")
    print(f"排汽干度:      {exhaust.x.val:10.4f}")
    
    print("\n" + "=" * 76)


def export_results(nw: Network) -> None:
    """导出结果."""
    
    print("\n导出结果...")
    nw.save("waste_heat_rankine_design.json")
    print("  ✓ 设计点: waste_heat_rankine_design.json")


def main() -> None:
    """主程序入口."""

    # 1. 构建模型
    nw = build_rankine_system()
    
    # 2. 求解
    solve_design_case(nw)
    
    # 3. 详细分析
    if nw.converged:
        detailed_analysis(nw)
        export_results(nw)
        print("\n仿真完成！\n")
    else:
        print("\n求解失败，请检查模型参数。\n")


if __name__ == "__main__":  # pragma: no cover
    main()
