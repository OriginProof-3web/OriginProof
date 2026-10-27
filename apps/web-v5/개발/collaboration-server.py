import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_SOURCE = Path("/Users/khj/Desktop/해커톤/OriginProof-w5-a-completion/apps/web")
os.environ["ORIGINPROOF_CONSOLE_ROOT"] = str(ROOT.parent / "페이지")  # 5안: 화면 파일은 ../페이지
os.environ["ORIGINPROOF_WEB_SOURCE"] = str(WEB_SOURCE)
runpy.run_path(str(WEB_SOURCE / "test/local-console-server.py"), run_name="__main__")
