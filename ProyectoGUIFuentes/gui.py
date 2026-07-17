import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import shutil
import re

# ==========================================
# Parsing and Data Utilities (Built-in)
# ==========================================

def parse_mpl(file_path):
    """
    Parses a *.mpl file according to Section 3.1 of the project description.
    Returns a dictionary of parameters.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if len(lines) < 8:
        raise ValueError(f"Invalid MPL file format: contains only {len(lines)} non-empty lines.")
        
    n = int(lines[0])
    m = int(lines[1])
    
    p = [int(x.strip()) for x in lines[2].split(',')]
    if len(p) != m:
        raise ValueError(f"Expected {m} values for initial distribution, got {len(p)}")
    if sum(p) != n:
        raise ValueError(f"Sum of initial distribution ({sum(p)}) must equal n ({n})")
        
    v = [float(x.strip()) for x in lines[3].split(',')]
    if len(v) != m:
        raise ValueError(f"Expected {m} values for opinion values, got {len(v)}")
        
    ce = [float(x.strip()) for x in lines[4].split(',')]
    if len(ce) != m:
        raise ValueError(f"Expected {m} values for extra costs, got {len(ce)}")
        
    c = []
    for i in range(5, 5 + m):
        row = [float(x.strip()) for x in lines[i].split(',')]
        if len(row) != m:
            raise ValueError(f"Expected {m} values in cost matrix row {i-5}, got {len(row)}")
        c.append(row)
        
    ct = float(lines[5 + m])
    max_movs = int(lines[6 + m])
    
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
    Writes the parameter dictionary to a *.dzn file in MiniZinc syntax.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(f"n = {data['n']};\n")
        f.write(f"m = {data['m']};\n")
        
        p_str = ", ".join(str(x) for x in data['p'])
        f.write(f"p = [{p_str}];\n")
        
        v_str = ", ".join(str(x) for x in data['v'])
        f.write(f"v = [{v_str}];\n")
        
        ce_str = ", ".join(str(x) for x in data['ce'])
        f.write(f"ce = [{ce_str}];\n")
        
        f.write("c = [|\n")
        for i, row in enumerate(data['c']):
            row_str = ", ".join(str(x) for x in row)
            if i == len(data['c']) - 1:
                f.write(f"  {row_str} |];\n")
            else:
                f.write(f"  {row_str} |\n")
        
        f.write(f"ct = {data['ct']};\n")
        f.write(f"MaxMovs = {data['MaxMovs']};\n")

def find_minizinc_executable():
    """
    Attempts to find the minizinc executable in standard locations.
    """
    # 1. Search system PATH
    path_res = shutil.which("minizinc")
    if path_res:
        return path_res
        
    # 2. Check common installation directories
    user_home = os.path.expanduser("~")
    common_paths = [
        r"C:\Program Files\MiniZinc\minizinc.exe",
        r"C:\Program Files (x86)\MiniZinc\minizinc.exe",
        r"C:\Program Files\MiniZinc 2.9.7 (bundled)\minizinc.exe",
        r"C:\Program Files\MiniZinc 2.8.5 (bundled)\minizinc.exe",
        r"C:\Program Files\MiniZinc 2.8.5\minizinc.exe",
        os.path.join(user_home, "MiniZinc", "minizinc.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "MiniZinc", "minizinc.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "MiniZinc 2.9.7 (bundled)", "minizinc.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "MiniZinc 2.8.5 (bundled)", "minizinc.exe"),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return ""

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

def parse_minizinc_matrix(matrix_str):
    """
    Converts a MiniZinc 2D array representation into a list of lists of integers.
    Supports both '[| 1, 2 | 3, 4 |]' and flat '[1, 2, 3, 4]' formats.
    """
    s = matrix_str.strip()
    if s.startswith("[|") and s.endswith("|]"):
        s = s[2:-2].strip()
        rows = s.split("|")
        matrix = []
        for r in rows:
            r = r.strip()
            if r:
                row_vals = [int(float(x.strip())) for x in r.split(",") if x.strip()]
                matrix.append(row_vals)
        return matrix
    elif s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
        vals = [int(float(x.strip())) for x in s.split(",") if x.strip()]
        import math
        m = int(math.isqrt(len(vals)))
        matrix = [vals[i * m : (i + 1) * m] for i in range(m)]
        return matrix
    return []

def parse_minizinc_array(array_str):
    """
    Converts a MiniZinc 1D array representation '[1, 2, 3]' into a list of integers.
    """
    s = array_str.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    return [int(float(x.strip())) for x in s.split(",") if x.strip()]

# ==========================================
# Graphical User Interface (Tkinter)
# ==========================================

class MinPolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MinPol Optimizer - Minimizar Polarización")
        self.root.geometry("1100x750")
        
        # Default State
        self.data = {
            'n': 0,
            'm': 0,
            'p': [],
            'v': [],
            'ce': [],
            'c': [],
            'ct': 0.0,
            'MaxMovs': 0
        }
        self.current_file = ""
        self.minizinc_path = find_minizinc_executable()
        
        # Style Setup
        self.setup_styles()
        
        # Build UI Components
        self.build_menu()
        self.build_widgets()
        
        # Update path label
        self.update_path_label()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Palette: Dark Slate Blue & Cool Gray
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#f8f9fa")
        self.style.configure("TLabel", background="#f8f9fa", foreground="#2c3e50")
        
        # Header Style
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#2c3e50")
        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1a5276")
        
        # Button Styles
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#e5e8e8", foreground="#2c3e50")
        self.style.map("TButton",
            background=[('active', '#d5dbdb'), ('pressed', '#bdc3c7')]
        )
        self.style.configure("Action.TButton", background="#3498db", foreground="white")
        self.style.map("Action.TButton",
            background=[('active', '#2980b9'), ('pressed', '#21618c')]
        )
        
        # Treeview Style
        self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=24, background="white")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#ebf5fb", foreground="#2c3e50")

    def build_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Cargar archivo .mpl", command=self.load_file)
        filemenu.add_command(label="Guardar archivo .mpl", command=self.save_file)
        filemenu.add_separator()
        filemenu.add_command(label="Salir", command=self.root.quit)
        menubar.add_cascade(label="Archivo", menu=filemenu)
        self.root.config(menu=menubar)

    def build_widgets(self):
        # Title Frame
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill="x", side="top")
        
        title_lbl = ttk.Label(title_frame, text="MinPol: Minimizar Polarización de una Población", style="Title.TLabel")
        title_lbl.pack(side="left")
        
        authors_lbl = ttk.Label(title_frame, text="Grupo: Paipilla - Arias - Granada", font=("Segoe UI", 9, "italic"))
        authors_lbl.pack(side="right", padx=10)
        
        # Main Pane
        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left Panel (Inputs)
        left_frame = ttk.Frame(main_pane, padding=10)
        main_pane.add(left_frame, weight=6)
        
        # Right Panel (Outputs & Controls)
        right_frame = ttk.Frame(main_pane, padding=10)
        main_pane.add(right_frame, weight=4)
        
        # ----------------------------------------
        # Left Panel Content (Inputs)
        # ----------------------------------------
        
        # Config & File Loading
        file_io_frame = ttk.LabelFrame(left_frame, text=" Carga e Información de Instancia ", padding=10)
        file_io_frame.pack(fill="x", pady=(0, 10))
        
        load_btn = ttk.Button(file_io_frame, text="Cargar Instancia (.mpl)", command=self.load_file)
        load_btn.pack(side="left", padx=(0, 10))
        
        self.file_lbl = ttk.Label(file_io_frame, text="Ningún archivo cargado", font=("Segoe UI", 9, "italic"))
        self.file_lbl.pack(side="left", fill="x", expand=True)
        
        # Base Parameters
        param_frame = ttk.LabelFrame(left_frame, text=" Parámetros Generales ", padding=10)
        param_frame.pack(fill="x", pady=(0, 10))
        
        # Grid layout for parameters
        param_frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        ttk.Label(param_frame, text="Población (n):").grid(row=0, column=0, sticky="w", pady=5)
        self.n_var = tk.StringVar(value="0")
        ttk.Label(param_frame, textvariable=self.n_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Label(param_frame, text="Opiniones (m):").grid(row=0, column=2, sticky="w", pady=5)
        self.m_var = tk.StringVar(value="0")
        ttk.Label(param_frame, textvariable=self.m_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="w", pady=5)
        
        ttk.Label(param_frame, text="Presupuesto (ct):").grid(row=1, column=0, sticky="w", pady=5)
        self.ct_ent = ttk.Entry(param_frame, width=10)
        self.ct_ent.grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(param_frame, text="Max Movimientos:").grid(row=1, column=2, sticky="w", pady=5)
        self.max_movs_ent = ttk.Entry(param_frame, width=10)
        self.max_movs_ent.grid(row=1, column=3, sticky="w", pady=5)
        
        # Notebook for Tables
        tables_notebook = ttk.Notebook(left_frame)
        tables_notebook.pack(fill="both", expand=True)
        
        # Tab 1: Opinions list (p, v, ce)
        self.tab_opinions = ttk.Frame(tables_notebook, padding=10)
        tables_notebook.add(self.tab_opinions, text="Distribución y Valores")
        
        # Scrollable Treeview
        tree_scroll = ttk.Scrollbar(self.tab_opinions)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree_ops = ttk.Treeview(self.tab_opinions, columns=("idx", "val", "p_init", "ce", "p_final"), show="headings", yscrollcommand=tree_scroll.set)
        self.tree_ops.pack(fill="both", expand=True)
        tree_scroll.config(command=self.tree_ops.yview)
        
        self.tree_ops.heading("idx", text="Opinión ID")
        self.tree_ops.heading("val", text="Valor (v_i)")
        self.tree_ops.heading("p_init", text="Pob. Inicial (p_i)")
        self.tree_ops.heading("ce", text="Costo Extra (ce_i)")
        self.tree_ops.heading("p_final", text="Pob. Final (p'_i)")
        
        self.tree_ops.column("idx", width=80, anchor="center")
        self.tree_ops.column("val", width=120, anchor="center")
        self.tree_ops.column("p_init", width=120, anchor="center")
        self.tree_ops.column("ce", width=120, anchor="center")
        self.tree_ops.column("p_final", width=120, anchor="center")
        
        self.tree_ops.bind("<<TreeviewSelect>>", self.on_opinion_select)
        
        # Edit Form for selected opinion row
        edit_ops_frame = ttk.Frame(self.tab_opinions, padding=5)
        edit_ops_frame.pack(fill="x", side="bottom", pady=5)
        
        ttk.Label(edit_ops_frame, text="Valor (v):").pack(side="left", padx=5)
        self.edit_val_ent = ttk.Entry(edit_ops_frame, width=8)
        self.edit_val_ent.pack(side="left", padx=5)
        
        ttk.Label(edit_ops_frame, text="Pob. Inicial:").pack(side="left", padx=5)
        self.edit_p_ent = ttk.Entry(edit_ops_frame, width=8)
        self.edit_p_ent.pack(side="left", padx=5)
        
        ttk.Label(edit_ops_frame, text="Costo Extra:").pack(side="left", padx=5)
        self.edit_ce_ent = ttk.Entry(edit_ops_frame, width=8)
        self.edit_ce_ent.pack(side="left", padx=5)
        
        save_op_btn = ttk.Button(edit_ops_frame, text="Guardar Fila", command=self.save_opinion_row)
        save_op_btn.pack(side="left", padx=10)
        
        # Tab 2: Transition Cost Matrix (c_ij)
        self.tab_costs = ttk.Frame(tables_notebook, padding=10)
        tables_notebook.add(self.tab_costs, text="Matriz de Costos (c_i,j)")
        
        matrix_scroll_y = ttk.Scrollbar(self.tab_costs, orient="vertical")
        matrix_scroll_y.pack(side="right", fill="y")
        matrix_scroll_x = ttk.Scrollbar(self.tab_costs, orient="horizontal")
        matrix_scroll_x.pack(side="bottom", fill="x")
        
        self.tree_costs = ttk.Treeview(self.tab_costs, show="headings",
                                      xscrollcommand=matrix_scroll_x.set, yscrollcommand=matrix_scroll_y.set)
        self.tree_costs.pack(fill="both", expand=True)
        
        matrix_scroll_y.config(command=self.tree_costs.yview)
        matrix_scroll_x.config(command=self.tree_costs.xview)
        
        self.tree_costs.bind("<<TreeviewSelect>>", self.on_cost_select)
        
        # Edit Form for transition cost
        edit_cost_frame = ttk.Frame(self.tab_costs, padding=5)
        edit_cost_frame.pack(fill="x", side="bottom", pady=5)
        
        self.cost_edit_lbl = ttk.Label(edit_cost_frame, text="Seleccione una celda para editar el costo de transición.")
        self.cost_edit_lbl.pack(side="left", padx=5)
        
        self.edit_cost_ent = ttk.Entry(edit_cost_frame, width=10)
        self.edit_cost_ent.pack(side="left", padx=5)
        
        self.save_cost_btn = ttk.Button(edit_cost_frame, text="Guardar Costo", command=self.save_cost_value, state="disabled")
        self.save_cost_btn.pack(side="left", padx=10)
        
        # ----------------------------------------
        # Right Panel Content (Solver & Outputs)
        # ----------------------------------------
        
        # Solver path config
        sz_path_frame = ttk.LabelFrame(right_frame, text=" Configuración de MiniZinc ", padding=10)
        sz_path_frame.pack(fill="x", pady=(0, 10))
        
        self.path_status_lbl = ttk.Label(sz_path_frame, text="Buscando executable minizinc...", font=("Segoe UI", 9, "bold"))
        self.path_status_lbl.pack(fill="x", pady=(0, 5))
        
        browse_path_btn = ttk.Button(sz_path_frame, text="Buscar minizinc.exe Manualmente", command=self.browse_minizinc_path)
        browse_path_btn.pack(fill="x", pady=(0, 10))
        
        # Solver selection dropdown
        ttk.Label(sz_path_frame, text="Seleccionar Solver:").pack(fill="x", pady=(0, 2))
        self.solver_var = tk.StringVar(value="Gecode")
        self.solver_combo = ttk.Combobox(sz_path_frame, textvariable=self.solver_var, values=["Gecode", "HiGHS", "COIN-BC", "Chuffed"], state="readonly")
        self.solver_combo.pack(fill="x", pady=(0, 5))
        
        # Execution Panel
        solve_frame = ttk.Frame(right_frame, padding=10)
        solve_frame.pack(fill="x", pady=(0, 10))
        
        self.solve_btn = ttk.Button(solve_frame, text="EJECUTAR SOLVER (MiniZinc)", style="Action.TButton", command=self.run_solver)
        self.solve_btn.pack(fill="x", ipady=5)
        
        self.status_lbl = ttk.Label(solve_frame, text="Estado: Listo", font=("Segoe UI", 11, "bold"), anchor="center")
        self.status_lbl.pack(fill="x", pady=10)
        
        # Results metrics frame
        metrics_frame = ttk.LabelFrame(right_frame, text=" Resumen de Solución Óptima ", padding=10)
        metrics_frame.pack(fill="x", pady=(0, 10))
        
        # Metricas: Polarizacion
        ttk.Label(metrics_frame, text="Polarización Mínima:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.pol_res_var = tk.StringVar(value="-")
        ttk.Label(metrics_frame, textvariable=self.pol_res_var, font=("Segoe UI", 14, "bold"), foreground="#27ae60").grid(row=0, column=1, sticky="e", pady=5)
        
        # Metricas: Mediana
        ttk.Label(metrics_frame, text="Opinión Mediana (Valor):").grid(row=1, column=0, sticky="w", pady=5)
        self.med_res_var = tk.StringVar(value="-")
        ttk.Label(metrics_frame, textvariable=self.med_res_var, font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="e", pady=5)
        
        # Metricas: Presupuesto
        ttk.Label(metrics_frame, text="Costo Total Utilizado:").grid(row=2, column=0, sticky="w", pady=2)
        self.cost_res_var = tk.StringVar(value="-")
        ttk.Label(metrics_frame, textvariable=self.cost_res_var).grid(row=2, column=1, sticky="e", pady=2)
        
        self.cost_bar = ttk.Progressbar(metrics_frame, orient="horizontal", mode="determinate")
        self.cost_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Metricas: Movimientos
        ttk.Label(metrics_frame, text="Movimientos Realizados:").grid(row=4, column=0, sticky="w", pady=2)
        self.movs_res_var = tk.StringVar(value="-")
        ttk.Label(metrics_frame, textvariable=self.movs_res_var).grid(row=4, column=1, sticky="e", pady=2)
        
        self.movs_bar = ttk.Progressbar(metrics_frame, orient="horizontal", mode="determinate")
        self.movs_bar.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # Detailed Transitions Log
        log_frame = ttk.LabelFrame(right_frame, text=" Detalle de Desplazamientos de Opinión ", padding=10)
        log_frame.pack(fill="both", expand=True)
        
        self.log_txt = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), background="white", height=10)
        self.log_txt.pack(fill="both", expand=True)
        self.log_txt.config(state="disabled")

    # ==========================================
    # Logic & Event Handlers
    # ==========================================
    
    def update_path_label(self):
        if self.minizinc_path and os.path.exists(self.minizinc_path):
            self.path_status_lbl.config(text=f"MiniZinc: {self.minizinc_path}", foreground="#27ae60")
            self.solve_btn.config(state="normal")
        else:
            self.path_status_lbl.config(text="MiniZinc: NO ENCONTRADO. Configure la ruta manual.", foreground="#c0392b")
            self.solve_btn.config(state="disabled")

    def browse_minizinc_path(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar ejecutable de MiniZinc",
            filetypes=[("Archivos ejecutables", "*.exe"), ("Todos los archivos", "*.*")]
        )
        if filepath:
            self.minizinc_path = filepath
            self.update_path_label()

    def load_file(self):
        filepath = filedialog.askopenfile(
            title="Seleccionar archivo de entrada MPL",
            filetypes=[("Archivos de Entrada MPL", "*.mpl"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return
            
        try:
            self.current_file = filepath.name
            filepath.close()
            
            # Parse the MPL data
            self.data = parse_mpl(self.current_file)
            
            # Update GUI elements
            self.file_lbl.config(text=os.path.basename(self.current_file))
            self.n_var.set(str(self.data['n']))
            self.m_var.set(str(self.data['m']))
            
            self.ct_ent.delete(0, tk.END)
            self.ct_ent.insert(0, str(self.data['ct']))
            
            self.max_movs_ent.delete(0, tk.END)
            self.max_movs_ent.insert(0, str(self.data['MaxMovs']))
            
            # Clear output results
            self.pol_res_var.set("-")
            self.med_res_var.set("-")
            self.cost_res_var.set("-")
            self.movs_res_var.set("-")
            self.cost_bar['value'] = 0
            self.movs_bar['value'] = 0
            self.set_log_text("")
            
            self.update_opinions_table()
            self.update_costs_table()
            self.status_lbl.config(text="Estado: Instancia Cargada", foreground="#2c3e50")
            
        except Exception as e:
            messagebox.showerror("Error de lectura", f"No se pudo parsear el archivo:\n{e}")
            self.status_lbl.config(text="Estado: Error de Carga", foreground="#c0392b")

    def save_file(self):
        if not self.data['p']:
            messagebox.showwarning("Sin datos", "No hay datos cargados para guardar.")
            return
            
        # Update parameters from entries first
        try:
            self.data['ct'] = float(self.ct_ent.get())
            self.data['MaxMovs'] = int(self.max_movs_ent.get())
        except ValueError:
            messagebox.showerror("Error de validación", "El presupuesto o max movimientos tienen valores inválidos.")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Guardar archivo de entrada MPL",
            defaultextension=".mpl",
            filetypes=[("Archivos de Entrada MPL", "*.mpl")]
        )
        if not filepath:
            return
            
        try:
            # We re-serialize data to the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"{self.data['n']}\n")
                f.write(f"{self.data['m']}\n")
                f.write(",".join(str(x) for x in self.data['p']) + "\n")
                f.write(",".join(str(x) for x in self.data['v']) + "\n")
                f.write(",".join(str(x) for x in self.data['ce']) + "\n")
                for row in self.data['c']:
                    f.write(",".join(str(x) for x in row) + "\n")
                f.write(f"{self.data['ct']}\n")
                f.write(f"{self.data['MaxMovs']}\n")
                
            self.current_file = filepath
            self.file_lbl.config(text=os.path.basename(self.current_file))
            messagebox.showinfo("Éxito", "Instancia guardada con éxito.")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar la instancia:\n{e}")

    def update_opinions_table(self, final_distribution=None):
        # Clear existing items
        for item in self.tree_ops.get_children():
            self.tree_ops.delete(item)
            
        for i in range(self.data['m']):
            idx = i + 1
            val = self.data['v'][i]
            p_init = self.data['p'][i]
            ce = self.data['ce'][i]
            p_final_val = final_distribution[i] if final_distribution else "-"
            
            self.tree_ops.insert("", "end", values=(idx, val, p_init, ce, p_final_val))

    def update_costs_table(self):
        # Clear existing cols and items
        self.tree_costs.delete(*self.tree_costs.get_children())
        
        # Configure columns
        m = self.data['m']
        cols = [f"col_{j+1}" for j in range(m)]
        self.tree_costs["columns"] = ["orig"] + cols
        
        # Setup headers
        self.tree_costs.heading("orig", text="De \\ A")
        self.tree_costs.column("orig", width=80, anchor="center")
        
        for j in range(m):
            col_id = f"col_{j+1}"
            self.tree_costs.heading(col_id, text=f"Op {j+1}")
            self.tree_costs.column(col_id, width=70, anchor="center")
            
        # Insert rows
        for i in range(m):
            row_vals = [f"Op {i+1}"]
            for j in range(m):
                row_vals.append(str(self.data['c'][i][j]))
            self.tree_costs.insert("", "end", values=row_vals)

    # Editing Table values
    def on_opinion_select(self, event):
        selected = self.tree_ops.selection()
        if not selected:
            return
        vals = self.tree_ops.item(selected[0])['values']
        # vals: (idx, val, p_init, ce, p_final)
        self.edit_val_ent.delete(0, tk.END)
        self.edit_val_ent.insert(0, str(vals[1]))
        
        self.edit_p_ent.delete(0, tk.END)
        self.edit_p_ent.insert(0, str(vals[2]))
        
        self.edit_ce_ent.delete(0, tk.END)
        self.edit_ce_ent.insert(0, str(vals[3]))

    def save_opinion_row(self):
        selected = self.tree_ops.selection()
        if not selected:
            messagebox.showwarning("Selección requerida", "Seleccione una fila en la lista de opiniones primero.")
            return
            
        idx = int(self.tree_ops.item(selected[0])['values'][0]) - 1
        try:
            val = float(self.edit_val_ent.get())
            p_val = int(self.edit_p_ent.get())
            ce_val = float(self.edit_ce_ent.get())
            
            # Apply changes
            self.data['v'][idx] = val
            self.data['p'][idx] = p_val
            self.data['ce'][idx] = ce_val
            
            # Update population sum n
            self.data['n'] = sum(self.data['p'])
            self.n_var.set(str(self.data['n']))
            
            self.update_opinions_table()
        except ValueError:
            messagebox.showerror("Error", "Los valores ingresados deben ser numéricos.")

    def on_cost_select(self, event):
        selected = self.tree_costs.selection()
        if not selected:
            self.save_cost_btn.config(state="disabled")
            return
            
        item_vals = self.tree_costs.item(selected[0])['values']
        # The first element is the label (e.g. "Op 1")
        # We need the user to pick a column too, so we bind to select cell
        # In tkinter treeviews, we can identify which column was clicked
        x, y = self.root.winfo_pointerxy()
        widget_x = x - self.tree_costs.winfo_rootx()
        column_clicked = self.tree_costs.identify_column(widget_x)
        
        if not column_clicked or column_clicked == "#1":
            # Clicked on origin label
            self.save_cost_btn.config(state="disabled")
            self.cost_edit_lbl.config(text="Haga clic en una columna de costo (Op 1...) para editar.")
            return
            
        col_idx = int(column_clicked.replace("#", "")) - 2 # Offset by 1 for #1 which is 'orig'
        row_idx = self.tree_costs.index(selected[0])
        
        self.selected_cost_cell = (row_idx, col_idx)
        current_val = self.data['c'][row_idx][col_idx]
        
        self.cost_edit_lbl.config(text=f"Costo de Op {row_idx+1} a Op {col_idx+1}:")
        self.edit_cost_ent.delete(0, tk.END)
        self.edit_cost_ent.insert(0, str(current_val))
        
        self.save_cost_btn.config(state="normal")

    def save_cost_value(self):
        try:
            val = float(self.edit_cost_ent.get())
            r, c = self.selected_cost_cell
            self.data['c'][r][c] = val
            self.update_costs_table()
            self.save_cost_btn.config(state="disabled")
            self.cost_edit_lbl.config(text="Costo guardado.")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un valor numérico para el costo.")

    def set_log_text(self, text):
        self.log_txt.config(state="normal")
        self.log_txt.delete("1.0", tk.END)
        self.log_txt.insert(tk.END, text)
        self.log_txt.config(state="disabled")

    # ==========================================
    # Optimization Execution (MiniZinc Call)
    # ==========================================
    
    def run_solver(self):
        if not self.data['p']:
            messagebox.showwarning("Sin datos", "Cargue una instancia .mpl antes de resolver.")
            return
            
        # Update budget and max movements from entries
        try:
            self.data['ct'] = float(self.ct_ent.get())
            self.data['MaxMovs'] = int(self.max_movs_ent.get())
        except ValueError:
            messagebox.showerror("Error de validación", "El presupuesto o max movimientos tienen valores inválidos.")
            return
            
        self.status_lbl.config(text="Estado: Resolviendo...", foreground="#1a5276")
        self.root.update_idletasks()
        
        # 1. Write current state to DatosProyecto.dzn
        dzn_path = os.path.join("DatosProyecto", "DatosProyecto.dzn")
        try:
            write_dzn(self.data, dzn_path)
        except Exception as e:
            messagebox.showerror("Error al escribir DZN", f"No se pudo guardar la configuración temporal DZN:\n{e}")
            self.status_lbl.config(text="Estado: Error", foreground="#c0392b")
            return
            
        # 2. Run MiniZinc via subprocess
        # Search for Proyecto.mzn in three possible locations:
        # a) Current working directory
        # b) Directory where gui.py resides
        # c) Parent directory of where gui.py resides (standard project layout)
        model_path = "Proyecto.mzn"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        
        candidates = [
            model_path,
            os.path.join(script_dir, "Proyecto.mzn"),
            os.path.join(parent_dir, "Proyecto.mzn")
        ]
        
        found = False
        for c_path in candidates:
            if os.path.exists(c_path):
                model_path = c_path
                found = True
                break
                
        if not found:
            messagebox.showerror("Error", "No se encontró el modelo de MiniZinc Proyecto.mzn en el directorio de trabajo, en la carpeta del script ni en la carpeta superior.")
            self.status_lbl.config(text="Estado: Error", foreground="#c0392b")
            return
            
        try:
            cmd = [
                self.minizinc_path,
                "--solver", self.solver_var.get(),
                model_path,
                dzn_path
            ]
            
            # Start process
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if res.returncode != 0:
                self.set_log_text(f"--- MiniZinc Error (exit code {res.returncode}) ---\n" + res.stderr)
                self.status_lbl.config(text="Estado: Error en Solver", foreground="#c0392b")
                messagebox.showerror("Error de MiniZinc", f"El solver falló con error de ejecución. Ver bitácora.")
                return
                
            output_text = res.stdout
            
            # Parse output
            assignments = parse_minizinc_output(output_text)
            
            if not assignments or "polarization" not in assignments:
                self.set_log_text("--- Output del Solver (Infactible o sin solución) ---\n" + output_text)
                self.status_lbl.config(text="Estado: Infactible", foreground="#e67e22")
                self.pol_res_var.set("Infactible")
                self.med_res_var.set("-")
                self.cost_res_var.set("-")
                self.movs_res_var.set("-")
                self.cost_bar['value'] = 0
                self.movs_bar['value'] = 0
                messagebox.showwarning("Infactible", "No se encontró solución óptima para los límites de presupuesto o movimientos.")
                return
                
            # Process successfully solved!
            pol_val = float(assignments['polarization'])
            med_idx = int(assignments['med_idx'])
            med_val = float(assignments['med_val'])
            p_final_list = parse_minizinc_array(assignments['p_final'])
            x_matrix = parse_minizinc_matrix(assignments['x'])
            tot_cost = float(assignments['total_cost'])
            tot_movs = int(assignments['total_movs'])
            
            # Update metrics
            self.pol_res_var.set(f"{pol_val:.3f}")
            self.med_res_var.set(f"Op {med_idx} ({med_val})")
            
            self.cost_res_var.set(f"{tot_cost:.2f} / {self.data['ct']}")
            # Set progress bar
            if self.data['ct'] > 0:
                self.cost_bar['value'] = min(100, int(tot_cost * 100 / self.data['ct']))
            else:
                self.cost_bar['value'] = 0
                
            self.movs_res_var.set(f"{tot_movs} / {self.data['MaxMovs']}")
            if self.data['MaxMovs'] > 0:
                self.movs_bar['value'] = min(100, int(tot_movs * 100 / self.data['MaxMovs']))
            else:
                self.movs_bar['value'] = 0
                
            # Update Treeview with final distribution
            self.update_opinions_table(p_final_list)
            
            # Construct detailed text log of transitions
            log_lines = []
            log_lines.append(f"POLARIZACIÓN ÓPTIMA: {pol_val:.3f}")
            log_lines.append(f"Opinión Mediana: ID {med_idx} (Valor: {med_val})")
            log_lines.append(f"Costo Total: {tot_cost:.2f} (Límite: {self.data['ct']})")
            log_lines.append(f"Movimientos: {tot_movs} (Límite: {self.data['MaxMovs']})\n")
            log_lines.append("Detalle de movimientos de personas:")
            log_lines.append("-" * 45)
            
            has_movements = False
            for i in range(self.data['m']):
                for j in range(self.data['m']):
                    if i != j and x_matrix[i][j] > 0:
                        has_movements = True
                        count = x_matrix[i][j]
                        # Calculate unit cost
                        p_init_j = self.data['p'][j]
                        base_cost = self.data['c'][i][j] * (1.0 + self.data['p'][i] / self.data['n'])
                        unit_c = base_cost if p_init_j > 0 else (base_cost + self.data['ce'][j])
                        total_c = unit_c * count
                        movs_count = count * abs(j - i)
                        
                        log_lines.append(f"Op {i+1} -> Op {j+1}: {count} personas")
                        log_lines.append(f"  Cost. ind: {unit_c:.2f} | Cost. tot: {total_c:.2f} | Movs: {movs_count}")
                        
            if not has_movements:
                log_lines.append("(No se requirieron desplazamientos, la población original ya está en su estado óptimo)")
                
            self.set_log_text("\n".join(log_lines))
            self.status_lbl.config(text="Estado: Solución Óptima Encontrada", foreground="#27ae60")
            
        except subprocess.TimeoutExpired:
            self.status_lbl.config(text="Estado: Tiempo Excedido (30s)", foreground="#c0392b")
            messagebox.showerror("Tiempo excedido", "La ejecución de MiniZinc superó el tiempo límite de 30 segundos.")
        except Exception as e:
            self.status_lbl.config(text="Estado: Error", foreground="#c0392b")
            messagebox.showerror("Error al ejecutar solver", f"Ocurrió un error inesperado al invocar MiniZinc:\n{e}")

# ==========================================
# Main entry point
# ==========================================

if __name__ == "__main__":
    root = tk.Tk()
    app = MinPolGUI(root)
    root.mainloop()
