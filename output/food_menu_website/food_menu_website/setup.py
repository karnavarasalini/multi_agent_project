import os
import subprocess
import sys
from pathlib import Path


def create_virtualenv(project_root: Path) -> None:
    venv_path = project_root / 'venv'
    if not venv_path.exists():
        print('Creating virtual environment...')
        subprocess.check_call([sys.executable, '-m', 'venv', str(venv_path)])
    else:
        print('Virtual environment already exists.')


def initialize_git(project_root: Path) -> None:
    git_dir = project_root / '.git'
    if not git_dir.exists():
        print('Initializing git repository...')
        subprocess.check_call(['git', 'init'], cwd=str(project_root))
    else:
        print('Git repository already initialized.')


def write_gitignore(project_root: Path) -> None:
    gitignore_path = project_root / '.gitignore'
    if gitignore_path.exists():
        print('.gitignore already exists.')
        return
    print('Writing .gitignore file...')
    content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# VS Code settings
.vscode/

# macOS
.DS_Store
"""
    gitignore_path.write_text(content)


def write_requirements(project_root: Path) -> None:
    req_path = project_root / 'requirements.txt'
    if req_path.exists():
        print('requirements.txt already exists.')
        return
    print('Creating requirements.txt...')
    content = """Flask>=2.2
Flask-Login>=0.6
Flask-Babel>=2.0
WTForms>=3.0
"""
    req_path.write_text(content)


def main() -> None:
    # Assume this script lives in <project_root>/food_menu_website/setup.py
    project_root = Path(__file__).resolve().parent.parent
    create_virtualenv(project_root)
    initialize_git(project_root)
    write_gitignore(project_root)
    write_requirements(project_root)
    print('Setup complete. Activate the virtual environment with:
source venv/bin/activate (Linux/macOS) or venv\\Scripts\\activate (Windows)')


if __name__ == '__main__':
    main()
