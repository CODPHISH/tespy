#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""余热锅炉-汽轮机 Rankine 循环基础示例.

本脚本基于 TESPy 官方教程中的 Rankine 循环示例，展示了通过余热
锅炉驱动汽轮机、经凝汽器和给水泵闭合循环的典型蒸汽动力系统。
运行过程：

1. 构建网络并定义组件
2. 建立连接并设置组件参数
3. 指定主蒸汽、冷却水等边界条件
4. 求解设计工况并输出主要结果

读者可在此基础上扩展再热、回热、抽汽等更复杂的模型。
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

    print("\n" + "=" * 70)
    print("TESPy 余热锅炉-汽轮机 Rankine 循环示例")
    print("=" * 70)

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
    boiler.set_attr(pr=0.90)
    turbine.set_attr(eta_s=0.90)
    condenser.set_attr(pr1=1.0, pr2=0.98)
    pump.set_attr(eta_s=0.75)
    print("[4] 组件参数设置完成")

    # 5) 设置连接参数（设计点）
    c1.set_attr(T=600, p=150, m=10, fluid={"water": 1})
    c2.set_attr(p=0.1)

    cw1.set_attr(T=20, p=1.2, fluid={"water": 1})
    cw2.set_attr(T=30)
    print("[5] 边界条件：主蒸汽 150 bar / 600°C / 10 kg/s, 凝汽器 0.1 bar, 冷却水 20°C")
    print("=" * 70)

    return nw


def solve_design_case(nw: Network) -> None:
    """求解设计工况并打印主要结果."""

    print("\n开始求解设计工况 ...")
    nw.solve(mode="design")
    nw.print_results()
    print("求解完成。")


def summarize_performance(nw: Network) -> None:
    """输出系统性能摘要."""

    turbine = nw.get_comp("汽轮机")
    pump = nw.get_comp("给水泵")
    boiler = nw.get_comp("锅炉")

    P_turb = abs(turbine.P.val)
    P_pump = abs(pump.P.val)
    Q_boiler = boiler.Q.val
    P_net = P_turb - P_pump
    eta = P_net / Q_boiler * 100

    print("\n" + "-" * 70)
    print("性能汇总")
    print("-" * 70)
    print(f"汽轮机出力: {P_turb:8.2f} MW")
    print(f"给水泵耗功: {P_pump:8.4f} MW")
    print(f"锅炉吸热:   {Q_boiler:8.2f} MW")
    print(f"净发电功率: {P_net:8.2f} MW")
    print(f"热效率:     {eta:8.2f} %")
    print("-" * 70)


def main() -> None:
    """主程序入口."""

    nw = build_rankine_system()
    solve_design_case(nw)
    summarize_performance(nw)
    nw.save("waste_heat_rankine_design.json")
    print("\n设计点已保存为 waste_heat_rankine_design.json")


if __name__ == "__main__":  # pragma: no cover
    main()
