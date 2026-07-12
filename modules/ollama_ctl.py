import subprocess

def _run(action):
    try:
        result = subprocess.run(
            ["sudo", "systemctl", action, "ollama"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return True
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out")

def start_ollama():
    return _run("start")

def stop_ollama():
    return _run("stop")

def restart_ollama():
    return _run("restart")