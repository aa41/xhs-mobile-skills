"""让 tests/ 能 import skills/xhs-mobile/scripts 下的模块。"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "xhs-mobile" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
