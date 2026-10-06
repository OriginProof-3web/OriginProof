"""A reexecutes frozen D QA against C #38; never represents D acceptance."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
C_SHA = "3ef1fd40943914c1450e8bc05047119ab7eabbc0"
D_SHA = "a3f55c6991061ac445d2223f19ff1b2a48acab0e"

if __name__ == "__main__":
    if os.getenv("W5_D_API_QA") != "1":
        raise SystemExit("W5_D_API_QA=1 required for disposable synthetic resources.")
    work = Path(os.getenv("W5_ADMIN_OUTPUT_DIR", str(ROOT / "build" / "w5-api"))) / uuid4().hex
    work.mkdir(parents=True, mode=0o700)
    blob = subprocess.check_output(["git", "archive", D_SHA], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
        archive.extractall(work, filter="data")
    (work / "uv.lock").write_bytes(subprocess.check_output(["git", "show", f"{C_SHA}:uv.lock"], cwd=ROOT))
    source = work / "fixtures/finals/w5_p0_api_qa.py"
    spec = importlib.util.spec_from_file_location("d_w5_reexecution", source)
    qa = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = qa
    spec.loader.exec_module(qa)
    original = qa.command
    def command(args, cwd=work, timeout=240):
        return original(args, cwd=ROOT if args[0] == "git" else cwd, timeout=timeout)
    qa.command = command
    qa.PRODUCT_SHA = C_SHA
    qa.DEPLOYER = "originproof-w5-a-admin-deployer:3ef1fd4"
    raise SystemExit(qa.main())
