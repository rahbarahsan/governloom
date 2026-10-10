"""From a fresh checkout: python scripts/quickstart.py (Python 3.13+, Node 22+)."""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--venv", type=Path, default=Path(".venv"))
    parser.add_argument("--skip-install", action="store_true", help="Use an already prepared development environment")
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if sys.version_info < (3, 13):
        raise SystemExit("The pinned actual-model quickstart needs Python 3.13+. The collector/SDK supports Python 3.11+.")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Install Node 22+ (including npm), then run this command again.")
    directory = (root / (options.directory or Path("data") / ("quickstart-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)))).resolve()
    if not directory.is_relative_to(root / "data") or directory == root / "data" or directory.exists():
        raise SystemExit("Choose a fresh directory beneath data/.")
    environment_path = (root / options.venv).resolve()
    if not environment_path.is_relative_to(root):
        raise SystemExit("Keep the quickstart environment inside this checkout.")
    python = environment_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    def execute(command, cwd=root):
        subprocess.run([str(item) for item in command], cwd=cwd, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    started = time.perf_counter()
    if not python.exists():
        execute([sys.executable, "-m", "venv", environment_path])
    if not options.skip_install:
        execute([python, "-m", "pip", "install", "-r", "requirements.lock", "-r", "examples/requirements.txt"])
        execute([python, "-m", "pip", "install", "--no-deps", "-e", "."])
        execute([npm, "ci"], root / "web")
    execute([npm, "run", "build"], root / "web")
    setup_seconds = round(time.perf_counter() - started, 3)
    command = [python, "-m", "examples.quickstart", "--directory", directory]
    if options.check:
        command.append("--check")
    stop_file = directory / "stop-requested"
    child = subprocess.Popen([str(item) for item in command], cwd=root,
        env={**os.environ, "GOVERNLOOM_QUICKSTART_STOP_FILE": str(stop_file)},
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        result = child.wait()
    except KeyboardInterrupt:
        # Windowless Windows children do not receive the parent's Ctrl+C. Ask the
        # owner to exit through its cleanup path rather than killing its parent.
        print("Stopping the quickstart's owned services...", flush=True)
        # Let the owner create its fresh directory. Creating it here can race its
        # exclusive admission if Ctrl+C arrives immediately after Popen.
        while child.poll() is None and not directory.exists():
            try:
                time.sleep(.1)
            except KeyboardInterrupt:
                continue
        if directory.exists():
            stop_file.touch()
        while child.poll() is None:
            try:
                child.wait(timeout=1)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                continue
        result = child.returncode
    if result:
        raise SystemExit(result)
    if (directory / "report.json").exists():
        report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        report["setup_seconds"] = setup_seconds
        report["setup_to_first_incident_seconds"] = round(setup_seconds + report.get("first_incident_seconds", 0), 3)
        (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
