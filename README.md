# Ultrex Drones ESP32 Flasher

A professional firmware flashing tool for ESP32 microcontrollers with a modern PyQt6 GUI.

## Features

- **Modern GUI**: Clean, professional interface with brand-quality design
- **ESP32 Detection**: Automatically detects ESP32 devices on CH340, CP210x, FTDI, and other USB-serial adapters
- **Flash Erase**: Complete flash memory erase with progress indicator
- **Firmware Flashing**: Automatic flashing of bootloader, partition table, and firmware binaries
- **Thread-Safe Operations**: Non-blocking operations using QThread
- **PyInstaller Ready**: Embedded binary support for standalone executable

## Requirements

- Python 3.8 or higher
- ESP32 development board
- USB cable
- Required firmware files: `bootloader.bin`, `partition-table.bin`, `LiteWing.bin`

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running from Source
```bash
python ultrex_flasher.py
```

### Creating Executable with PyInstaller

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Create executable with embedded binaries:
   ```bash
   pyinstaller --onefile --windowed --add-data "bootloader.bin;." --add-data "partition-table.bin;." --add-data "LiteWing.bin;." ultrex_flasher.py
   ```

3. The executable will be created in the `dist/` directory

## Binary Files

Place the following binary files in the same directory as the script:
- `bootloader.bin` - ESP32 bootloader (flashed at 0x1000)
- `partition-table.bin` - Partition table (flashed at 0x8000)
- `LiteWing.bin` - Main firmware (flashed at 0x10000)

## ESP32 Connection

1. Connect your ESP32 to your computer via USB
2. Put the ESP32 in download mode (hold BOOT button while pressing RESET)
3. Select the correct COM port from the dropdown
4. Use "Erase Flash" to clear existing firmware (optional)
5. Use "Flash Firmware" to upload new firmware

## Supported ESP32 Boards

The application automatically detects ESP32 boards using these USB-to-serial chips:
- CH340/CH341 (NodeMCU, Wemos D1 Mini ESP32, etc.)
- CP210x (ESP32-DevKitC, ESP32-WROVER-KIT, etc.)
- FTDI (custom boards)
- Silicon Labs (some development boards)

## Troubleshooting

### No ESP32 devices found
- Ensure ESP32 is connected via USB
- Install proper USB drivers for your board
- Try a different USB cable or port
- Put ESP32 in download mode

### Flash/Erase operations fail
- Ensure ESP32 is in download mode
- Check COM port selection
- Try lower baud rate (modify code if needed)
- Verify binary files are present and valid

### Application won't start
- Check Python version (3.8+ required)
- Install all dependencies: `pip install -r requirements.txt`
- Ensure PyQt6 is properly installed

## License

This software is provided as-is for use with Ultrex Drones products.

## Contact

- Website: https://www.ultrexdrones.in/
- Email: contact@ultrexdrones.in