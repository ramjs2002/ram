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

        # Set a classic ttk theme if available
        try:
            style = ttk.Style()
            available = style.theme_names()
            if "clam" in available:
                style.theme_use("clam")
            elif "alt" in available:
                style.theme_use("alt")
            # Tweak some spacing for a classic, clean look
            style.configure("TLabel", padding=(4, 2))
            style.configure("TButton", padding=(6, 4))
            style.configure("TCombobox", padding=(2, 2))
            style.configure("TLabelframe", padding=(8, 8))
            style.configure("TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))
        except Exception:
            pass

        self.serial_conn: serial.Serial | None = None
        self.running = False

        # Separate TX and RX parameters
        self.tx_params = {k: v for k, v in PARAMS.items() if k.startswith("Tx ")}
        self.rx_params = {k: v for k, v in PARAMS.items() if not k.startswith("Tx ")}

        # Tk variables for all params
        self.param_vars: dict[str, tk.StringVar] = {}

        # Version string
        self.version_var = tk.StringVar(value="Not connected")

        self._build_ui()

        # Graceful close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -------------------------- UI ---------------------------
    def _build_ui(self) -> None:
        # Serial connection at top
        conn_frame = ttk.LabelFrame(self.root, text="Serial Connection")
        conn_frame.pack(fill="x", padx=8, pady=8)

        ttk.Label(conn_frame, text="Port:").pack(side="left", padx=(8, 4), pady=4)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            conn_frame,
            textvariable=self.port_var,
            values=self.get_serial_ports(),
            width=18,
            state="readonly",
        )
        self.port_combo.pack(side="left", padx=(0, 8), pady=4)

        refresh_ports_btn = ttk.Button(conn_frame, text="Refresh Ports", command=self._refresh_ports)
        refresh_ports_btn.pack(side="left", padx=(0, 8), pady=4)

        ttk.Label(conn_frame, text="Baudrate:").pack(side="left", padx=(8, 4), pady=4)
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=10).pack(side="left", padx=(0, 8), pady=4)

        ttk.Button(conn_frame, text="Connect", command=self.connect_serial).pack(side="left", padx=(0, 8), pady=4)
        ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_serial).pack(side="left", padx=(0, 8), pady=4)

        # Notebook with TX and RX tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=(0, 0))

        self.tx_tab = ttk.Frame(notebook)
        self.rx_tab = ttk.Frame(notebook)
        notebook.add(self.tx_tab, text="TX")
        notebook.add(self.rx_tab, text="RX")

        # Build each tab
        self._build_param_tab(self.tx_tab, self.tx_params, section_label="TX")
        self._build_param_tab(self.rx_tab, self.rx_params, section_label="RX")

        # Version box centered below tabs
        version_frame_outer = ttk.Frame(self.root)
        version_frame_outer.pack(fill="x", padx=8, pady=8)
        version_frame = ttk.Frame(version_frame_outer)
        version_frame.pack()
        ttk.Label(version_frame, text="Device Version:", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(0, 8))
        self.version_entry = ttk.Entry(
            version_frame,
            textvariable=self.version_var,
            state="readonly",
            width=60,
        )
        self.version_entry.pack(side="left")

        # Output log at bottom
        output_frame = ttk.LabelFrame(self.root, text="Device Output")
        output_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=12)
        self.output_text.pack(fill="both", expand=True)

    def _build_param_tab(self, parent: ttk.Frame, params_dict: dict, section_label: str) -> None:
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Scrollable area for parameters
        canvas = tk.Canvas(container, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        params_frame = ttk.Frame(canvas)
        params_frame_id = canvas.create_window((0, 0), window=params_frame, anchor="nw")

        def on_configure(event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Match frame width to canvas width
            canvas_width = event.width
            canvas.itemconfig(params_frame_id, width=canvas_width)

        params_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_configure)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        # Build the parameter grid
        current_row = 0
        for param_name, options in params_dict.items():
            ttk.Label(params_frame, text=f"{param_name}:").grid(
                row=current_row, column=0, sticky="w", padx=(6, 10), pady=4
            )

            var = tk.StringVar()
            self.param_vars[param_name] = var

            if options is None:
                entry = ttk.Entry(params_frame, textvariable=var, width=28)
                entry.grid(row=current_row, column=1, sticky="ew", padx=(0, 6), pady=4)
            else:
                values = [f"{k} = {v}" for k, v in options.items()]
                combo = ttk.Combobox(params_frame, textvariable=var, values=values, width=28, state="readonly")
                combo.grid(row=current_row, column=1, sticky="ew", padx=(0, 6), pady=4)

            current_row += 1

        params_frame.columnconfigure(1, weight=1)

        # Mousewheel scrolling for this canvas only when pointer is over it
        def _on_mousewheel(event: tk.Event) -> None:
            delta = int(-1 * (event.delta / 120)) if event.delta else (1 if event.num == 5 else -1)
            canvas.yview_scroll(delta, "units")

        def _bind_mousewheel(_: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(_: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # Control buttons at bottom of the tab
        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=8, pady=(0, 8))

        btn_refresh = ttk.Button(controls, text="Refresh Params", command=self.refresh_params)
        btn_refresh.pack(side="left", padx=(0, 8))

        btn_write = ttk.Button(
            controls,
            text="Write Params",
            command=lambda pd=params_dict, lbl=section_label: self.write_params(pd, lbl),
        )
        btn_write.pack(side="left", padx=(0, 8))

        btn_store = ttk.Button(controls, text="Load Params", command=self.load_params)
        btn_store.pack(side="left", padx=(0, 8))

    # ----------------------- Serial helpers -----------------------
    def _refresh_ports(self) -> None:
        try:
            ports = self.get_serial_ports()
            self.port_combo["values"] = ports
            if ports:
                if self.port_var.get() not in ports:
                    self.port_var.set(ports[0])
            else:
                self.port_var.set("")
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to refresh ports: {ex}")

    def get_serial_ports(self) -> list[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect_serial(self) -> None:
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.print_output("Already connected.")
                return

            port = self.port_var.get().strip()
            baud = int(self.baud_var.get().strip())
            if not port:
                messagebox.showwarning("Warning", "Select a serial port")
                return

            self.serial_conn = serial.Serial(port, baud, timeout=1)
            self.running = True
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.print_output(f"Connected to {port} @ {baud}.")

            # Request device version after connection
            self.request_version()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def disconnect_serial(self) -> None:
        self.running = False
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
                self.print_output("Disconnected.")
        finally:
            self.serial_conn = None
            self.version_var.set("Not connected")

    def on_close(self) -> None:
        try:
            self.running = False
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
        finally:
            self.root.destroy()

    def request_version(self) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            self.send_command("v;")

    # --------------------- Serial I/O loop ---------------------
    def read_serial(self) -> None:
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                self.print_output(line)

                # Version detection (simple heuristics)
                lower_line = line.lower()
                if any(k in lower_line for k in ["version", "firmware", "mlrs"]) and (
                    not line.startswith(">") and "=" not in line
                ):
                    self._set_version_text(line)

                # Parameter update lines: "Name = value [idx]"
                if " = " in line and not line.startswith(">"):
                    name, value = line.split(" = ", 1)
                    name = name.strip()
                    value = value.strip()

                    num_value = None
                    if "[" in value and "]" in value:
                        inside = value.split("[")[-1].split("]")[0]
                        if inside.isdigit():
                            num_value = int(inside)

                    if name in PARAMS and name in self.param_vars:
                        if PARAMS[name] is None:
                            # Free text parameter
                            display_value = value.split(" [")[0]
                            self._set_param_value(name, display_value)
                        else:
                            # Dropdown parameter
                            if num_value is not None and num_value in PARAMS[name]:
                                self._set_param_value(name, f"{num_value} = {PARAMS[name][num_value]}")
                            else:
                                # Try to match by label
                                for k, v in PARAMS[name].items():
                                    if v in value:
                                        self._set_param_value(name, f"{k} = {v}")
                                        break
            except Exception as e:
                self.print_output(f"Serial read error: {e}")
                break

    # ------------------- UI-safe updaters -------------------
    def print_output(self, text: str) -> None:
        def _append() -> None:
            self.output_text.insert(tk.END, text + "\n")
            self.output_text.see(tk.END)

        try:
            self.output_text.after(0, _append)
        except Exception:
            pass

    def _set_version_text(self, text: str) -> None:
        try:
            self.version_entry.after(0, lambda: self.version_var.set(text))
        except Exception:
            pass

    def _set_param_value(self, name: str, value: str) -> None:
        var = self.param_vars.get(name)
        if not var:
            return
        try:
            self.root.after(0, lambda: var.set(value))
        except Exception:
            pass

    # ------------------- Commands -------------------
    def send_command(self, cmd: str) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write((cmd + "\n").encode())
                self.print_output(f"TX: {cmd}")
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to send command: {ex}")
        else:
            messagebox.showwarning("Warning", "Not connected to serial device")

    def refresh_params(self) -> None:
        self.send_command("pl;")
        self.print_output("Refreshing all parameters...")

    def write_params(self, params_dict: dict, section_type: str) -> None:
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return

        self.print_output(f"Writing {section_type} parameters to device...")
        params_written = 0

        for param_name in params_dict.keys():
            var = self.param_vars.get(param_name)
            if not var:
                continue
            current_value = var.get().strip()
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
        # Per requirement: Load Params triggers pstore;
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return
        self.send_command("pstore;")
        self.print_output("Executing 'pstore;' (Load Params)...")


if __name__ == "__main__":
    root = tk.Tk()
    app = ParamApp(root)
    root.mainloop()