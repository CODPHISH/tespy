#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析博士提供的设计模式数据

此脚本分析 boiler-turbine_design_state 目录中的数据，
提取关键参数和性能指标，为Stage2模型改进提供参考。
"""

import json
import pandas as pd
from pathlib import Path
import numpy as np


def load_phd_design_data():
    """加载博士提供的设计数据."""
    data_dir = Path(__file__).parent / "boiler-turbine_design_state"
    
    # 读取连接数据
    connections = pd.read_csv(
        data_dir / "connections.csv",
        sep=';',
        encoding='utf-8'
    )
    
    # 读取换热器数据
    heat_exchangers = pd.read_csv(
        data_dir / "components" / "HeatExchanger.csv",
        sep=';',
        index_col=0,
        encoding='utf-8'
    )
    
    # 读取汽轮机数据
    turbines = pd.read_csv(
        data_dir / "components" / "Turbine.csv",
        sep=';',
        index_col=0,
        encoding='utf-8'
    )
    
    # 读取泵数据
    pumps = pd.read_csv(
        data_dir / "components" / "Pump.csv",
        sep=';',
        index_col=0,
        encoding='utf-8'
    )
    
    # 读取燃烧室数据
    combustion = pd.read_csv(
        data_dir / "components" / "DiabaticCombustionChamber.csv",
        sep=';',
        index_col=0,
        encoding='utf-8'
    )
    
    # 读取busses（功率）数据
    with open(data_dir / "busses.json", 'r', encoding='utf-8') as f:
        busses = json.load(f)
    
    return {
        'connections': connections,
        'heat_exchangers': heat_exchangers,
        'turbines': turbines,
        'pumps': pumps,
        'combustion': combustion,
        'busses': busses,
    }


def analyze_main_steam_parameters(data):
    """分析主蒸汽参数."""
    conn = data['connections']
    
    # 查找主蒸汽连接
    main_steam = conn[conn.iloc[:, 0] == '1#发电锅炉_主蒸汽'].iloc[0]
    
    print("\n" + "=" * 80)
    print("主蒸汽参数")
    print("=" * 80)
    print(f"流量:    {main_steam['m']:.2f} t/h  ({main_steam['m']/3.6:.2f} kg/s)")
    print(f"压力:    {main_steam['p']:.2f} bar")
    print(f"温度:    {main_steam['T']:.2f} °C")
    print(f"焓值:    {main_steam['h']:.2f} kJ/kg")
    
    return {
        'flow_t_h': main_steam['m'],
        'flow_kg_s': main_steam['m'] / 3.6,
        'pressure_bar': main_steam['p'],
        'temperature_C': main_steam['T'],
        'enthalpy_kJ_kg': main_steam['h'],
    }


def analyze_reheat_steam_parameters(data):
    """分析再热蒸汽参数."""
    conn = data['connections']
    
    # 再热蒸汽入口
    reheat_in = conn[conn.iloc[:, 0] == '1#发电锅炉_再热蒸汽入口'].iloc[0]
    # 再热蒸汽出口
    reheat_out = conn[conn.iloc[:, 0] == '1#发电锅炉_再热蒸汽高再出口'].iloc[0]
    
    print("\n" + "=" * 80)
    print("再热蒸汽参数")
    print("=" * 80)
    print("再热蒸汽入口:")
    print(f"  流量:    {reheat_in['m']:.2f} t/h  ({reheat_in['m']/3.6:.2f} kg/s)")
    print(f"  压力:    {reheat_in['p']:.2f} bar")
    print(f"  温度:    {reheat_in['T']:.2f} °C")
    print("\n再热蒸汽出口:")
    print(f"  流量:    {reheat_out['m']:.2f} t/h  ({reheat_out['m']/3.6:.2f} kg/s)")
    print(f"  压力:    {reheat_out['p']:.2f} bar")
    print(f"  温度:    {reheat_out['T']:.2f} °C")
    
    return {
        'inlet_flow_kg_s': reheat_in['m'] / 3.6,
        'inlet_pressure_bar': reheat_in['p'],
        'inlet_temperature_C': reheat_in['T'],
        'outlet_flow_kg_s': reheat_out['m'] / 3.6,
        'outlet_pressure_bar': reheat_out['p'],
        'outlet_temperature_C': reheat_out['T'],
    }


def analyze_flue_gas_parameters(data):
    """分析烟气参数."""
    conn = data['connections']
    combustion = data['combustion']
    
    # 燃烧烟气
    flue_gas_combustion = conn[conn.iloc[:, 0] == '1#发电锅炉_燃烧烟气'].iloc[0]
    # 烟气出口
    flue_gas_out = conn[conn.iloc[:, 0] == '1#发电锅炉_煤预烟气出口'].iloc[0]
    
    print("\n" + "=" * 80)
    print("烟气系统参数")
    print("=" * 80)
    print("燃烧烟气:")
    print(f"  流量:    {flue_gas_combustion['m']:.2f} t/h  ({flue_gas_combustion['m']/3.6:.2f} kg/s)")
    print(f"  压力:    {flue_gas_combustion['p']:.4f} bar")
    print(f"  温度:    {flue_gas_combustion['T']:.2f} °C")
    print(f"  成分:    N2={flue_gas_combustion['N2']:.4f}, O2={flue_gas_combustion['O2']:.4f}, "
          f"CO2={flue_gas_combustion['CO2']:.4f}, H2O={flue_gas_combustion['H2O']:.4f}")
    print("\n烟气出口:")
    print(f"  温度:    {flue_gas_out['T']:.2f} °C")
    print(f"\n温降:      {flue_gas_combustion['T'] - flue_gas_out['T']:.2f} K")
    
    print("\n燃烧室参数:")
    combustion_params = combustion.iloc[0]
    print(f"  过量空气系数 λ:  {combustion_params['lamb']:.2f}")
    print(f"  总热输入 ti:     {combustion_params['ti']/1e6:.2f} MW")
    print(f"  效率 η:          {combustion_params['eta']:.2%}")
    print(f"  热损失 Q_loss:   {combustion_params['Q_loss']/1e6:.2f} MW")
    
    return {
        'combustion_flow_kg_s': flue_gas_combustion['m'] / 3.6,
        'combustion_temperature_C': flue_gas_combustion['T'],
        'outlet_temperature_C': flue_gas_out['T'],
        'temperature_drop_K': flue_gas_combustion['T'] - flue_gas_out['T'],
        'composition': {
            'N2': flue_gas_combustion['N2'],
            'O2': flue_gas_combustion['O2'],
            'CO2': flue_gas_combustion['CO2'],
            'H2O': flue_gas_combustion['H2O'],
        },
        'combustion_ti_MW': combustion_params['ti'] / 1e6,
        'combustion_eta': combustion_params['eta'],
        'combustion_Q_loss_MW': combustion_params['Q_loss'] / 1e6,
    }


def analyze_heat_exchangers(data):
    """分析换热器参数."""
    hx = data['heat_exchangers']
    
    print("\n" + "=" * 80)
    print("换热器系统")
    print("=" * 80)
    print(f"{'换热器名称':<25} {'热量Q (MW)':<15} {'kA (kW/K)':<15} {'pr1':<10} {'pr2':<10}")
    print("-" * 80)
    
    hx_summary = {}
    total_Q = 0
    
    for name, row in hx.iterrows():
        Q_MW = row['Q'] / 1e6
        kA_kW_K = row['kA'] / 1e3
        pr1 = row['pr1']
        pr2 = row['pr2']
        
        print(f"{name:<25} {Q_MW:>13.2f}   {kA_kW_K:>13.1f}   {pr1:>8.4f}  {pr2:>8.4f}")
        
        total_Q += abs(Q_MW)
        hx_summary[name] = {
            'Q_MW': Q_MW,
            'kA_kW_K': kA_kW_K,
            'pr1': pr1,
            'pr2': pr2,
        }
    
    print("-" * 80)
    print(f"{'总换热量 (吸热)':<25} {total_Q:>13.2f} MW")
    
    return hx_summary


def analyze_turbine_power(data):
    """分析汽轮机功率."""
    turbines = data['turbines']
    busses = data['busses']
    
    print("\n" + "=" * 80)
    print("汽轮机系统")
    print("=" * 80)
    print(f"{'汽轮机段':<30} {'功率 (MW)':<15} {'等熵效率':<12} {'压比':<10}")
    print("-" * 80)
    
    total_turbine_power = 0
    turbine_summary = {}
    
    for name, row in turbines.iterrows():
        P_MW = row['P'] / 1e6
        eta_s = row['eta_s']
        pr = row['pr']
        
        print(f"{name:<30} {P_MW:>13.3f}   {eta_s:>10.4f}  {pr:>8.4f}")
        
        total_turbine_power += P_MW
        turbine_summary[name] = {
            'P_MW': P_MW,
            'eta_s': eta_s,
            'pr': pr,
        }
    
    print("-" * 80)
    print(f"{'汽轮机总功率':<30} {abs(total_turbine_power):>13.3f} MW")
    
    # 从busses获取总功率
    bus_name = list(busses.keys())[0]
    bus_powers = busses[bus_name]
    bus_total = sum(bus_powers.values()) / 1e6
    print(f"{'Bus总功率（验证）':<30} {abs(bus_total):>13.3f} MW")
    
    return turbine_summary


def analyze_pump_power(data):
    """分析泵功率."""
    pumps = data['pumps']
    
    print("\n" + "=" * 80)
    print("泵系统")
    print("=" * 80)
    print(f"{'泵名称':<30} {'功率 (MW)':<15} {'等熵效率':<12} {'压比':<10}")
    print("-" * 80)
    
    pump_summary = {}
    
    for name, row in pumps.iterrows():
        P_MW = row['P'] / 1e6
        eta_s = row['eta_s']
        pr = row['pr']
        
        print(f"{name:<30} {P_MW:>13.3f}   {eta_s:>10.4f}  {pr:>8.2f}")
        
        pump_summary[name] = {
            'P_MW': P_MW,
            'eta_s': eta_s,
            'pr': pr,
        }
    
    return pump_summary


def generate_simplified_parameters(main_steam, reheat_steam, flue_gas, 
                                  heat_exchangers, turbines, pumps):
    """生成简化模型的推荐参数."""
    print("\n" + "=" * 80)
    print("Stage2简化模型推荐参数")
    print("=" * 80)
    
    # 主蒸汽参数（略微简化）
    print("\n# 主蒸汽设计参数")
    print(f"main_steam_p = {main_steam['pressure_bar']:.0f}  # bar")
    print(f"main_steam_T = {main_steam['temperature_C']:.0f}  # °C")
    print(f"main_steam_m = {main_steam['flow_kg_s']:.1f}  # kg/s")
    
    # 再热参数
    print("\n# 再热蒸汽参数")
    print(f"reheat_p = {reheat_steam['inlet_pressure_bar']:.0f}  # bar")
    print(f"reheat_T = {reheat_steam['outlet_temperature_C']:.0f}  # °C")
    
    # 烟气参数
    print("\n# 烟气参数")
    print(f"flue_gas_T_in = {flue_gas['combustion_temperature_C']:.0f}  # °C")
    print(f"flue_gas_m = {flue_gas['combustion_flow_kg_s']:.1f}  # kg/s")
    print(f"flue_gas_p = {1.05:.2f}  # bar")
    
    # 烟气成分
    comp = flue_gas['composition']
    print("\n# 烟气成分")
    print("flue_gas_composition = {")
    print(f"    'N2': {comp['N2']:.4f},")
    print(f"    'O2': {comp['O2']:.4f},")
    print(f"    'CO2': {comp['CO2']:.4f},")
    print(f"    'H2O': {comp['H2O']:.4f},")
    print("}")
    
    # 换热器kA参数（合并简化）
    print("\n# 换热器kA参数（从博士模型提取）")
    
    # 省煤器 = 上级省煤器 + 下级省煤器
    economizer_kA = (
        heat_exchangers['1#发电锅炉_上级省煤器']['kA_kW_K'] +
        heat_exchangers['1#发电锅炉_下级省煤器']['kA_kW_K']
    )
    print(f"economizer_kA = {economizer_kA:.0f}  # kW/K (上省+下省)")
    
    # 水冷壁 = 蒸发器上升管
    waterwall_kA = heat_exchangers['1#发电锅炉_蒸发器上升管']['kA_kW_K']
    print(f"waterwall_kA = {waterwall_kA:.0f}  # kW/K (蒸发器上升管)")
    
    # 过热器 = 低温过热器 + 屏式过热器 + 三级过热器 + 末级过热器
    superheater_kA = (
        heat_exchangers['1#发电锅炉_低温过热器']['kA_kW_K'] +
        heat_exchangers['1#发电锅炉_屏式过热器']['kA_kW_K'] +
        heat_exchangers['1#发电锅炉_三级过热器']['kA_kW_K'] +
        heat_exchangers['1#发电锅炉_末级过热器']['kA_kW_K']
    )
    print(f"superheater_kA = {superheater_kA:.0f}  # kW/K (低过+屏过+三过+末过)")
    
    # 再热器 = 低温再热器 + 末级再热器
    reheater_kA = (
        heat_exchangers['1#发电锅炉_低温再热器']['kA_kW_K'] +
        heat_exchangers['1#发电锅炉_末级再热器']['kA_kW_K']
    )
    print(f"reheater_kA = {reheater_kA:.0f}  # kW/K (低再+高再)")
    
    # 汽轮机效率（取平均）
    turbine_list = list(turbines.values())
    hp_eta = np.mean([t['eta_s'] for t in turbine_list[:2]])  # 高压缸段
    lp_eta = np.mean([t['eta_s'] for t in turbine_list[2:]])  # 低压缸段
    
    print("\n# 汽轮机效率")
    print(f"hp_turbine_eta = {hp_eta:.4f}")
    print(f"lp_turbine_eta = {lp_eta:.4f}")
    
    # 泵效率
    pump_eta = list(pumps.values())[0]['eta_s']
    print(f"pump_eta = {pump_eta:.4f}")
    
    # 生成Python字典格式
    params = {
        'main_steam_p': round(main_steam['pressure_bar'], 0),
        'main_steam_T': round(main_steam['temperature_C'], 0),
        'main_steam_m': round(main_steam['flow_kg_s'], 1),
        'reheat_p': round(reheat_steam['inlet_pressure_bar'], 0),
        'reheat_T': round(reheat_steam['outlet_temperature_C'], 0),
        'flue_gas_T_in': round(flue_gas['combustion_temperature_C'], 0),
        'flue_gas_m': round(flue_gas['combustion_flow_kg_s'], 1),
        'flue_gas_p': 1.05,
        'flue_gas_composition': {
            'N2': round(comp['N2'], 4),
            'O2': round(comp['O2'], 4),
            'CO2': round(comp['CO2'], 4),
            'H2O': round(comp['H2O'], 4),
        },
        'economizer_kA': round(economizer_kA, 0),
        'waterwall_kA': round(waterwall_kA, 0),
        'superheater_kA': round(superheater_kA, 0),
        'reheater_kA': round(reheater_kA, 0),
        'hp_turbine_eta': round(hp_eta, 4),
        'lp_turbine_eta': round(lp_eta, 4),
        'pump_eta': round(pump_eta, 4),
    }
    
    # 保存为JSON
    output_file = Path(__file__).parent / "phd_model_parameters.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 参数已保存到: {output_file}")
    
    return params


def main():
    """主函数."""
    print("\n" + "=" * 80)
    print("分析博士提供的设计模式数据")
    print("=" * 80)
    print("\n正在加载数据...")
    
    try:
        data = load_phd_design_data()
        print("✓ 数据加载完成")
        
        # 分析各个子系统
        main_steam = analyze_main_steam_parameters(data)
        reheat_steam = analyze_reheat_steam_parameters(data)
        flue_gas = analyze_flue_gas_parameters(data)
        heat_exchangers = analyze_heat_exchangers(data)
        turbines = analyze_turbine_power(data)
        pumps = analyze_pump_power(data)
        
        # 生成简化模型参数
        params = generate_simplified_parameters(
            main_steam, reheat_steam, flue_gas,
            heat_exchangers, turbines, pumps
        )
        
        # 总结对比
        print("\n" + "=" * 80)
        print("模型对比总结")
        print("=" * 80)
        print("\n博士模型特点：")
        print("  • 多级汽轮机（高压2段 + 低压7段）")
        print("  • 多级换热器（4级过热 + 2级再热 + 2级省煤）")
        print("  • 包含燃烧室建模")
        print("  • 包含空气预热器和煤气预热器")
        print(f"  • 净功率: ~{abs(sum(t['P_MW'] for t in turbines.values())) - list(pumps.values())[0]['P_MW']:.1f} MW")
        
        print("\nStage2简化模型：")
        print("  • 简化汽轮机（高压1段 + 低压1段）")
        print("  • 简化换热器（1个省煤器 + 1个水冷壁 + 1个过热器 + 1个再热器）")
        print("  • 不包含燃烧室（直接使用烟气源）")
        print("  • 参数经过合并以保持物理意义")
        
        print("\n改进建议：")
        print("  1. 使用博士模型的实际参数更新Stage2的默认值")
        print("  2. 调整烟气成分以匹配实际工况")
        print("  3. 考虑增加燃烧室建模（可选）")
        print("  4. 可以创建分级换热器版本以提高精度（可选）")
        
        print("\n" + "=" * 80)
        print("分析完成！")
        print("=" * 80)
        print(f"\n推荐参数已保存到: phd_model_parameters.json")
        print("可以在Stage2模型中使用这些参数进行计算。")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
