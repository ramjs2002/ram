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
    def __init__(self, root):
        self.root = root
        self.root.title("mLRS Parameter Control - Enhanced")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # Configure styles for classic look
        self.setup_styles()
        
        self.serial_conn = None
        self.running = False
        
        # Separate TX and RX parameters
        self.tx_params = {k: v for k, v in PARAMS.items() if k.startswith("Tx ")}
        self.rx_params = {k: v for k, v in PARAMS.items() if not k.startswith("Tx ")}
        
        self.param_vars = {}
        
        self.create_widgets()

    def setup_styles(self):
        """Configure ttk styles for a classic look"""
        style = ttk.Style()
        
        # Configure classic button style
        style.configure("Classic.TButton",
                       padding=(10, 5),
                       font=("Arial", 9, "bold"))
        
        # Configure frame styles
        style.configure("Card.TLabelFrame",
                       background="#f8f8f8",
                       relief="raised",
                       borderwidth=2)
        
        # Configure notebook style
        style.configure("Classic.TNotebook",
                       background="#e0e0e0",
                       borderwidth=2,
                       relief="raised")
        
        style.configure("Classic.TNotebook.Tab",
                       padding=(20, 8),
                       font=("Arial", 10, "bold"))

    def create_widgets(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Serial connection frame at top
        self.create_connection_frame(main_container)
        
        # Tabbed interface for parameters
        self.create_tabbed_interface(main_container)
        
        # Version display (centered below tabs)
        self.create_version_frame(main_container)
        
        # Output frame at bottom
        self.create_output_frame(main_container)

    def create_connection_frame(self, parent):
        """Create the serial connection controls at the top"""
        conn_frame = ttk.LabelFrame(parent, text="Serial Connection", style="Card.TLabelFrame")
        conn_frame.pack(fill="x", pady=(0, 10))
        
        # Inner frame for better padding
        inner_frame = ttk.Frame(conn_frame)
        inner_frame.pack(fill="x", padx=10, pady=8)
        
        # Port selection
        ttk.Label(inner_frame, text="Port:", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(inner_frame, textvariable=self.port_var, 
                                      values=self.get_serial_ports(), width=15, font=("Arial", 9))
        self.port_combo.grid(row=0, column=1, padx=(0, 20))
        
        # Baudrate
        ttk.Label(inner_frame, text="Baudrate:", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.baud_var = tk.StringVar(value="115200")
        baud_entry = ttk.Entry(inner_frame, textvariable=self.baud_var, width=10, font=("Arial", 9))
        baud_entry.grid(row=0, column=3, padx=(0, 20))
        
        # Connection buttons
        ttk.Button(inner_frame, text="Connect", command=self.connect_serial, 
                  style="Classic.TButton").grid(row=0, column=4, padx=5)
        ttk.Button(inner_frame, text="Disconnect", command=self.disconnect_serial, 
                  style="Classic.TButton").grid(row=0, column=5, padx=5)
        
        # Refresh ports button
        ttk.Button(inner_frame, text="Refresh Ports", command=self.refresh_ports, 
                  style="Classic.TButton").grid(row=0, column=6, padx=(20, 0))

    def create_tabbed_interface(self, parent):
        """Create the tabbed interface for TX and RX parameters"""
        # Notebook widget
        self.notebook = ttk.Notebook(parent, style="Classic.TNotebook")
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # TX Tab
        self.tx_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tx_tab, text="TX Parameters")
        self.create_param_tab(self.tx_tab, self.tx_params, "TX")
        
        # RX Tab
        self.rx_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.rx_tab, text="RX Parameters")
        self.create_param_tab(self.rx_tab, self.rx_params, "RX")

    def create_param_tab(self, tab_frame, params_dict, section_type):
        """Create a parameter tab with scrollable content and controls"""
        # Main container for the tab
        main_container = ttk.Frame(tab_frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Parameters frame (scrollable)
        params_container = ttk.LabelFrame(main_container, text=f"{section_type} Configuration", 
                                        style="Card.TLabelFrame")
        params_container.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create scrollable frame
        canvas = tk.Canvas(params_container, highlightthickness=0, bg="#f8f8f8")
        scrollbar = ttk.Scrollbar(params_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add parameters to scrollable frame
        self.populate_parameters(scrollable_frame, params_dict)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Control buttons frame
        self.create_tab_controls(main_container, params_dict, section_type)

    def populate_parameters(self, parent_frame, params_dict):
        """Populate parameters in a grid layout"""
        row = 0
        for param, options in params_dict.items():
            # Create frame for each parameter row
            param_frame = ttk.Frame(parent_frame)
            param_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=3)
            param_frame.columnconfigure(1, weight=1)
            
            # Parameter label
            label = ttk.Label(param_frame, text=param + ":", 
                            font=("Arial", 9, "bold"), width=20, anchor="w")
            label.grid(row=0, column=0, sticky="w", padx=(0, 10))

            # Parameter variable
            var = tk.StringVar()
            self.param_vars[param] = var

            if options is None:
                # Text entry for free text parameters
                entry = ttk.Entry(param_frame, textvariable=var, width=30, font=("Arial", 9))
                entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
            else:
                # Combobox for dropdown parameters
                combo = ttk.Combobox(param_frame, textvariable=var, 
                                   values=[f"{k} = {v}" for k, v in options.items()], 
                                   width=30, state="readonly", font=("Arial", 9))
                combo.grid(row=0, column=1, sticky="ew", padx=(0, 5))

            row += 1
        
        # Configure parent frame column weight
        parent_frame.columnconfigure(0, weight=1)

    def create_tab_controls(self, parent, params_dict, section_type):
        """Create control buttons for each tab"""
        controls_frame = ttk.LabelFrame(parent, text="Controls", style="Card.TLabelFrame")
        controls_frame.pack(fill="x", pady=(0, 5))
        
        # Inner frame for button layout
        btn_container = ttk.Frame(controls_frame)
        btn_container.pack(padx=10, pady=8)
        
        # Three buttons in a row
        refresh_btn = ttk.Button(btn_container, text="Refresh Params", 
                               command=self.refresh_params, style="Classic.TButton", width=15)
        refresh_btn.grid(row=0, column=0, padx=5)
        
        write_btn = ttk.Button(btn_container, text=f"Write {section_type}", 
                             command=lambda: self.write_params(params_dict, section_type), 
                             style="Classic.TButton", width=15)
        write_btn.grid(row=0, column=1, padx=5)
        
        store_btn = ttk.Button(btn_container, text="Store Params", 
                             command=self.store_params, style="Classic.TButton", width=15)
        store_btn.grid(row=0, column=2, padx=5)

    def create_version_frame(self, parent):
        """Create the version display frame"""
        version_frame = ttk.LabelFrame(parent, text="Device Information", style="Card.TLabelFrame")
        version_frame.pack(fill="x", pady=(0, 10))
        
        # Center the version info
        version_container = ttk.Frame(version_frame)
        version_container.pack(expand=True, padx=10, pady=8)
        
        ttk.Label(version_container, text="Firmware Version:", 
                 font=("Arial", 10, "bold")).pack(side="left", padx=(0, 10))
        
        self.version_var = tk.StringVar(value="Not connected - Please connect to view version")
        self.version_entry = ttk.Entry(version_container, textvariable=self.version_var, 
                                     state="readonly", width=50, font=("Arial", 9),
                                     justify="center")
        self.version_entry.pack(side="left")

    def create_output_frame(self, parent):
        """Create the output log frame"""
        output_frame = ttk.LabelFrame(parent, text="Device Communication Log", style="Card.TLabelFrame")
        output_frame.pack(fill="both", expand=True)
        
        # Output text with classic styling
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=8,
                                                   font=("Consolas", 9), bg="#ffffff",
                                                   relief="sunken", borderwidth=2)
        self.output_text.pack(fill="both", expand=True, padx=10, pady=8)

    def get_serial_ports(self):
        """Get list of available serial ports"""
        return [port.device for port in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        ports = self.get_serial_ports()
        self.port_combo['values'] = ports
        self.print_output("Serial ports refreshed.")

    def connect_serial(self):
        """Connect to the selected serial port"""
        try:
            if not self.port_var.get():
                messagebox.showwarning("Warning", "Please select a serial port")
                return
                
            self.serial_conn = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
            self.running = True
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.print_output(f"✓ Connected to {self.port_var.get()} at {self.baud_var.get()} baud")
            
            # Request device version after connection
            self.request_version()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")

    def disconnect_serial(self):
        """Disconnect from the serial port"""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.print_output("✗ Disconnected from serial port")
            self.version_var.set("Not connected - Please connect to view version")

    def request_version(self):
        """Request device version information"""
        if self.serial_conn and self.serial_conn.is_open:
            self.send_command("v;")
            self.print_output("Requesting device version...")

    def read_serial(self):
        """Read data from serial port in background thread"""
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode(errors="ignore").strip()
                if line:
                    self.print_output(f"RX: {line}")

                    # Check for version information
                    if any(keyword in line.lower() for keyword in ['version', 'firmware', 'mlrs']):
                        if not line.startswith('>') and not line.startswith('TX:') and '=' not in line:
                            # Update version display
                            self.version_var.set(line)
                            self.print_output(f"✓ Device version detected: {line}")

                    # Auto-update UI when parameters are received
                    if " = " in line and not line.startswith(">") and not line.startswith("TX:"):
                        self.update_parameter_from_response(line)
                        
            except Exception as e:
                self.print_output(f"✗ Serial read error: {str(e)}")
                break

    def update_parameter_from_response(self, line):
        """Update parameter UI from device response"""
        try:
            name, value = line.split(" = ", 1)
            name = name.strip()
            value = value.strip()

            # Extract numeric key from [ ] if available
            num_value = None
            if "[" in value and "]" in value:
                inside_brackets = value.split("[")[-1].split("]")[0]
                if inside_brackets.isdigit():
                    num_value = int(inside_brackets)

            if name in PARAMS:
                if PARAMS[name] is None:
                    # Free text parameter
                    self.param_vars[name].set(value.split(" [")[0])
                else:
                    # Dropdown parameter
                    if num_value is not None and num_value in PARAMS[name]:
                        self.param_vars[name].set(f"{num_value} = {PARAMS[name][num_value]}")
                    else:
                        # Try to match by value string
                        for k, v in PARAMS[name].items():
                            if v in value:
                                self.param_vars[name].set(f"{k} = {v}")
                                break
        except Exception as e:
            self.print_output(f"✗ Error parsing parameter: {str(e)}")

    def print_output(self, text):
        """Add text to the output log with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}"
        
        self.output_text.insert(tk.END, formatted_text + "\n")
        self.output_text.see(tk.END)
        
        # Limit output text size to prevent memory issues
        lines = int(self.output_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.output_text.delete('1.0', '500.0')

    def send_command(self, cmd):
        """Send command to the serial device"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write((cmd + "\n").encode())
            self.print_output(f"TX: {cmd}")
        else:
            messagebox.showwarning("Warning", "Not connected to serial device")

    def refresh_params(self):
        """Send pl; command to retrieve all parameters from device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return
            
        self.send_command("pl;")
        self.print_output("🔄 Refreshing all parameters...")

    def write_params(self, params_dict, section_type):
        """Loop through specified section parameters and send them to device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return

        # Confirmation dialog
        result = messagebox.askyesno(
            "Confirm Write", 
            f"This will write all {section_type} parameters to the device.\n\nContinue?"
        )
        
        if not result:
            return

        self.print_output(f"📤 Writing {section_type} parameters to device...")
        
        params_written = 0
        for param_name in params_dict.keys():
            if param_name not in self.param_vars:
                continue
                
            current_value = self.param_vars[param_name].get().strip()
            
            if not current_value:
                continue  # Skip empty parameters
            
            # Convert parameter name (replace spaces with underscores)
            cmd_param_name = param_name.replace(" ", "_")
            
            if PARAMS[param_name] is None:
                # Free text parameter - send as-is
                cmd_value = current_value
            else:
                # Dropdown parameter - extract the key (number before "=")
                if "=" in current_value:
                    cmd_value = current_value.split("=")[0].strip()
                else:
                    continue  # Skip if format is incorrect
            
            # Send the command
            command = f"p {cmd_param_name}={cmd_value};"
            self.send_command(command)
            params_written += 1

        self.print_output(f"✓ Finished writing {params_written} {section_type} parameters")

    def store_params(self):
        """Send pstore; command to permanently store settings on device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Warning", "Not connected to serial device")
            return
        
        # Confirmation dialog with warning
        result = messagebox.askyesno(
            "Confirm Store", 
            "⚠️  PERMANENT STORAGE  ⚠️\n\n"
            "This will permanently store ALL current settings to the device.\n"
            "This action cannot be undone!\n\n"
            "Are you sure you want to continue?",
            icon="warning"
        )
        
        if result:
            self.send_command("pstore;")
            self.print_output("💾 Storing parameters permanently to device...")


def main():
    """Main application entry point"""
    root = tk.Tk()
    
    # Set application icon and properties
    root.resizable(True, True)
    root.minsize(800, 600)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (900 // 2)
    y = (root.winfo_screenheight() // 2) - (700 // 2)
    root.geometry(f"900x700+{x}+{y}")
    
    app = ParamApp(root)
    
    # Handle window close event
    def on_closing():
        if app.serial_conn and app.serial_conn.is_open:
            app.disconnect_serial()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()