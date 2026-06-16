# -*- coding: utf-8 -*-
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORM_DIR = ROOT / "ui" / "forms"
GENERATED_DIR = ROOT / "ui" / "generated"


def main():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    for form_path in sorted(FORM_DIR.glob("*.ui")):
        output_path = GENERATED_DIR / f"{form_path.stem}_ui.py"
        form_arg = form_path.relative_to(ROOT).as_posix()
        output_arg = output_path.relative_to(ROOT).as_posix()
        subprocess.run(
            ["pyuic5", form_arg, "-o", output_arg],
            check=True,
            cwd=ROOT,
        )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
