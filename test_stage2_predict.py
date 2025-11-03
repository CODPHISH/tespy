#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试阶段2的预测功能

专注于小范围烟气变化，验证预测模式的可行性。
"""

from stage2_minimal_working import Stage2MinimalSystem


def test_small_change():
    """测试小范围烟气变化的预测."""
    
    print("=" * 80)
    print("测试1：小范围烟气变化预测")
    print("=" * 80)
    
    # 1. 运行设计模式
    system = Stage2MinimalSystem()
    system.build_network(mode='design')
    
    if not system.solve():
        print("✗ 设计模式求解失败")
        return False
    
    design_results = system.analyze()
    system.save_design_point('test_design.json')
    
    # 2. 测试预测模式 - 烟气温度降低10°C
    print("\n" + "=" * 80)
    print("测试场景：烟气温度降低10°C（1200°C → 1190°C）")
    print("=" * 80)
    
    system2 = Stage2MinimalSystem()
    system2.load_design_point('test_design.json')
    
    inputs = {
        'flue_gas_T_in': 1190,  # 小幅变化
        'flue_gas_m': 300,      # 保持不变
    }
    
    predict_results = system2.predict(inputs)
    
    if 'error' in predict_results:
        print(f"\n✗ 预测失败: {predict_results['error']}")
        return False
    
    print("\n✓ 预测成功！")
    print("\n结果对比：")
    print("=" * 80)
    print(f"{'参数':<30} {'设计点':<15} {'预测点':<15} {'变化':<15}")
    print("-" * 80)
    
    comparisons = [
        ("主蒸汽压力 [bar]", "main_steam_p_bar"),
        ("主蒸汽温度 [°C]", "main_steam_T_degC"),
        ("净发电功率 [MW]", "P_net_MW"),
        ("循环热效率 [%]", "eta_thermal_percent"),
    ]
    
    for name, key in comparisons:
        if key in design_results and key in predict_results:
            design_val = design_results[key]
            predict_val = predict_results[key]
            change = (predict_val - design_val) / design_val * 100 if design_val != 0 else 0
            print(f"{name:<30} {design_val:>13.2f} {predict_val:>13.2f} {change:>+13.2f}%")
    
    print("=" * 80)
    return True


def test_staged_prediction():
    """测试分步预测：先小变化，再大变化."""
    
    print("\n\n" + "=" * 80)
    print("测试2：分步预测（渐进式变化）")
    print("=" * 80)
    
    system = Stage2MinimalSystem()
    system.load_design_point('test_design.json')
    
    test_cases = [
        {'name': "烟气-10°C", 'flue_gas_T_in': 1190, 'flue_gas_m': 300},
        {'name': "烟气-20°C", 'flue_gas_T_in': 1180, 'flue_gas_m': 300},
        {'name': "烟气-30°C", 'flue_gas_T_in': 1170, 'flue_gas_m': 300},
    ]
    
    print(f"\n{'场景':<15} {'主蒸汽T[°C]':<15} {'功率[MW]':<15} {'状态':<10}")
    print("-" * 60)
    
    for case in test_cases:
        name = case.pop('name')
        results = system.predict(case)
        
        if 'error' in results:
            print(f"{name:<15} {'N/A':<15} {'N/A':<15} {'失败':<10}")
        else:
            T = results.get('main_steam_T_degC', 0)
            P = results.get('P_net_MW', 0)
            print(f"{name:<15} {T:<15.2f} {P:<15.2f} {'✓成功':<10}")
    
    print("=" * 80)


def main():
    """主测试函数."""
    
    print("\n" + "=" * 80)
    print("阶段2预测模式测试")
    print("=" * 80)
    
    success = test_small_change()
    
    if success:
        test_staged_prediction()
        print("\n✓ 所有测试完成")
    else:
        print("\n✗ 测试失败，需要进一步调试")


if __name__ == "__main__":
    main()
