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


class ParamApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("mLRS Parameter Control")
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)

        # Classic ttk look
        self._configure_style()

        self.serial_conn = None
        self.running = False

        # Separate TX and RX parameters
        self.tx_params = {k: v for k, v in PARAMS.items() if k.startswith("Tx ")}
        self.rx_params = {k: v for k, v in PARAMS.items() if not k.startswith("Tx ")}

        self.param_vars: dict[str, tk.StringVar] = {}

        self._create_widgets()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            if "classic" in style.theme_names():
                style.theme_use("classic")
            else:
                style.theme_use("clam")
        except Exception:
            pass

        base_font = ("TkDefaultFont", 10)
        bold_font = ("TkDefaultFont", 10, "bold")

        # General paddings and fonts for a classic look
        style.configure("TFrame", padding=6)
        style.configure("TLabelframe", padding=10)
        style.configure("TLabelframe.Label", font=bold_font)
        style.configure("TLabel", font=base_font)
        style.configure("TEntry", padding=3, font=base_font)
        style.configure("TCombobox", padding=2, font=base_font)
        style.configure("TButton", padding=(8, 4), font=base_font)
        style.configure("TNotebook", padding=4)
        style.configure("TNotebook.Tab", padding=(14, 8))

    def _create_widgets(self) -> None:
        # Serial connection frame at top
        conn_frame = ttk.LabelFrame(self.root, text="Serial Connection")
        conn_frame.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(conn_frame, text="Port:").pack(side="left", padx=(6, 4))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            conn_frame,
            textvariable=self.port_var,
            values=self.get_serial_ports(),
            width=20,
            state="readonly",
        )
        self.port_combo.pack(side="left", padx=(0, 12))

        ttk.Label(conn_frame, text="Baudrate:").pack(side="left", padx=(6, 4))
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=10).pack(side="left", padx=(0, 12))

        ttk.Button(conn_frame, text="Connect", command=self.connect_serial).pack(side="left", padx=(0, 6))
        ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_serial).pack(side="left", padx=(0, 6))

        # Notebook for TX and RX tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        self.tx_tab = ttk.Frame(notebook)
        self.rx_tab = ttk.Frame(notebook)
        notebook.add(self.tx_tab, text="TX")
        notebook.add(self.rx_tab, text="RX")

        self._create_param_tab(self.tx_tab, self.tx_params, section_type="TX")
        self._create_param_tab(self.rx_tab, self.rx_params, section_type="RX")

        # Version box (centered below tabs)
        version_frame = ttk.Frame(self.root)
        version_frame.pack(fill="x", padx=8, pady=(4, 4))

        version_inner = ttk.Frame(version_frame)
        version_inner.pack()
        ttk.Label(version_inner, text="Device Version:", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(4, 6))
        self.version_var = tk.StringVar(value="Not connected")
        self.version_entry = ttk.Entry(
            version_inner, textvariable=self.version_var, state="readonly", width=70
        )
        self.version_entry.pack(side="left", padx=(0, 4))

        # Output frame at bottom
        output_frame = ttk.LabelFrame(self.root, text="Device Output")
        output_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10)
        self.output_text.pack(fill="both", expand=True)

    def _create_param_tab(self, tab_parent: ttk.Frame, params_dict: dict, section_type: str) -> None:
        # Container with scrollable area
        container = ttk.Frame(tab_parent)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)

        # Resize canvas window to match width
        def _on_frame_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_frame_configure)

        # Parameters grid
        row_index = 0
        for param_name, options in params_dict.items():
            label = ttk.Label(scrollable, text=f"{param_name}:")
            label.grid(row=row_index, column=0, sticky="w", padx=(8, 12), pady=4)

            var = tk.StringVar()
            self.param_vars[param_name] = var

            if options is None:
                entry = ttk.Entry(scrollable, textvariable=var, width=28)
                entry.grid(row=row_index, column=1, sticky="ew", padx=(0, 8), pady=4)
            else:
                values = [f"{k} = {v}" for k, v in options.items()]
                combo = ttk.Combobox(scrollable, textvariable=var, values=values, width=28, state="readonly")
                combo.grid(row=row_index, column=1, sticky="ew", padx=(0, 8), pady=4)

            row_index += 1

        scrollable.columnconfigure(1, weight=1)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        # Mousewheel support (Windows/Mac). For Linux, also bind Button-4/5
        def _on_mousewheel(event):
            delta = 0
            if event.num == 5 or event.delta < 0:
                delta = 1
            elif event.num == 4 or event.delta > 0:
                delta = -1
            canvas.yview_scroll(delta, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        # Bottom controls inside each tab
        controls = ttk.Frame(tab_parent)
        controls.pack(fill="x", padx=8, pady=(6, 4))

        btn_refresh = ttk.Button(controls, text="Refresh Params", command=self.refresh_params)
        btn_write = ttk.Button(controls, text="Write Params", command=lambda: self.write_params(params_dict, section_type))
        btn_load = ttk.Button(controls, text="Load Params", command=self.load_params)

        # Layout buttons horizontally and centered
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(4, weight=1)

        btn_refresh.grid(row=0, column=1, padx=6, pady=2)
        btn_write.grid(row=0, column=2, padx=6, pady=2)
        btn_load.grid(row=0, column=3, padx=6, pady=2)

    def get_serial_ports(self) -> list[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect_serial(self) -> None:
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            if not port:
                messagebox.showwarning("Warning", "Please select a serial port")
                return
            self.serial_conn = serial.Serial(port, baud, timeout=1)
            self.running = True
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.print_output("Connected to serial port.")

            # Request device version after connection
            self.request_version()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def disconnect_serial(self) -> None:
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.print_output("Disconnected.")
            self.version_var.set("Not connected")

    def request_version(self) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            self.send_command("v;")

    def read_serial(self) -> None:
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                self.print_output(line)

                # Version line heuristics
                lowered = line.lower()
                if any(keyword in lowered for keyword in ["version", "firmware", "mlrs"]) and not line.startswith(">"):
                    if "=" not in line:
                        self.version_var.set(line)

                # Parameter updates of the form: Name = value [n]
                if " = " in line and not line.startswith(">") and not line.startswith("TX:"):
                    name, value = line.split(" = ", 1)
                    name = name.strip()
                    value = value.strip()

                    # Extract numeric key from brackets if present
                    num_value = None
                    if "[" in value and "]" in value:
                        inside = value.split("[")[-1].split("]")[0]
                        if inside.isdigit():
                            num_value = int(inside)

                    if name in PARAMS:
                        if PARAMS[name] is None:
                            # Free text parameter
                            self.param_vars[name].set(value.split(" [")[0])
                        else:
                            # Dropdown parameter by numeric key or string match
                            if num_value is not None and num_value in PARAMS[name]:
                                self.param_vars[name].set(f"{num_value} = {PARAMS[name][num_value]}")
                            else:
                                for k, v in PARAMS[name].items():
                                    if v in value:
                                        self.param_vars[name].set(f"{k} = {v}")
                                        break
            except Exception as exc:
                self.print_output(f"Serial read error: {str(exc)}")
                break

    def print_output(self, text: str) -> None:
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def send_command(self, cmd: str) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write((cmd + "\n").encode())
                self.print_output(f"TX: {cmd}")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to send command: {exc}")
        else:
            messagebox.showwarning("Warning", "Not connected to serial device")

    def refresh_params(self) -> None:
        self.send_command("pl;")
        self.print_output("Refreshing parameters (pl;) ...")

    def write_params(self, params_dict: dict, section_type: str) -> None:
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return

        self.print_output(f"Writing {section_type} parameters to device...")
        params_written = 0

        for param_name in params_dict.keys():
            if param_name not in self.param_vars:
                continue

            current_value = self.param_vars[param_name].get().strip()
            if not current_value:
                continue

            cmd_param_name = param_name.replace(" ", "_")

            if PARAMS[param_name] is None:
                cmd_value = current_value
            else:
                if "=" in current_value:
                    cmd_value = current_value.split("=")[0].strip()
                else:
                    continue

            command = f"p {cmd_param_name}={cmd_value};"
            self.send_command(command)
            params_written += 1

        self.print_output(f"Finished writing {params_written} {section_type} parameters.")

    def load_params(self) -> None:
        # Per request: Load Params triggers pstore;
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return
        self.send_command("pstore;")
        self.print_output("Executing pstore; (Load Params)")


if __name__ == "__main__":
    root = tk.Tk()
    app = ParamApp(root)
    root.mainloop()