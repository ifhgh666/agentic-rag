"""Start the local Wenmai workspace from a checkout."""

import hashlib
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def prepare_config() -> bool:
    env_file = BACKEND / ".env"
    if env_file.is_file():
        return True
    template = (BACKEND / ".env.example").read_bytes()
    try:
        with env_file.open("xb") as target:
            target.write(template)
    except FileExistsError:
        if env_file.is_file():
            return True
        raise
    print("Created backend/.env. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL, then run python start.py again.")
    return False


def install_dependencies(marker: Path, inputs: tuple[Path, ...], command: list[str], cwd: Path) -> None:
    fingerprint = hashlib.sha256(b"\0".join(path.read_bytes() for path in inputs)).hexdigest()
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == fingerprint:
        return
    subprocess.run(command, cwd=cwd, check=True)
    marker.write_text(fingerprint + "\n", encoding="utf-8")


def wait_until_ready(process: subprocess.Popen, url: str, timeout: float) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Timed out waiting for {url}")
        time.sleep(0.25)
    raise RuntimeError(f"Service exited with code {process.returncode} before {url} was ready.")


def stop_services(processes: list[subprocess.Popen]) -> None:
    for process in reversed(processes):
        if process.stdin is not None:
            process.stdin.close()
        elif process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    processes: list[subprocess.Popen] = []
    try:
        if not prepare_config():
            return 1
        if sys.version_info < (3, 11):
            raise RuntimeError("Python 3.11 or newer is required.")
        node = shutil.which("node")
        npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
        if not node or not npm:
            raise RuntimeError("Install Node.js 22 or newer, including npm.")
        node_version = subprocess.check_output([node, "--version"], text=True).strip()
        if int(node_version.lstrip("v").split(".", 1)[0]) < 22:
            raise RuntimeError("Node.js 22 or newer is required.")
        for port in (BACKEND_PORT, FRONTEND_PORT):
            with socket.socket() as listener:
                try:
                    listener.bind((HOST, port))
                except OSError as exc:
                    raise RuntimeError(f"{HOST}:{port} is in use or unavailable.") from exc

        venv = BACKEND / ".venv"
        backend_env = os.environ.copy()
        if sys.platform == "win32" and (Path(sys.prefix) / "conda-meta").is_dir():
            # Keep Conda's working native DLL search path while isolating pip installs.
            python = Path(sys.executable)
            packages = venv / "packages"
            packages.mkdir(parents=True, exist_ok=True)
            backend_env["PYTHONPATH"] = os.pathsep.join(
                filter(None, (str(packages), backend_env.get("PYTHONPATH")))
            )
            pip_args = ["--upgrade", "--target", str(packages)]
            backend_marker = packages / ".wenmai-requirements"
        else:
            python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            if not python.is_file():
                subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            pip_args = []
            backend_marker = venv / ".wenmai-requirements"
        install_dependencies(
            backend_marker,
            (BACKEND / "requirements.txt",),
            [str(python), "-m", "pip", "install", *pip_args, "-r", "requirements.txt"],
            BACKEND,
        )
        node_modules = FRONTEND / "node_modules"
        vite = node_modules / "vite/bin/vite.js"
        marker = node_modules / ".wenmai-lock"
        if not vite.is_file():
            marker.unlink(missing_ok=True)
        install_dependencies(
            marker,
            (FRONTEND / "package.json", FRONTEND / "package-lock.json"),
            [npm, "ci"],
            FRONTEND,
        )

        child_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        backend = subprocess.Popen(
            [str(python), "-u", "-m", "scripts.start_local", "--parent-pipe"],
            cwd=BACKEND,
            stdin=subprocess.PIPE,
            env=backend_env,
            creationflags=child_flags,
        )
        processes.append(backend)
        wait_until_ready(backend, f"http://{HOST}:{BACKEND_PORT}/api/health", timeout=600)
        frontend = subprocess.Popen(
            [node, str(vite), "--host", HOST, "--port", str(FRONTEND_PORT), "--strictPort"],
            cwd=FRONTEND,
            creationflags=child_flags,
        )
        processes.append(frontend)
        url = f"http://{HOST}:{FRONTEND_PORT}"
        wait_until_ready(frontend, f"{url}/api/health", timeout=30)
        print(f"Open {url}/ and sign in with admin / 123456. Press Ctrl+C to stop.", flush=True)

        while all(process.poll() is None for process in processes):
            time.sleep(0.25)
        raise RuntimeError("A workspace service stopped.")
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        stop_services(processes)


if __name__ == "__main__":
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    raise SystemExit(main())
