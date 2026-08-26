import os

from models.schemas import DeveloperOutput


# Map: an import string found in generated Python source -> the pip package
# name to add to requirements.txt if that import is present but the package isn't listed.
DEPENDENCY_RULES = [
    ("import flask", "flask"),
    ("from flask", "flask"),
    ("import requests", "requests"),
    ("import pytest", "pytest"),
    ("import fastapi", "fastapi"),
    ("from fastapi", "fastapi"),
    ("import uvicorn", "uvicorn"),
    ("import pandas", "pandas"),
    ("import numpy", "numpy"),
    ("import PyQt5", "PyQt5"),
    ("import PIL", "Pillow"),
    ("from PIL", "Pillow"),
]

# Stdlib modules that look like third-party imports but aren't -- never add these.
STDLIB_SAFE = {"tkinter", "unittest", "json", "os", "re", "sys", "argparse", "math", "sqlite3"}


def write_project_files(developer_output: DeveloperOutput, project_name: str, base_dir: str = "output") -> str:
    safe_name = project_name.lower().replace(" ", "_")
    project_root = os.path.join(base_dir, safe_name)

    for file in developer_output.files:
        full_path = os.path.join(project_root, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file.content)

    ensure_dependencies(project_root, developer_output)
    ensure_init_files(project_root, developer_output)

    return project_root


def ensure_dependencies(project_root: str, developer_output: DeveloperOutput) -> None:
    """
    Scan all generated Python source for imports that need a pip package,
    and write/update requirements.txt with anything missing.
    """
    all_py_source = "\n".join(
        f.content for f in developer_output.files if f.path.endswith(".py")
    )

    req_path = os.path.join(project_root, "requirements.txt")
    existing = set()
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            existing = {line.strip().split("==")[0].lower() for line in f if line.strip()}

    needed = set()
    for marker, package in DEPENDENCY_RULES:
        if marker in all_py_source and package.lower() not in existing:
            needed.add(package)

    if not needed:
        return

    with open(req_path, "a", encoding="utf-8") as f:
        for package in sorted(needed):
            f.write(package + "\n")

    print(f"  -> Auto-added {len(needed)} missing dependenc{'y' if len(needed) == 1 else 'ies'} to requirements.txt")


def ensure_init_files(project_root: str, developer_output: DeveloperOutput) -> None:
    """
    Any directory (besides 'tests') that contains a generated .py file needs an
    __init__.py so it's importable as a package.
    """
    package_dirs = set()
    for f in developer_output.files:
        if f.path.endswith(".py"):
            dir_path = os.path.dirname(f.path)
            if dir_path and not dir_path.startswith("tests"):
                package_dirs.add(dir_path)

    for dir_path in package_dirs:
        full_dir = os.path.join(project_root, dir_path)
        init_path = os.path.join(full_dir, "__init__.py")
        if not os.path.exists(init_path):
            os.makedirs(full_dir, exist_ok=True)
            open(init_path, "w").close()