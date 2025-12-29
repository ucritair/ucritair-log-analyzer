from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    data_sep = os.pathsep
    resources = f"{ROOT / 'app' / 'resources'}{data_sep}app/resources"
    docs = f"{ROOT / 'docs'}{data_sep}docs"
    icon_dir = ROOT / "app" / "resources" / "icons"
    if sys.platform == "darwin":
        icon_path = icon_dir / "ucritter.icns"
    elif sys.platform.startswith("win"):
        icon_path = icon_dir / "ucritter.ico"
    else:
        icon_path = icon_dir / "ucritter.png"
    subprocess.run([
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "ucritter-log-analyzer",
        "--icon",
        str(icon_path),
        "--add-data",
        resources,
        "--add-data",
        docs,
        "app/main.py",
    ], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
