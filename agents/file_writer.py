import os

from models.schemas import DeveloperOutput


def write_project_files(developer_output: DeveloperOutput, project_name: str, base_dir: str = "output") -> str:
    safe_name = project_name.lower().replace(" ", "_")
    project_root = os.path.join(base_dir, safe_name)

    for file in developer_output.files:
        full_path = os.path.join(project_root, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file.content)

    check_stack_integrity(project_root, developer_output)

    return project_root


def check_stack_integrity(project_root: str, developer_output: DeveloperOutput) -> None:
    """
    This project's output must always be Java/Spring Boot. Warn loudly (rather than
    silently reporting success) if the generated files don't look like a valid Maven /
    Spring Boot project, or if any Python files slipped through.
    """
    paths = [f.path for f in developer_output.files]

    has_pom = any(p.endswith("pom.xml") for p in paths)
    has_java = any(p.endswith(".java") for p in paths)
    python_files = [p for p in paths if p.endswith(".py")]

    if python_files:
        print(f"  !! STACK WARNING: {len(python_files)} Python file(s) were written into a "
              f"Java/Spring Boot project: {python_files}. This should not happen -- check "
              f"the Planner/Developer prompts for stack drift.")

    if not has_pom:
        print(f"  !! STACK WARNING: no pom.xml found in '{project_root}'. This project "
              f"will not build with Maven.")

    if not has_java:
        print(f"  !! STACK WARNING: no .java files found in '{project_root}'. This is not "
              f"a valid Spring Boot output.")