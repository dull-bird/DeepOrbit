from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path


def open_note(path: Path | str, *, execute: bool = True) -> dict[str, str]:
    note = Path(path).expanduser().resolve()
    cli = shutil.which("obsidian")
    if cli:
        command = [cli, "open", f"path={note}"]
        if execute:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"method": "cli", "target": str(note)}
    uri = "obsidian://open?path=" + urllib.parse.quote(str(note), safe="")
    if execute and webbrowser.open(uri):
        return {"method": "uri", "target": uri}
    return {"method": "path", "target": str(note), "platform": sys.platform}
