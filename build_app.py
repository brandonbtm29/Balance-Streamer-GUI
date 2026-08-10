import sys
import subprocess
import os

def ensure_requirements():
    print("Ensuring dependencies are installed...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        sys.exit(1)

def build():
    print("Building executable for Balance Streamer GUI...")
    
    cmd = [
        "pyinstaller",
        "-y",
        "--noconsole",
        "--onedir", # Large scipy/matplotlib apps run faster in onedir mode, less temp unpacking
        "--name", "Balance_Streamer",
        "--exclude-module", "PySide6",
        "--exclude-module", "PyQt5",
        "multi_balance_stream.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        
        print("\n=============================================")
        print("BUILD COMPLETE!")
        if sys.platform == "darwin":
            print("Your application bundle is located in the 'dist/Balance_Streamer' folder.")
        else:
            print("Your executable is located in the 'dist\\Balance_Streamer' folder: dist\\Balance_Streamer\\Balance_Streamer.exe")
            print("You can right-click this to create a shortcut for your Desktop or Taskbar.")
        print("=============================================\n")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ensure_requirements()
    print("Running PyInstaller...")
    build()
