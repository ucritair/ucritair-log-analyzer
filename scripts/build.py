from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    data_sep = os.pathsep
    resources = f"{ROOT / 'app' / 'resources'}{data_sep}app/resources"
    docs = f"{ROOT / 'docs'}{data_sep}docs"
    subprocess.run([
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "mcritair-log-analyzer",
        "--add-data",
        resources,
        "--add-data",
        docs,
        "app/main.py",
    ], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
