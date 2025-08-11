import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading


# Parameters and options
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
    "Tx Buzzer": None
}

# ------------------------------ GUI APPLICATION ----------------------------- #

class ParamApp:
    """Main application class for mLRS parameter control via serial interface."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mLRS Parameter Control")
        self.root.geometry("1000x700")
        self.serial_conn = None
        self.running = False

        # Split parameters into TX and RX
        self.tx_params = {k: v for k, v in PARAMS.items() if k.startswith("Tx ")}
        self.rx_params = {k: v for k, v in PARAMS.items() if not k.startswith("Tx ")}
        self.param_vars: dict[str, tk.StringVar] = {}

        self._configure_style()
        self._build_widgets()

    # --------------------------------------------------------------------- UI #
    def _configure_style(self):
        """Apply a classic ttk style."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            # fall back to default if clam unavailable
            pass
        style.configure("TLabel", font=("TkDefaultFont", 9))
        style.configure("TButton", padding=5)
        style.configure("TEntry", padding=3)

    def _build_widgets(self):
        """Construct the complete interface."""
        # 1. Serial connection controls (top)
        conn_f = ttk.LabelFrame(self.root, text="Serial Connection")
        conn_f.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_f, text="Port:").pack(side="left", padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_f, textvariable=self.port_var, width=15,
                                       values=self._available_ports())
        self.port_combo.pack(side="left", padx=5)

        ttk.Label(conn_f, text="Baudrate:").pack(side="left", padx=5)
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(conn_f, textvariable=self.baud_var, width=10).pack(side="left", padx=5)

        ttk.Button(conn_f, text="Refresh Ports", command=self._refresh_ports).pack(side="left", padx=5)
        ttk.Button(conn_f, text="Connect", command=self._connect_serial).pack(side="left", padx=5)
        ttk.Button(conn_f, text="Disconnect", command=self._disconnect_serial).pack(side="left", padx=5)

        # 2. Notebook for TX / RX parameters
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)

        self.tx_frame = ttk.Frame(nb)
        self.rx_frame = ttk.Frame(nb)
        nb.add(self.tx_frame, text="TX Parameters")
        nb.add(self.rx_frame, text="RX Parameters")

        self._create_param_tab(self.tx_frame, self.tx_params, "TX")
        self._create_param_tab(self.rx_frame, self.rx_params, "RX")

        # 3. Version info (below notebook)
        version_container = ttk.Frame(self.root)
        version_container.pack(fill="x", pady=(0, 5))
        version_container.columnconfigure(1, weight=1)

        ttk.Label(version_container, text="Device Version:").grid(row=0, column=0, padx=(10, 5))
        self.version_var = tk.StringVar(value="Not connected")
        ttk.Entry(version_container, textvariable=self.version_var, state="readonly", width=60)
        version_entry = ttk.Entry(version_container, textvariable=self.version_var, state="readonly")
        version_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # 4. Output log (bottom)
        output_f = ttk.LabelFrame(self.root, text="Device Output")
        output_f.pack(fill="both", expand=True, padx=10, pady=5)
        self.output_txt = scrolledtext.ScrolledText(output_f, wrap="word", height=8)
        self.output_txt.pack(fill="both", expand=True)

    # --------------------------------- PARAM TABS -------------------------- #
    def _create_param_tab(self, parent: ttk.Frame, params: dict, section: str):
        """Populate a notebook tab with parameter controls and action buttons."""
        # Scrollable area for parameters
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrl = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrl_h = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrl.set, xscrollcommand=scrl_h.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrl.grid(row=0, column=1, sticky="ns")
        scrl_h.grid(row=1, column=0, sticky="ew")

        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        # Add parameters to grid
        for r, (p_name, options) in enumerate(params.items()):
            ttk.Label(scroll_frame, text=f"{p_name}:").grid(row=r, column=0, sticky="w", padx=5, pady=2)
            var = tk.StringVar()
            self.param_vars[p_name] = var

            if options is None:
                ttk.Entry(scroll_frame, textvariable=var, width=30).grid(row=r, column=1, sticky="ew", padx=5, pady=2)
            else:
                choices = [f"{k} = {v}" for k, v in options.items()]
                ttk.Combobox(scroll_frame, values=choices, textvariable=var, state="readonly", width=30)
                combo = ttk.Combobox(scroll_frame, values=choices, textvariable=var, state="readonly", width=30)
                combo.grid(row=r, column=1, sticky="ew", padx=5, pady=2)

            scroll_frame.columnconfigure(1, weight=1)

        # Action buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(btn_frame, text="Refresh Params", command=self._refresh_params).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Write Params", command=lambda: self._write_params(params, section)).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Load Params", command=self._store_params).grid(row=0, column=2, padx=5)

    # ----------------------------- SERIAL HANDLING ------------------------- #
    @staticmethod
    def _available_ports():
        return [port.device for port in serial.tools.list_ports.comports()]

    def _refresh_ports(self):
        self.port_combo["values"] = self._available_ports()

    def _connect_serial(self):
        try:
            self.serial_conn = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
            self.running = True
            threading.Thread(target=self._read_serial, daemon=True).start()
            self._print_output("Connected.")
            self._request_version()
        except Exception as exc:
            messagebox.showerror("Connection Error", str(exc))

    def _disconnect_serial(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.serial_conn = None
        self.version_var.set("Not connected")
        self._print_output("Disconnected.")

    # ---------------------------- SERIAL I/O HELPERS ----------------------- #
    def _send_cmd(self, cmd: str):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write((cmd + "\n").encode())
            self._print_output(f"TX: {cmd}")
        else:
            messagebox.showwarning("Warning", "Serial not connected")

    def _print_output(self, text: str):
        self.output_txt.insert(tk.END, text + "\n")
        self.output_txt.see(tk.END)

    def _request_version(self):
        self._send_cmd("v;")

    def _read_serial(self):
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                self._print_output(line)
                self._handle_incoming(line)
            except Exception as exc:
                self._print_output(f"Serial read error: {exc}")
                break

    # ------------------------------ LOGIC ---------------------------------- #
    def _handle_incoming(self, line: str):
        # Version handling
        lower = line.lower()
        if any(k in lower for k in ("firmware", "version", "mlrs")) and "=" not in line and not line.startswith(">"):
            self.version_var.set(line)
            return

        # Parameter update e.g. "Bind Phrase = hello [0]"
        if " = " in line and not line.startswith(">"):
            name, value = [x.strip() for x in line.split(" = ", 1)]
            if name not in PARAMS:
                return

            num_value = None
            if "[" in value and "]" in value:
                inside = value.split("[")[-1].split("]")[0]
                if inside.isdigit():
                    num_value = int(inside)

            if PARAMS[name] is None:
                self.param_vars[name].set(value.split(" [")[0])
            else:
                if num_value is not None and num_value in PARAMS[name]:
                    self.param_vars[name].set(f"{num_value} = {PARAMS[name][num_value]}")
                else:
                    for k, v in PARAMS[name].items():
                        if v in value:
                            self.param_vars[name].set(f"{k} = {v}")
                            break

    # ----------------------------- COMMANDS -------------------------------- #
    def _refresh_params(self):
        self._send_cmd("pl;")
        self._print_output("Refreshing parameters...")

    def _write_params(self, params_dict: dict, section: str):
        if not (self.serial_conn and self.serial_conn.is_open):
            messagebox.showwarning("Warning", "Serial not connected")
            return
        self._print_output(f"Writing {section} parameters ...")
        count = 0
        for p_name in params_dict:
            val_str = self.param_vars[p_name].get().strip()
            if not val_str:
                continue
            cmd_value = val_str.split("=")[0].strip() if "=" in val_str else val_str
            cmd_pname = p_name.replace(" ", "_")
            self._send_cmd(f"p {cmd_pname}={cmd_value};")
            count += 1
        self._print_output(f"Wrote {count} {section} parameters.")

    def _store_params(self):
        if not (self.serial_conn and self.serial_conn.is_open):
            messagebox.showwarning("Warning", "Serial not connected")
            return
        if messagebox.askyesno("Load Params", "Load stored parameters from device? (pstore;)"):
            self._send_cmd("pstore;")
            self._print_output("Loading parameters from device memory (pstore;)")


# ----------------------------------- MAIN --------------------------------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = ParamApp(root)
    root.mainloop()