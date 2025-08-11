import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading


# ---------------------------------------------------------------------------
# Parameter definitions
# ---------------------------------------------------------------------------
PARAMS = {
    "Bind Phrase": None,
    "Mode": {1: "31 Hz", 2: "19 Hz", 4: "FSK"},
    "RF Band": {1: "915 MHz FCC", 2: "868 MHz"},
    "RF Ortho": None,
    "Tx Power": {0: "min", 1: "1 mW", 2: "10 mW", 3: "25 mW", 4: "100 mW", 5: "158 mW"},
    "Tx Diversity": {1: "antenna1"},
    "Tx Ch Source": {0: "none", 1: "crsf", 2: "in", 3: "mbridge"},
    "Tx Ch Order": {0: "AETR", 1: "TAER", 2: "ETAR"},
    "Tx In Mode": {0: "sbus", 1: "sbus inv"},
    "Tx Ser Dest": {0: "serial", 2: "mbridge"},
    "Tx Ser Baudrate": {0: "9600", 1: "19200", 2: "38400", 3: "57600", 4: "115200", 5: "230400"},
    "Tx Snd RadioStat": {0: "off", 1: "1 Hz"},
    "Tx Mav Component": {0: "off", 1: "enabled"},
    "Tx Power Sw Ch": {
        0: "off", 1: "5", 2: "6", 3: "7", 4: "8", 5: "9", 6: "10",
        7: "11", 8: "12", 9: "13", 10: "14", 11: "15", 12: "16"
    },
    "Tx Buzzer": None,
}


class ParamApp:
    """Tkinter GUI for controlling mLRS Tx / Rx parameters over serial."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mLRS Parameter Control")
        self.root.geometry("1000x700")

        # Serial connection state
        self.serial_conn: serial.Serial | None = None
        self.running = False

        # Separate TX / RX parameter dicts
        self.tx_params = {k: v for k, v in PARAMS.items() if k.startswith("Tx ")}
        self.rx_params = {k: v for k, v in PARAMS.items() if not k.startswith("Tx ")}

        # Mapping of parameter names to their StringVar
        self.param_vars: dict[str, tk.StringVar] = {}

        self._configure_style()
        self._build_widgets()

    # --------------------------------------------------------------------- UI
    def _configure_style(self):
        """Apply a simple classic ttk theme for a clean look."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # default theme
        style.configure("TLabel", font=("TkDefaultFont", 9))
        style.configure("TButton", padding=5)
        style.configure("TEntry", padding=3)

    def _build_widgets(self):
        """Construct the interface: serial bar, notebook, version box, output log."""
        # Serial connection bar
        conn_frame = ttk.LabelFrame(self.root, text="Serial Connection")
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Port:").pack(side="left", padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=15,
                                       values=self._available_ports())
        self.port_combo.pack(side="left", padx=5)

        ttk.Label(conn_frame, text="Baudrate:").pack(side="left", padx=5)
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=10).pack(side="left", padx=5)

        ttk.Button(conn_frame, text="Refresh Ports", command=self._refresh_ports).pack(side="left", padx=5)
        ttk.Button(conn_frame, text="Connect", command=self._connect_serial).pack(side="left", padx=5)
        ttk.Button(conn_frame, text="Disconnect", command=self._disconnect_serial).pack(side="left", padx=5)

        # Notebook with TX / RX tabs
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)

        self.tx_tab = ttk.Frame(nb)
        self.rx_tab = ttk.Frame(nb)
        nb.add(self.tx_tab, text="TX Parameters")
        nb.add(self.rx_tab, text="RX Parameters")

        self._populate_param_tab(self.tx_tab, self.tx_params, "TX")
        self._populate_param_tab(self.rx_tab, self.rx_params, "RX")

        # Version box underneath notebook
        version_frame = ttk.Frame(self.root)
        version_frame.pack(fill="x", pady=(0, 5))
        version_frame.columnconfigure(1, weight=1)

        ttk.Label(version_frame, text="Device Version:").grid(row=0, column=0, padx=(10, 5))
        self.version_var = tk.StringVar(value="Not connected")
        ttk.Entry(version_frame, textvariable=self.version_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # Output log
        out_frame = ttk.LabelFrame(self.root, text="Device Output")
        out_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.output_txt = scrolledtext.ScrolledText(out_frame, wrap="word", height=8)
        self.output_txt.pack(fill="both", expand=True)

    # ----------------------------------------------------------- Param Tabs
    def _populate_param_tab(self, tab: ttk.Frame, params: dict, section: str):
        """Add controls and buttons to a single notebook tab."""
        # Scrollable canvas + interior frame
        canvas = tk.Canvas(tab, highlightthickness=0)
        vbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        hbar = ttk.Scrollbar(tab, orient="horizontal", command=canvas.xview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)

        # Parameter rows
        for r, (p_name, opts) in enumerate(params.items()):
            ttk.Label(inner, text=f"{p_name}:").grid(row=r, column=0, sticky="w", padx=5, pady=2)
            var = tk.StringVar()
            self.param_vars[p_name] = var

            if opts is None:
                ttk.Entry(inner, textvariable=var, width=30).grid(row=r, column=1, sticky="ew", padx=5, pady=2)
            else:
                values = [f"{k} = {v}" for k, v in opts.items()]
                ttk.Combobox(inner, values=values, textvariable=var, state="readonly", width=30).grid(
                    row=r, column=1, sticky="ew", padx=5, pady=2)
            inner.columnconfigure(1, weight=1)

        # Bottom buttons (Refresh, Write, Load)
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(btn_frame, text="Refresh Params", command=self._refresh_params).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Write Params", command=lambda: self._write_params(params, section)).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Load Params", command=self._store_params).grid(row=0, column=2, padx=5)

    # ------------------------------------------------------------ Serial I/O
    @staticmethod
    def _available_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def _refresh_ports(self):
        self.port_combo["values"] = self._available_ports()

    def _connect_serial(self):
        try:
            self.serial_conn = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
            self.running = True
            threading.Thread(target=self._serial_reader, daemon=True).start()
            self._print("Connected.")
            self._send("v;")
        except Exception as err:
            messagebox.showerror("Error", str(err))

    def _disconnect_serial(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.serial_conn = None
        self.version_var.set("Not connected")
        self._print("Disconnected.")

    def _send(self, cmd: str):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write((cmd + "\n").encode())
            self._print(f"TX: {cmd}")
        else:
            messagebox.showwarning("Warning", "Serial not connected")

    def _print(self, text: str):
        self.output_txt.insert(tk.END, text + "\n")
        self.output_txt.see(tk.END)

    def _serial_reader(self):
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode(errors="ignore").strip()
                if line:
                    self._print(line)
                    self._process_incoming(line)
            except Exception as exc:
                self._print(f"Serial read error: {exc}")
                break

    # ------------------------------------------------------------- Processing
    def _process_incoming(self, line: str):
        lower = line.lower()
        if any(k in lower for k in ("firmware", "version", "mlrs")) and "=" not in line and not line.startswith(">"):
            self.version_var.set(line)
            return

        if " = " in line and not line.startswith(">"):
            name, val = [x.strip() for x in line.split(" = ", 1)]
            if name not in PARAMS:
                return
            num_val = None
            if "[" in val and "]" in val:
                inside = val.split("[")[-1].split("]")[0]
                if inside.isdigit():
                    num_val = int(inside)
            if PARAMS[name] is None:
                self.param_vars[name].set(val.split(" [")[0])
            else:
                if num_val is not None and num_val in PARAMS[name]:
                    self.param_vars[name].set(f"{num_val} = {PARAMS[name][num_val]}")
                else:
                    for k, v in PARAMS[name].items():
                        if v in val:
                            self.param_vars[name].set(f"{k} = {v}")
                            break

    # ------------------------------------------------------------- Commands
    def _refresh_params(self):
        self._send("pl;")
        self._print("Refreshing parameters...")

    def _write_params(self, params: dict, section: str):
        if not (self.serial_conn and self.serial_conn.is_open):
            messagebox.showwarning("Warning", "Serial not connected")
            return
        self._print(f"Writing {section} parameters...")
        count = 0
        for pname in params:
            value = self.param_vars[pname].get().strip()
            if not value:
                continue
            cmd_val = value.split("=")[0].strip() if "=" in value else value
            cmd_pname = pname.replace(" ", "_")
            self._send(f"p {cmd_pname}={cmd_val};")
            count += 1
        self._print(f"Wrote {count} {section} parameters.")

    def _store_params(self):
        if not (self.serial_conn and self.serial_conn.is_open):
            messagebox.showwarning("Warning", "Serial not connected")
            return
        if messagebox.askyesno("Load Params", "Load stored parameters from device? (pstore;)"):
            self._send("pstore;")
            self._print("Loading parameters from device memory (pstore;)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ParamApp(root)
        root.mainloop()
    except ModuleNotFoundError as mnfe:
        print("Tkinter is not available on this system. Install the python3-tk package to run the GUI.")