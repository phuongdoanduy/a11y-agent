"""Sidecar FastAPI service for validating local project paths before audit.

Runs on port 8001. Single endpoint: GET /validate?path=<abs_path>
Returns file count and detected platforms so the frontend can show a
confirmation chip before the user starts an expensive LLM audit.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="a11y-path-validator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


_MAX_FILES = 50_000


@app.get("/validate")
def validate_path(path: str) -> dict:
    """Validate a local directory path and detect its platform(s).

    Returns:
        exists: whether the path is a readable directory
        file_count: total number of files (recursive, capped at 50k)
        detected_platforms: subset of ["ios", "android", "web"]
    """
    # resolve() collapses ../ traversal and symlink chains before the existence check
    p = Path(path).resolve()
    if not p.exists() or not p.is_dir():
        return {"exists": False, "file_count": 0, "detected_platforms": []}

    # Exclude symlinks to prevent walking directories outside the project root
    all_files: list[Path] = []
    for f in p.rglob("*"):
        if f.is_file() and not f.is_symlink():
            all_files.append(f)
            if len(all_files) >= _MAX_FILES:
                break

    file_count = len(all_files)
    exts = {f.suffix.lower() for f in all_files}
    names = {f.name for f in all_files}

    platforms: list[str] = []
    if ".swift" in exts or any(n.endswith(".xcodeproj") or n.endswith(".xcworkspace") for n in names):
        platforms.append("ios")
    if ".kt" in exts or ".kts" in exts or "AndroidManifest.xml" in names:
        platforms.append("android")
    if {".tsx", ".jsx", ".html"} & exts:
        platforms.append("web")

    return {"exists": True, "file_count": file_count, "detected_platforms": platforms}
