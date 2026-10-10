import os
import sys
import winreg
from pathlib import Path

def setup_permanent_autostart():
    project_dir = Path(__file__).resolve().parent
    script_path = project_dir / "whisper_flow.py"
    
    # 1. Locate pythonw in the current active python environment
    venv_dir = Path(sys.executable).parent
    pythonw_candidate = venv_dir / "pythonw.exe"
    python_exe = pythonw_candidate if pythonw_candidate.exists() else Path(sys.executable)
    
    # 2. Write dynamic run_pill.vbs with local absolute paths
    vbs_path = project_dir / "run_pill.vbs"
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{python_exe}"" ""{script_path}""", 0, False
'''
    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"Generated launcher script: {vbs_path}")

    # 3. Add to Windows Current User Startup Registry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)
    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    command_str = f'wscript.exe "{vbs_path}"'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "WhistleFlow", 0, winreg.REG_SZ, command_str)
        print("Registered in Windows Registry: HKCU\\...\\Run\\WhistleFlow")
    except Exception as e:
        print(f"Registry registration error: {e}")

    # 4. Also copy runner to Windows Startup folder as robust fallback
    appdata = os.environ.get("APPDATA")
    if appdata:
        startup_folder = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup_folder.exists():
            dest = startup_folder / "Whistle_Flow.vbs"
            dest.write_text(vbs_content, encoding="utf-8")
            print(f"Installed to Windows Startup folder: {dest}")

    print("\n[SUCCESS] Whistle Flow is permanently configured!")
    print("Whistle Flow will now start automatically in the background on every Windows boot.")
    print("Hotkey: Ctrl + Space (Hold to talk, or tap to lock handsfree).")

if __name__ == "__main__":
    setup_permanent_autostart()
