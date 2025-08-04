#!/usr/bin/env python3
"""
Ultrex Drones ESP32 Flasher
A professional firmware flashing tool for ESP32 microcontrollers
"""

import sys
import os
import subprocess
import threading
import time
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QComboBox, QProgressDialog,
                             QMessageBox, QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    import sys
    import os
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class EraseThread(QThread):
    """Thread for handling flash erase operations"""
    progress_updated = pyqtSignal(int)
    operation_finished = pyqtSignal(bool, str)
    
    def __init__(self, com_port):
        super().__init__()
        self.com_port = com_port
        
    def run(self):
        try:
            # Simulate progress while running esptool
            cmd = [
                sys.executable, "-m", "esptool",
                "--chip", "esp32",
                "--port", self.com_port,
                "--baud", "921600",
                "erase_flash"
            ]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Simulate progress
            for i in range(0, 101, 5):
                self.progress_updated.emit(i)
                time.sleep(0.1)
                
                # Check if process is still running
                if process.poll() is not None:
                    break
            
            # Wait for process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.progress_updated.emit(100)
                self.operation_finished.emit(True, "Flash erased successfully!")
            else:
                self.operation_finished.emit(False, f"Erase failed: {stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Error: {str(e)}")


class FlashThread(QThread):
    """Thread for handling firmware flashing operations"""
    operation_finished = pyqtSignal(bool, str)
    
    def __init__(self, com_port):
        super().__init__()
        self.com_port = com_port
        
    def run(self):
        try:
            # Get paths to binary files
            bootloader_path = resource_path("bootloader.bin")
            partition_path = resource_path("partition-table.bin")
            firmware_path = resource_path("LiteWing.bin")
            
            # Check if files exist
            missing_files = []
            for name, path in [("bootloader.bin", bootloader_path), 
                             ("partition-table.bin", partition_path),
                             ("LiteWing.bin", firmware_path)]:
                if not os.path.exists(path):
                    missing_files.append(name)
            
            if missing_files:
                self.operation_finished.emit(False, f"Missing files: {', '.join(missing_files)}")
                return
            
            # Flash firmware
            cmd = [
                sys.executable, "-m", "esptool",
                "--chip", "esp32",
                "--port", self.com_port,
                "--baud", "921600",
                "write_flash",
                "-z",
                "0x1000", bootloader_path,
                "0x8000", partition_path,
                "0x10000", firmware_path
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                self.operation_finished.emit(True, "Firmware flashed successfully!")
            else:
                self.operation_finished.emit(False, f"Flash failed: {process.stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Error: {str(e)}")


class UltrexFlasher(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.erase_thread = None
        self.flash_thread = None
        self.progress_dialog = None
        self.init_ui()
        self.refresh_com_ports()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Ultrex Drones ESP32 Flasher")
        self.setFixedSize(500, 400)
        self.setStyleSheet(self.get_stylesheet())
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        # Title
        title_label = QLabel("Ultrex Drones")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Tagline
        tagline_label = QLabel("Make Drones Work for India")
        tagline_label.setObjectName("tagline")
        tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(tagline_label)
        
        main_layout.addLayout(header_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setObjectName("separator")
        main_layout.addWidget(line)
        
        # COM Port section
        com_layout = QVBoxLayout()
        com_layout.setSpacing(10)
        
        com_label = QLabel("Select ESP32 COM Port:")
        com_label.setObjectName("section_label")
        com_layout.addWidget(com_label)
        
        # COM port controls
        com_controls_layout = QHBoxLayout()
        self.com_combo = QComboBox()
        self.com_combo.setObjectName("com_combo")
        com_controls_layout.addWidget(self.com_combo)
        
        self.refresh_btn = QPushButton("Refresh COM Ports")
        self.refresh_btn.setObjectName("secondary_button")
        self.refresh_btn.clicked.connect(self.refresh_com_ports)
        com_controls_layout.addWidget(self.refresh_btn)
        
        com_layout.addLayout(com_controls_layout)
        main_layout.addLayout(com_layout)
        
        # Action buttons section
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)
        
        self.erase_btn = QPushButton("Erase Flash")
        self.erase_btn.setObjectName("danger_button")
        self.erase_btn.clicked.connect(self.erase_flash)
        buttons_layout.addWidget(self.erase_btn)
        
        self.flash_btn = QPushButton("Flash Firmware")
        self.flash_btn.setObjectName("primary_button")
        self.flash_btn.clicked.connect(self.flash_firmware)
        buttons_layout.addWidget(self.flash_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Spacer
        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Footer section
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(5)
        
        website_label = QLabel("Website: https://www.ultrexdrones.in/")
        website_label.setObjectName("footer")
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(website_label)
        
        email_label = QLabel("Email: contact@ultrexdrones.in")
        email_label.setObjectName("footer")
        email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(email_label)
        
        main_layout.addLayout(footer_layout)
        
    def get_stylesheet(self):
        """Return the application stylesheet"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        #title {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        #tagline {
            font-size: 14px;
            color: #7f8c8d;
            font-style: italic;
            margin-bottom: 10px;
        }
        
        #separator {
            color: #bdc3c7;
            margin: 10px 0;
        }
        
        #section_label {
            font-size: 14px;
            font-weight: bold;
            color: #34495e;
            margin-bottom: 5px;
        }
        
        #com_combo {
            padding: 8px 12px;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            font-size: 14px;
            background-color: white;
            min-height: 20px;
        }
        
        #com_combo:focus {
            border-color: #3498db;
        }
        
        #primary_button {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            min-height: 20px;
        }
        
        #primary_button:hover {
            background-color: #229954;
        }
        
        #primary_button:pressed {
            background-color: #1e8449;
        }
        
        #danger_button {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            min-height: 20px;
        }
        
        #danger_button:hover {
            background-color: #c0392b;
        }
        
        #danger_button:pressed {
            background-color: #a93226;
        }
        
        #secondary_button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            min-height: 20px;
        }
        
        #secondary_button:hover {
            background-color: #2980b9;
        }
        
        #secondary_button:pressed {
            background-color: #21618c;
        }
        
        #footer {
            font-size: 12px;
            color: #7f8c8d;
            margin: 2px 0;
        }
        
        QPushButton:disabled {
            background-color: #95a5a6;
            color: #ecf0f1;
        }
        """
    
    def refresh_com_ports(self):
        """Refresh the list of available ESP32 COM ports"""
        self.com_combo.clear()
        
        # Get all serial ports
        ports = serial.tools.list_ports.comports()
        esp32_ports = []
        
        # Filter for ESP32-compatible ports (CH340, CP210x, FTDI)
        for port in ports:
            description = port.description.upper()
            manufacturer = port.manufacturer.upper() if port.manufacturer else ""
            
            if any(chip in description or chip in manufacturer for chip in 
                   ['CH340', 'CP210', 'FTDI', 'SILICON LABS', 'USB-SERIAL']):
                esp32_ports.append(f"{port.device} - {port.description}")
        
        if esp32_ports:
            self.com_combo.addItems(esp32_ports)
            self.erase_btn.setEnabled(True)
            self.flash_btn.setEnabled(True)
        else:
            self.com_combo.addItem("No ESP32 devices found")
            self.erase_btn.setEnabled(False)
            self.flash_btn.setEnabled(False)
    
    def get_selected_port(self):
        """Get the currently selected COM port"""
        current_text = self.com_combo.currentText()
        if " - " in current_text:
            return current_text.split(" - ")[0]
        return None
    
    def erase_flash(self):
        """Erase the ESP32 flash memory"""
        port = self.get_selected_port()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a valid COM port")
            return
        
        # Create and show progress dialog
        self.progress_dialog = QProgressDialog("Erasing flash...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Erase Flash")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_erase)
        
        # Start erase thread
        self.erase_thread = EraseThread(port)
        self.erase_thread.progress_updated.connect(self.progress_dialog.setValue)
        self.erase_thread.operation_finished.connect(self.erase_finished)
        self.erase_thread.start()
        
        # Disable buttons during operation
        self.erase_btn.setEnabled(False)
        self.flash_btn.setEnabled(False)
        
        self.progress_dialog.show()
    
    def cancel_erase(self):
        """Cancel the erase operation"""
        if self.erase_thread and self.erase_thread.isRunning():
            self.erase_thread.terminate()
            self.erase_thread.wait()
        
        self.erase_btn.setEnabled(True)
        self.flash_btn.setEnabled(True)
    
    def erase_finished(self, success, message):
        """Handle erase operation completion"""
        if self.progress_dialog:
            self.progress_dialog.close()
        
        # Re-enable buttons
        self.erase_btn.setEnabled(True)
        self.flash_btn.setEnabled(True)
        
        # Show result message
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
    def flash_firmware(self):
        """Flash the firmware to ESP32"""
        port = self.get_selected_port()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a valid COM port")
            return
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Confirm Flash", 
            "This will flash the firmware to your ESP32.\nMake sure your device is connected and in download mode.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start flash thread
        self.flash_thread = FlashThread(port)
        self.flash_thread.operation_finished.connect(self.flash_finished)
        self.flash_thread.start()
        
        # Disable buttons during operation
        self.erase_btn.setEnabled(False)
        self.flash_btn.setEnabled(False)
        
        # Show status message
        QMessageBox.information(self, "Flashing", "Flashing firmware... Please wait.")
    
    def flash_finished(self, success, message):
        """Handle flash operation completion"""
        # Re-enable buttons
        self.erase_btn.setEnabled(True)
        self.flash_btn.setEnabled(True)
        
        # Show result message
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Ultrex Drones ESP32 Flasher")
    app.setApplicationVersion("1.0.0")
    
    # Set application icon if available
    try:
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except:
        pass
    
    window = UltrexFlasher()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()