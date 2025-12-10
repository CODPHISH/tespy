
lines = []
with open('stage2_detailed_model.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Uncomment Drum P fixing
    if '1#发电锅炉_汽包饱和蒸汽出口' in line and 'nw.get_conn' in line and line.strip().startswith('#'):
        new_lines.append(line.replace('# ', '', 1))
    elif 'data = conn_data.get("1#发电锅炉_汽包饱和蒸汽出口"' in line and line.strip().startswith('#'):
        new_lines.append(line.replace('# ', '', 1))
    elif 'if data.get(\'p\') is not None:' in line and line.strip().startswith('#'):
        new_lines.append(line.replace('# ', '', 1))
    elif 'conn.set_attr(p=data.get(\'p\'))' in line and line.strip().startswith('#'):
        new_lines.append(line.replace('# ', '', 1))
    elif 'try:' in line and line.strip().startswith('#') and 'try:' in lines[lines.index(line)+1]: # Context check is hard in loop
        # Simple approach: replace exact strings
        pass 
    
    # Actually, simpler logic:
    if '        # try:' in line and '1#发电锅炉_汽包饱和蒸汽出口' in lines[lines.index(line)+1]: 
         new_lines.append(line.replace('# ', '', 1))
         continue
    if '        # except KeyError:' in line and 'pass' in lines[lines.index(line)+1]:
         new_lines.append(line.replace('# ', '', 1))
         continue
    if '        #     pass' in line and 'except KeyError:' in lines[lines.index(line)-1]:
         new_lines.append(line.replace('# ', '', 1))
         continue

    # Add Temperature constraints
    if 'conn.set_attr(T=data.get(\'T\'))' in line and '1#发电锅炉_再热蒸汽高再出口' in lines[lines.index(line)-2]:
        new_lines.append(line)
        new_lines.append('\n')
        new_lines.append('        # 增加关键中间点温度固定，以补充缺失的kA约束\n')
        new_lines.append('        intermediate_conns = [\n')
        new_lines.append('            "1#发电锅炉_汽包给水入口",\n')
        new_lines.append('            "1#发电锅炉_蒸汽低过出口",\n')
        new_lines.append('            "1#发电锅炉_蒸汽屏过出口",\n')
        new_lines.append('            "1#发电锅炉_再热蒸汽低再出口",\n')
        new_lines.append('        ]\n')
        new_lines.append('        for label in intermediate_conns:\n')
        new_lines.append('            try:\n')
        new_lines.append('                conn = nw.get_conn(label)\n')
        new_lines.append('                data = conn_data.get(label, {})\n')
        new_lines.append('                if data.get(\'T\') is not None:\n')
        new_lines.append('                    conn.set_attr(T=data.get(\'T\'))\n')
        new_lines.append('            except KeyError:\n')
        new_lines.append('                pass\n')
        continue

    # Just copy if no special rule
    # But wait, the commenting logic above is flawed because index finding is slow or wrong
    pass

# Let's write the whole file content explicitly using read/replace logic
content = "".join(lines)

# 1. Uncomment Drum P
content = content.replace('        # try:\n        #     conn = nw.get_conn("1#发电锅炉_汽包饱和蒸汽出口")', '        try:\n            conn = nw.get_conn("1#发电锅炉_汽包饱和蒸汽出口")')
content = content.replace('        #     data = conn_data.get("1#发电锅炉_汽包饱和蒸汽出口", {})', '            data = conn_data.get("1#发电锅炉_汽包饱和蒸汽出口", {})')
content = content.replace('        #     if data.get(\'p\') is not None:', '            if data.get(\'p\') is not None:')
content = content.replace('        #         conn.set_attr(p=data.get(\'p\'))', '                conn.set_attr(p=data.get(\'p\'))')
content = content.replace('        # except KeyError:', '        except KeyError:')
content = content.replace('        #     pass', '            pass')

# 2. Add Temperature Constraints
insert_point = '            conn.set_attr(T=data.get(\'T\'))\n        except KeyError:\n            pass'
addition = '''
        # 增加关键中间点温度固定，以补充缺失的kA约束
        intermediate_conns = [
            "1#发电锅炉_汽包给水入口",
            "1#发电锅炉_蒸汽低过出口",
            "1#发电锅炉_蒸汽屏过出口",
            "1#发电锅炉_再热蒸汽低再出口",
        ]
        for label in intermediate_conns:
            try:
                conn = nw.get_conn(label)
                data = conn_data.get(label, {})
                if data.get('T') is not None:
                    conn.set_attr(T=data.get('T'))
            except KeyError:
                pass
'''
# Find the LAST occurrence of the insert point (Reheat Final T)
# The string appears multiple times?
# "1#发电锅炉_再热蒸汽高再出口" is unique.
# So I search for that block.

idx = content.find('1#发电锅炉_再热蒸汽高再出口')
if idx != -1:
    # Find the end of the block
    end_idx = content.find('pass', idx) + 4
    content = content[:end_idx] + addition + content[end_idx:]

with open('stage2_detailed_model.py', 'w') as f:
    f.write(content)
