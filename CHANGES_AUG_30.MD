# Changes — August 30, 2026

Session goal: understand the project and get it running. It could not run at all at the
start. It now completes end to end and produces Spring Boot projects that compile with
passing tests.

**Headline result:** pipeline went from `Status: failed` (3 debug iterations exhausted, no
tests ever generated) to `Status: success` in **1 debug iteration**, verified with an
independent `mvn clean test` giving `BUILD SUCCESS`.

---

## 1. What the project is

An LLM-driven multi-agent pipeline that turns a plain-English requirement into a complete
Java Spring Boot (Maven) project, then compiles it and self-repairs the errors.

`main.py` runs six stages over one shared `ProjectState`:

| Stage | File | Job |
| --- | --- | --- |
| Requirement | `agents/requirement_agent.py` | Requirement text → structured reqs, assumptions, clarification questions |
| Planner | `agents/planner_agent.py` | → modules, JPA entities, REST endpoints, ordered tasks |
| Developer | `agents/developer_agent.py` | One LLM call per task, each returning one `{path, content}` file |
| Writer | `agents/file_writer.py` | Writes to `output/<slug>/`, warns on stack drift |
| Tester | `agents/tester_agent.py` | `mvn compile`, then `mvn test`; parses javac/surefire output |
| Debugger | `agents/debugger_agent.py` | Parses errors, creates missing classes, LLM-patches files, loops up to 3× |

Supporting pieces: `rag/knowledge_base.py` embeds 7 hardcoded Spring Boot patterns with
`sentence-transformers` + FAISS and injects the best match into each developer prompt. The
LLM is **Groq** (`openai/gpt-oss-120b`) accessed through the OpenAI SDK with a swapped
`base_url`, keyed by `GROQ_API_KEY`.

---

## 2. Code fixes

### 2.1 `agents/tester_agent.py` — TesterAgent never actually ran Maven

The single highest-impact bug. `_run()` was:

```python
from sympy import true          # sympy's `true` object
...
subprocess.run(args, ..., shell=true)
```

On POSIX, `shell=True` with a **list** executes only `mvn` and discards every flag and
goal. Confirmed directly: every `test()` returned

```
[ERROR] No goals have been specified for this build.
```

So the tester reported a **permanent phantom failure** regardless of the code's real
state, and then fed that meaningless output to the DebuggerAgent, which burned LLM calls
on a compile error that did not exist.

**Fix:** removed the `sympy` import and the `shell=true` argument. The TesterAgent now
genuinely compiles and parses real per-file, per-line javac errors.

### 2.2 `agents/developer_agent.py` — test tasks were silently discarded

```python
SKIP_KEYWORDS = ["unit test", "integration test", "write test"]
```

`"Write JUnit tests".lower()` contains the substring `"unit test"` (inside *JUnit*), so
the planner's mandatory final test task was dropped on **every** run. Consequences: no
test file was ever generated, `mvn test` had nothing to execute, the TesterAgent always
took its `No tests found -- compile check passed` branch and returned `passed=True`
without running anything, and its entire surefire-parsing path was dead code.

**Fix:** replaced with genuine non-code chores:

```python
SKIP_KEYWORDS = ["documentation", "readme", "deploy", "ci/cd", "pipeline setup"]
```

### 2.3 `agents/debugger_agent.py` — debugger could not fix cross-file errors

This was the reason the pipeline failed even once the tester worked.

`fix_file()` sent the LLM **only the one file's content plus the raw error text** — no
project plan, no sight of the files that reference it. Two failure modes compounded:

**It patched where the error was *reported*, not where it was *caused*.** A real example
from the failing run: `BookRepository` was generated as

```java
public interface BookRepository extends JpaRepository<Object, Long> {   // should be <Book, Long>
```

which makes `findAll()` return `List<Object>`. javac blames the **service**, so the
debugger rewrote `BookService` over and over while the actual defect sat in
`BookRepository`, which had no error of its own and was never correctly touched. When it
did reach the repository, it saw `List<Object>` in the error text and "helpfully" wrote
`JpaRepository<Object, Long>` to match — propagating the bug instead of fixing it.

**With no plan context it re-invented the schema each pass.** The plan specified
`read: Boolean`; the debugger dropped it and invented `isbn: String`, while `BookService`
still called `getRead()`. Result: identical errors after all 3 iterations.

**Fixes:**

- **`fix_compile_errors_project_wide()` (new, now the primary compile-error strategy).**
  Sends the plan's authoritative entity list, the compiler output, and *all* project
  sources in one call, then applies every file the model says must change — so the repair
  can land in the file at fault. Returns `None` for projects over 14 Java files so the
  per-file path still handles large cases.
- **`_plan_context()` (new).** Injects the plan's entities and exact field types into every
  repair prompt, marked authoritative, which stops the schema drift.
- **`_gather_related_files()` (new).** Gives the per-file fallback the collaborator context
  it never had, reusing the idea already present in `_gather_reference_context()`.
- **`parse_missing_members()` + `MISSING_MEMBER_RE` (new).** Parses javac's
  `symbol: method getRead() / location: ... of type ...Book` blocks and routes the fix to
  the class that should **declare** the member, not the caller that invoked it.
- **`call_llm_json()` (new).** JSON-mode LLM call with the same retry and rate-limit
  contract as `call_llm`, including `RateLimitStop`.
- **`_write_and_register()`, `_read_generated()`, `_repair_double_escaping()`,
  `_class_name_from_path()`, `_find_generated_path_for_class()` (new helpers).**
- **`run_debugger_agent()` rewired.** Compile errors now try project-wide repair first and
  fall back to per-file patching (with missing-member routing) if it is unavailable.
- **`import json`** added.

**Safety note:** paths returned by the model are rejected unless they normalize to inside
`src/` and are neither absolute nor contain `..`, so a bad response cannot write outside
the project tree.

---

## 3. Configuration fixes

### 3.1 `requirements.txt` — rewritten

The old file was **UTF-16 with a BOM and CRLF endings**, which pip cannot parse at all.
Contents were also wrong. Dependencies are now derived from the actual imports:

```
openai==2.9.0
pydantic==2.13.4
python-dotenv==1.2.3
sentence-transformers==5.1.2
faiss-cpu==1.13.0
numpy==2.3.5
```

The original listed 15 entries; only `pydantic` and `python-dotenv` survived unchanged.

| Change | Detail |
| --- | --- |
| Encoding | UTF-16 + BOM + CRLF → UTF-8 / ASCII with LF |
| Removed 2 nonexistent packages | `httpx2==2.12.0` and `httpcore2==2.12.0` are not real PyPI packages |
| Corrected 1 nonexistent version | `openai==3.3.1` does not exist → `openai==2.9.0` |
| Dropped 10 transitive pins | `annotated-types`, `anyio`, `h11`, `idna`, `jiter`, `pydantic_core`, `sniffio`, `truststore`, `typing-inspection`, `typing_extensions` — resolved automatically by `openai`/`pydantic`; hand-pinning them invites conflicts |
| Added 3 missing packages | `sentence-transformers`, `faiss-cpu`, `numpy` — all imported by `rag/knowledge_base.py` but unlisted, so the RAG layer could never work from a clean install |
| Dropped `sympy` | Only needed for the `from sympy import true` bug removed in §2.1 |
| Documented prerequisites | Python 3.10+, and JDK 17 + Maven on PATH — neither is discoverable from the code |

> If you regenerate this file on Windows PowerShell, `>` defaults to UTF-16. Use
> `Out-File -Encoding utf8`. That is almost certainly the original cause.

### 3.2 `.gitignore` — expanded

Went from 5 patterns to full coverage of what the project produces:

- `.venv/` — only `venv/` was listed, so the standard venv name was untracked-unsafe
- `target/`, `*.class` — Maven output. `output/attendance_website/target/` and
  `output/target/` already exist on disk and would have been committed
- `.env.*` with a `!.env.example` negation, so a template can be checked in safely
- `.DS_Store`, `Thumbs.db`, `.idea/`, and the usual Python caches

Generated projects under `output/` remain **tracked** — there are 18 and they look
intentional. Add `output/` if you would rather keep the repo lean.

---

## 4. Environment setup (machine state, not repo changes)

| Item | Detail |
| --- | --- |
| Python | System is **3.9.6**, too old — the agents use PEP 604 `X \| None` annotations, which raise `TypeError` on 3.9. Created `.venv` on **Python 3.12.13** via `uv`. |
| Maven | Was **not installed**. Installed **Apache Maven 3.9.16** to `~/.local/opt/`, SHA-512 verified against Apache's published checksum, symlinked to `~/.local/bin/mvn`. Works with the existing Temurin **JDK 17.0.19**. |
| `GROQ_API_KEY` | Was absent. Supplied by the user in `.env`. Note `main.py` line 11 imports `debugger_agent`, which builds its OpenAI client at **module scope**, so a missing key crashes before any prompt appears. |

---

## 5. Verification

Nothing below is the pipeline's own self-report; each was confirmed with an independent
`mvn clean test`.

### Before vs after

| | Before | After |
| --- | --- | --- |
| Status | `failed` | `success` |
| Debug iterations | 3 (exhausted) | **1** |
| Files generated | 6 | 7 |
| Test files | 0 (task silently skipped) | 1 |
| `mvn` outcome | compile errors persisted unchanged | `BUILD SUCCESS` |

### Runs

| Requirement | Files | Iterations | Independent `mvn clean test` |
| --- | --- | --- | --- |
| Book library REST API | 7 | 1 | `BUILD SUCCESS` — **5 tests**, 0 failures |
| Task tracker (Project → many Tasks) | 12 | 1 | `BUILD SUCCESS` — **1 test**, 0 failures |

Both previously-failing defects are gone: repositories now declare
`JpaRepository<Book, Long>` / `<Project, Long>` / `<Task, Long>`, and the `Book` entity
carries exactly the planned fields (`id, title, author, read: Boolean`) with
`getRead()`/`setRead()` and no trace of the hallucinated `isbn`.

The two-entity run is the stronger evidence — the debugger diagnosed a compound problem in
a single pass: *"TaskController references a non-existent TaskDto and calls service methods
that do not exist, and the project lacks the ResourceNotFoundException"* — then created the
missing exception class and corrected two files together. That is exactly the cross-file
reasoning the old isolated approach could not do.

### Other checks

- **RAG layer:** `test_rag.py` correctly ranked the JWT security pattern top for a
  login/token query.
- **`requirements.txt` completeness:** built a throwaway venv from it alone; every app
  module imported successfully.
- **`.gitignore` correctness:** `git check-ignore` in a scratch repo seeded with real
  project paths — 16 assertions, all passing.

---

## 6. Files changed

| File | Change |
| --- | --- |
| `agents/tester_agent.py` | Removed `sympy` import and `shell=true` |
| `agents/developer_agent.py` | Corrected `SKIP_KEYWORDS` |
| `agents/debugger_agent.py` | Project-wide repair, plan context, related-file context, missing-member routing, path validation |
| `requirements.txt` | Rewritten — UTF-8, accurate pins |
| `.gitignore` | Expanded |
| `CHANGES_AUG_30.MD` | This document |

---

## 7. How to run

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

echo 'GROQ_API_KEY=your_key_here' > .env
export PATH="$HOME/.local/bin:$PATH"      # so the TesterAgent can find mvn

.venv/bin/python main.py
```

Then type a requirement at the prompt. Output lands in `output/<project_slug>/`.

---

## 8. Known issues not addressed

- **Pre-existing output corruption.** `output/attendance_website` does not compile: three
  files were written with literal `\n` sequences instead of newlines
  (`CustomUserDetailsService.java` is one line containing 43 of them). Running the
  project's own `_repair_double_escaping()` fixed all three, leaving 2 genuine syntax
  errors in `ReportController.java:25,28`. **The repair function exists but is not applied
  on the write path**, so the DeveloperAgent can still emit non-compiling files. Suggested
  fix: move the call into `file_writer.py` where it cannot be bypassed.
- **Stack drift in older output.** `output/student_attendance_website/` contains a **Flask**
  app (`flask`, `flask_sqlalchemy`, `reportlab`), despite every prompt insisting on
  Java/Spring Boot. The `check_stack_integrity()` warnings exist but only warn.
- **Absolute paths in the per-file fallback.** Maven reports absolute paths, and
  `fix_file()` matches `gf.path == file_path` against relative paths, so `ProjectState`
  content is not updated on that path. The new project-wide repair avoids this by using
  relative paths, so it is now a fallback-only wart.
- **`resources/pom_template.xml` is unreferenced** by any agent — pom.xml is generated by
  the LLM instead. Either wire it in or delete it.
- **Interactive-only input.** `requirement_input.py` uses `input()`, so the pipeline cannot
  be run non-interactively without piping stdin. A `--requirement` CLI flag would help CI.
