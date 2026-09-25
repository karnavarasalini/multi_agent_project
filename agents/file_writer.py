import os
import re

from models.schemas import DeveloperOutput


def _normalize_path(path: str) -> str:
    """Collapses any path style a GeneratedFile might arrive with -- relative,
    Windows-absolute, or a Unix-style absolute path that os.path.join still treats
    as rooted on Windows -- down to one canonical project-relative key. Without
    this, two entries that are really the same file (one relative, one absolute)
    both resolve to the identical real path on disk via os.path.join's "rooted
    path discards previous components" behavior, and whichever is written LAST
    silently wins -- even if it's empty or a different, conflicting version."""
    p = path.replace("\\", "/")
    p = re.sub(r"^/?[A-Za-z]:/", "", p)  # strip a leading drive prefix if present

    src_marker = re.search(r"(src/(?:main|test)/.+)$", p)
    if src_marker:
        return src_marker.group(1)

    return p.lstrip("/")


def _dedupe_files(files: list) -> list[tuple[str, object]]:
    """Groups GeneratedFile entries by normalized path and keeps exactly one per
    key: prefer a non-empty entry; if multiple non-empty entries collide (a real
    conflicting duplicate, not just a path-format duplicate), keep the last one
    but warn loudly instead of silently picking a winner."""
    by_key: dict[str, list] = {}
    for gf in files:
        key = _normalize_path(gf.path)
        by_key.setdefault(key, []).append(gf)

    deduped = []
    for key, entries in by_key.items():
        if len(entries) == 1:
            deduped.append((key, entries[0]))
            continue

        non_empty = [e for e in entries if (e.content or "").strip()]

        if not non_empty:
            print(f"  !! FILE_WRITER WARNING: all {len(entries)} generated entries for "
                  f"'{key}' are empty -- writing an empty file. This file will fail to "
                  f"do anything useful even though it will compile.")
            deduped.append((key, entries[-1]))
            continue

        if len(non_empty) > 1:
            print(f"  !! FILE_WRITER WARNING: {len(non_empty)} conflicting non-empty "
                  f"generated entries for '{key}' -- keeping the last one. This means "
                  f"the Developer Agent generated the same file more than once with "
                  f"different content; check its prompt/parsing for duplicate emission.")
        elif len(entries) > 1:
            print(f"  [file_writer] Deduplicated '{key}': {len(entries)} entries "
                  f"resolved to the same file, kept the non-empty one.")

        deduped.append((key, non_empty[-1]))

    return deduped


def write_project_files(developer_output: DeveloperOutput, project_name: str, base_dir: str = "output") -> str:
    safe_name = project_name.lower().replace(" ", "_")
    project_root = os.path.join(base_dir, safe_name)

    deduped = _dedupe_files(developer_output.files)

    for key, gf in deduped:
        full_path = os.path.join(project_root, key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(gf.content or "")

    # Normalize developer_output.files in place too, so every downstream consumer
    # (TesterAgent's empty-file scan, DebuggerAgent's duplicate-lookup helpers,
    # _gather_related_files, etc.) sees exactly one canonical entry per file
    # instead of the raw duplicates the Developer Agent produced.
    developer_output.files = [
        type(gf)(path=key, content=gf.content) for key, gf in deduped
    ]

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