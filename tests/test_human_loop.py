"""Run the optional standalone Human Loop example in the normal CI suite."""
import importlib.util
from pathlib import Path
import sys

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "human-loop"
spec = importlib.util.spec_from_file_location("_human_loop_example_tests", EXAMPLE / "test_human_loop.py")
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(EXAMPLE))
try:
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)

HumanLoopTests = module.HumanLoopTests
