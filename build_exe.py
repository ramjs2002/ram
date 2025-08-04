#!/usr/bin/env python3
"""
Build script for Ultrex Drones ESP32 Flasher
This script creates a standalone executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil

def check_requirements():
    """Check if all required files and dependencies are present"""
    print("🔍 Checking requirements...")
    
    # Check for Python files
    if not os.path.exists("ultrex_flasher.py"):
        print("❌ Error: ultrex_flasher.py not found!")
        return False
    
    # Check for binary files
    binary_files = ["bootloader.bin", "partition-table.bin", "LiteWing.bin"]
    missing_binaries = []
    
    for binary in binary_files:
        if not os.path.exists(binary):
            missing_binaries.append(binary)
    
    if missing_binaries:
        print(f"⚠️  Warning: Missing binary files: {', '.join(missing_binaries)}")
        print("   The executable will be created but may not work without these files.")
    else:
        print("✅ All binary files found")
    
    # Check for PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller is installed")
    except ImportError:
        print("❌ Error: PyInstaller not found!")
        print("   Install it with: pip install pyinstaller")
        return False
    
    return True

def build_executable():
    """Build the executable using PyInstaller"""
    print("\n🔨 Building executable...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("🧹 Cleaned build directory")
    
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("🧹 Cleaned dist directory")
    
    # Build command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "UltrexDronesFlasher",
        "--icon", "icon.ico" if os.path.exists("icon.ico") else "",
    ]
    
    # Add binary files if they exist
    binary_files = ["bootloader.bin", "partition-table.bin", "LiteWing.bin"]
    for binary in binary_files:
        if os.path.exists(binary):
            if sys.platform.startswith('win'):
                cmd.extend(["--add-data", f"{binary};."])
            else:
                cmd.extend(["--add-data", f"{binary}:."])
    
    cmd.append("ultrex_flasher.py")
    
    # Remove empty icon parameter if no icon file
    cmd = [arg for arg in cmd if arg != ""]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main build function"""
    print("🚀 Ultrex Drones ESP32 Flasher - Build Script")
    print("=" * 50)
    
    if not check_requirements():
        print("\n❌ Build aborted due to missing requirements")
        sys.exit(1)
    
    if build_executable():
        print("\n🎉 Build completed successfully!")
        print(f"📁 Executable location: {os.path.abspath('dist')}")
        
        # List created files
        if os.path.exists("dist"):
            files = os.listdir("dist")
            for file in files:
                size = os.path.getsize(os.path.join("dist", file))
                print(f"   📄 {file} ({size / 1024 / 1024:.1f} MB)")
        
        print("\n📋 Next steps:")
        print("   1. Test the executable in the dist/ folder")
        print("   2. Copy your .bin files to the same directory as the .exe")
        print("   3. Distribute the executable to users")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()