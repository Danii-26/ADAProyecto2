import os

def parse_mpl(file_path):
    """
    Parses a *.mpl file according to Section 3.1 of the project description.
    Returns a dictionary of parameters.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        # Filter out empty lines and strip whitespace
        lines = [line.strip() for line in f if line.strip()]
        
    if len(lines) < 8:
        raise ValueError(f"Invalid MPL file format: {file_path} contains only {len(lines)} non-empty lines.")
        
    try:
        n = int(lines[0])
        m = int(lines[1])
        
        # p_i: distribution of people (m integers)
        p = [int(x.strip()) for x in lines[2].split(',')]
        if len(p) != m:
            raise ValueError(f"Expected {m} values for initial distribution, got {len(p)}")
        if sum(p) != n:
            raise ValueError(f"Sum of initial distribution ({sum(p)}) must equal n ({n})")
            
        # v_i: opinion values (m floats)
        v = [float(x.strip()) for x in lines[3].split(',')]
        if len(v) != m:
            raise ValueError(f"Expected {m} values for opinion values, got {len(v)}")
            
        # ce_i: extra costs (m floats)
        ce = [float(x.strip()) for x in lines[4].split(',')]
        if len(ce) != m:
            raise ValueError(f"Expected {m} values for extra costs, got {len(ce)}")
            
        # c_ij: matrix of transition costs (m lines of m floats each)
        c = []
        for i in range(5, 5 + m):
            row = [float(x.strip()) for x in lines[i].split(',')]
            if len(row) != m:
                raise ValueError(f"Expected {m} values in cost matrix row {i-5}, got {len(row)}")
            c.append(row)
            
        # ct: cost threshold (float)
        ct = float(lines[5 + m])
        
        # MaxMovs: maximum allowed movements (integer)
        max_movs = int(lines[6 + m])
        
    except (ValueError, IndexError) as e:
        raise ValueError(f"Error parsing MPL file {file_path}: {e}")
        
    return {
        'n': n,
        'm': m,
        'p': p,
        'v': v,
        'ce': ce,
        'c': c,
        'ct': ct,
        'MaxMovs': max_movs
    }

def write_dzn(data, dest_path):
    """
    Writes the parsed parameter dictionary to a *.dzn file in MiniZinc syntax.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(f"n = {data['n']};\n")
        f.write(f"m = {data['m']};\n")
        
        # Write array format: [p1, p2, ...]
        p_str = ", ".join(str(x) for x in data['p'])
        f.write(f"p = [{p_str}];\n")
        
        v_str = ", ".join(str(x) for x in data['v'])
        f.write(f"v = [{v_str}];\n")
        
        ce_str = ", ".join(str(x) for x in data['ce'])
        f.write(f"ce = [{ce_str}];\n")
        
        # Write 2D array format: [| row1 | row2 | ... |]
        f.write("c = [|\n")
        for i, row in enumerate(data['c']):
            row_str = ", ".join(str(x) for x in row)
            if i == len(data['c']) - 1:
                f.write(f"  {row_str} |];\n")
            else:
                f.write(f"  {row_str} |\n")
        
        f.write(f"ct = {data['ct']};\n")
        f.write(f"MaxMovs = {data['MaxMovs']};\n")

def parse_minizinc_output(output_str):
    """
    Parses key-value pairs from the MiniZinc output.
    """
    lines = [line.strip() for line in output_str.split('\n') if line.strip()]
    assignments = {}
    current_statement = ""
    
    for line in lines:
        if line.startswith("----------") or line.startswith("=========="):
            continue
        current_statement += " " + line
        if ";" in line:
            statement = current_statement.strip()
            if "=" in statement:
                parts = statement.split("=", 1)
                var_name = parts[0].strip()
                var_val = parts[1].split(";")[0].strip()
                assignments[var_name] = var_val
            current_statement = ""
            
    return assignments

if __name__ == "__main__":
    # Test parser with the example in the folder
    import glob
    files = glob.glob("bateria_pruebas/mpl/*.mpl")
    if files:
        test_file = files[0]
        print(f"Testing parser on {test_file}...")
        try:
            data = parse_mpl(test_file)
            print("Successfully parsed file!")
            print(f"n={data['n']}, m={data['m']}, ct={data['ct']}, MaxMovs={data['MaxMovs']}")
            
            dzn_path = "test_output.dzn"
            write_dzn(data, dzn_path)
            print(f"Successfully wrote DZN to {dzn_path}")
            if os.path.exists(dzn_path):
                os.remove(dzn_path)
        except Exception as e:
            print(f"Error: {e}")
