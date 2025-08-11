# mLRS Parameter Control GUI (Tkinter)

A classic-look Tkinter GUI to control mLRS Tx/Rx parameters over a serial connection.

## Features
- TX and RX tabs using `ttk.Notebook`
- Parameter list with labels and dropdowns/entries
- Per-tab buttons: Refresh Params (pl;), Write Params (p name=value;), Load Params (pstore;)
- Version box shows firmware/device version after `v;`
- Serial controls at top; device output log at bottom

## Requirements
- Python 3.9+
- Tkinter (usually included with Python)
- pyserial

## Setup
```bash
python -m pip install -r requirements.txt
```

## Run
```bash
python mlrs_gui.py
```

Select the serial port and baudrate, connect, and use the tab controls to refresh/write/load parameters.