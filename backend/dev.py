from __future__ import annotations

import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _npm() -> str:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required to run the MemoryReef frontend.")
    return npm


def _ensure_frontend_dependencies(frontend_dir: Path, npm: str) -> None:
    if (frontend_dir / "node_modules").exists():
        return

    install_command = [npm, "ci"] if (frontend_dir / "package-lock.json").exists() else [npm, "install"]
    print("Installing frontend dependencies...")
    subprocess.run(install_command, cwd=frontend_dir, check=True)


def _terminate(processes: list[subprocess.Popen[object]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    deadline = time.monotonic() + 5
    for process in processes:
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        if process.poll() is None:
            process.kill()


def run() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    frontend_dir = root_dir / "frontend"
    npm = _npm()

    if "--check" in sys.argv:
        if not frontend_dir.exists():
            raise SystemExit("frontend/ directory is missing.")
        __import__("uvicorn")
        print("MemoryReef dev launcher is ready.")
        return

    _ensure_frontend_dependencies(frontend_dir, npm)

    backend_host = os.getenv("MEMORYREEF_HOST", "127.0.0.1")
    backend_port = os.getenv("MEMORYREEF_PORT", "8000")
    frontend_port = os.getenv("MEMORYREEF_FRONTEND_PORT", "5173")

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--reload",
            "--host",
            backend_host,
            "--port",
            backend_port,
        ],
        cwd=root_dir,
    )
    frontend = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", frontend_port],
        cwd=frontend_dir,
    )
    processes = [backend, frontend]

    def stop_processes(signum: int, _frame: object) -> None:
        _terminate(processes)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, stop_processes)
    signal.signal(signal.SIGTERM, stop_processes)

    print("", flush=True)
    print("MemoryReef is starting:", flush=True)
    print(f"  Frontend: http://127.0.0.1:{frontend_port}", flush=True)
    print(f"  Backend:  http://{backend_host}:{backend_port}", flush=True)
    print("", flush=True)
    print("Press Ctrl+C to stop both servers.", flush=True)

    try:
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    raise SystemExit(exit_code)
            time.sleep(0.5)
    finally:
        _terminate(processes)
