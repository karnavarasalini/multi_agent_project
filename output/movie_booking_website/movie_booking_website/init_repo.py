import os
import sys
import subprocess

def create_readme():
    """Create a basic README.md at the project root if it doesn't exist."""
    readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")
    readme_path = os.path.abspath(readme_path)
    if not os.path.exists(readme_path):
        content = """# Movie Booking Website

A Flask based web application for booking movies.
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created README at {readme_path}")
    else:
        print(f"README already exists at {readme_path}")

def create_virtualenv():
    """Create a virtual environment in the project root named .venv if missing."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    venv_path = os.path.join(project_root, ".venv")
    if not os.path.isdir(venv_path):
        subprocess.check_call([sys.executable, "-m", "venv", venv_path])
        print(f"Virtual environment created at {venv_path}")
    else:
        print(f"Virtual environment already exists at {venv_path}")

def init_git():
    """Initialize a git repository in the project root if not already a repo."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    git_dir = os.path.join(project_root, ".git")
    if not os.path.isdir(git_dir):
        subprocess.check_call(["git", "init"], cwd=project_root)
        print(f"Initialized git repository in {project_root}")
    else:
        print(f"Git repository already initialized in {project_root}")

def main():
    create_readme()
    create_virtualenv()
    init_git()
    print("Repository initialization complete.")

if __name__ == "__main__":
    main()