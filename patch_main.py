import re

with open('argus-cli/argus_cli/main.py', 'r') as f:
    content = f.read()

helpers_code = """
import socket

def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def _spawn_backend_if_needed(project_root: pathlib.Path) -> str:
    port = 8000
    if _is_port_in_use(port):
        return f"http://localhost:{port}"
    
    port = 8090
    print(f"Spawning backend on port {port}...")
    
    # We assume backend is in the same repo as argus-cli for this hackathon
    repo_root = project_root.parent if project_root.name == "demo-project" else project_root
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    log_file = open(repo_root / "backend.log", "a")
    
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--port", str(port)],
        cwd=str(repo_root),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    
    # Wait a bit for it to start
    time.sleep(2)
    return f"http://localhost:{port}"
"""

content = content.replace("def _load_dotenv(path: pathlib.Path) -> None:", helpers_code + "\ndef _load_dotenv(path: pathlib.Path) -> None:")

start_code_old = """    # Initial detection
    print("Detecting tools...")"""

start_code_new = """    # Spawn backend if needed
    if backend == "http://localhost:8000":
        backend = _spawn_backend_if_needed(project_root)
        print(f"   Using Backend : {backend}")

    # Initial detection
    print("Detecting tools...")"""

content = content.replace(start_code_old, start_code_new)

with open('argus-cli/argus_cli/main.py', 'w') as f:
    f.write(content)
