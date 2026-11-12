"""
postprocess.py -- deterministic clean-up of a freshly generated Spring Boot project.

No LLM calls. It runs BEFORE Maven (server.py) and again at the start of every debug pass,
and removes whole classes of failures that an LLM keeps getting wrong:

1. Lombok.  Lombok has to match the JDK exactly; on a newer JDK it silently stops generating
   getters/setters/builders and the build dies with hundreds of "cannot find symbol" errors.
   The generated code is rewritten into plain Java (explicit getters, setters, constructors,
   builder(), toString/equals/hashCode, logger) and the Lombok dependency is removed from
   pom.xml. If a file uses a Lombok feature this module cannot translate, that file is left
   alone and Lombok stays in the pom.
2. builder() calls on classes that have no builder (tests often call Entity.builder()).
3. A route prefix such as /api that the plan never asked for.
4. Mockito on a new JDK: Mockito's default "inline" mock maker attaches a Java agent to the
   test JVM, which fails on some JDK/ByteBuddy combinations ("Could not self-attach to current
   VM ..." / "Could not initialize plugin: interface org.mockito.plugins.MockMaker"). Every
   test then errors before it runs. The pom is given surefire flags that make the attach work,
   and use_subclass_mock_maker() is a fallback that needs no agent at all.

Every function is idempotent: running it twice changes nothing the second time.
"""
import os
import re

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_LOMBOK_IMPORT_RE = re.compile(r"^[ \t]*import\s+(?:static\s+)?lombok\.[\w.*]+\s*;[ \t]*\r?\n?", re.MULTILINE)

_LOMBOK_ANNOT_RE = re.compile(
    r"@(?:lombok\.)?(Data|Getter|Setter|NoArgsConstructor|AllArgsConstructor|RequiredArgsConstructor|"
    r"Builder|ToString|EqualsAndHashCode|Slf4j)\b(?!\.)(\s*\((?:[^()]|\([^()]*\))*\))?"
)
_LOMBOK_NONNULL_RE = re.compile(r"@(?:lombok\.)?NonNull\b")
_LOMBOK_UNSUPPORTED_RE = re.compile(
    r"@(?:lombok\.)?(?:With|Singular|SuperBuilder|Cleanup|SneakyThrows|Synchronized|Log|Log4j|Log4j2|"
    r"CommonsLog|XSlf4j|JBossLog|Flogger|CustomLog|UtilityClass|Accessors|FieldDefaults|Delegate|"
    r"Jacksonized|ExtensionMethod|Locked)\b|@(?:lombok\.)?Builder\.|@lombok\.Value\b"
)
_ANNOTATION_RE = re.compile(r"@[\w.]+(?:\s*\((?:[^()]|\([^()]*\))*\))?")
_CLASS_DECL_RE = re.compile(
    r"(?<![.\w])((?:(?:public|protected|private|abstract|final|static|sealed|strictfp)\s+)*)"
    r"(class|interface|enum|record)\s+(\w+)"
)
_RELATION_RE = re.compile(r"@(?:OneToMany|ManyToMany|ManyToOne|OneToOne)\b")
_ACCESS = {"PUBLIC": "public ", "PROTECTED": "protected ", "PACKAGE": "", "PRIVATE": "private "}


def _normalize_key(path: str) -> str:
    """Same canonical project-relative path the file writer uses."""
    p = path.replace("\\", "/")
    p = re.sub(r"^/?[A-Za-z]:/", "", p)
    m = re.search(r"(src/(?:main|test)/.+)$", p)
    return m.group(1) if m else p.lstrip("/")


def _mask(src: str) -> str:
    """Copy of `src` (same length, same newlines) with the CONTENT of comments, string
    literals and char literals blanked out, so braces/parentheses/annotations inside them
    can never confuse the structural scans below."""
    out = list(src)
    n = len(src)
    i = 0
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if src[k] != "\n":
                    out[k] = " "
            i = j
        elif c == '"' and src.startswith('"""', i):
            j = src.find('"""', i + 3)
            j = n if j == -1 else j + 3
            for k in range(i + 3, max(i + 3, j - 3)):
                if src[k] != "\n":
                    out[k] = " "
            i = j
        elif c in "\"'":
            q = c
            j = i + 1
            while j < n and src[j] != q:
                if src[j] == "\\":
                    j += 1
                if j < n and src[j] == "\n":
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if src[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _match_brace(mask: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(mask)):
        if mask[i] == "{":
            depth += 1
        elif mask[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _count_params(params: str) -> int:
    params = params.strip()
    if not params:
        return 0
    depth, count = 0, 1
    for ch in params:
        if ch in "<(":
            depth += 1
        elif ch in ">)":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def _cap(name: str) -> str:
    return name[:1].upper() + name[1:]


def _apply_edits(src: str, edits: list[tuple[int, int, str]]) -> str:
    """edits = (start, end, replacement); applied from the end so indexes stay valid."""
    for start, end, text in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        src = src[:start] + text + src[end:]
    return src


def _removal_span(src: str, start: int, end: int) -> tuple[int, int]:
    """Span to delete for an annotation at [start, end): the whole line when the annotation
    is alone on it, otherwise just the annotation and one trailing space."""
    n = len(src)
    left = start
    while left > 0 and src[left - 1] in " \t":
        left -= 1
    if left == 0 or src[left - 1] == "\n":
        right = end
        while right < n and src[right] in " \t":
            right += 1
        if right < n and src[right] == "\r":
            right += 1
        if right < n and src[right] == "\n":
            right += 1
            return left, right
    right = end
    if right < n and src[right] == " ":
        right += 1
    return start, right


# ---------------------------------------------------------------------------
# class parsing
# ---------------------------------------------------------------------------

class _Field:
    __slots__ = ("name", "type", "is_static", "is_final", "has_init", "annots", "relation",
                 "want_getter", "want_setter", "no_getter", "no_setter", "span")

    def __init__(self):
        self.annots = ""
        self.relation = False
        self.want_getter = self.want_setter = self.no_getter = self.no_setter = False


def _parse_class(src: str):
    """Structure of the first top-level class in `src`, or None if it is not a plain class."""
    mask = _mask(src)
    m = _CLASS_DECL_RE.search(mask)
    if not m or m.group(2) != "class":
        return None
    body_open = mask.find("{", m.end())
    if body_open == -1:
        return None
    body_close = _match_brace(mask, body_open)
    if body_close == -1:
        return None

    head_start = 0
    for hm in re.finditer(r"^\s*(?:import|package)\b[^;]*;", mask[:m.start()], re.MULTILINE):
        head_start = hm.end()

    class_annots = []  # (name, args, start, end)
    for am in _LOMBOK_ANNOT_RE.finditer(mask, head_start, m.start()):
        class_annots.append((am.group(1), am.group(2) or "", am.start(), am.end()))

    fields: list[_Field] = []
    depth = paren = 0
    stmt_start = body_open + 1
    for i in range(body_open + 1, body_close):
        ch = mask[i]
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "{" and paren == 0:
            depth += 1
        elif ch == "}" and paren == 0:
            depth -= 1
            if depth == 0:
                stmt_start = i + 1
        elif ch == ";" and depth == 0 and paren == 0:
            f = _parse_field(mask, stmt_start, i)
            if f is not None:
                fields.append(f)
            stmt_start = i + 1

    name = m.group(3)
    body_mask = mask[body_open:body_close]
    arities = set()
    for cm in re.finditer(
        r"^[ \t]*(?:public\s+|protected\s+|private\s+)?" + re.escape(name) +
        r"\s*\(([^)]*)\)\s*(?:throws[^{]*)?\{", body_mask, re.MULTILINE
    ):
        arities.add(_count_params(cm.group(1)))

    return {
        "mask": mask, "name": name, "decl_start": m.start(), "body_open": body_open,
        "body_close": body_close, "head_start": head_start, "annots": class_annots,
        "fields": fields, "arities": arities, "body_mask": body_mask,
    }


def _parse_field(mask: str, start: int, end: int):
    text = mask[start:end]
    ann_text = " ".join(a.group(0) for a in _ANNOTATION_RE.finditer(text))
    core = _ANNOTATION_RE.sub(" ", text).strip()
    if not core or "(" in core.split("=")[0]:
        return None
    m = re.match(
        r"^((?:(?:private|protected|public|static|final|transient|volatile)\s+)*)(.+?)\s+(\w+)\s*(=\s*.+)?$",
        core, re.S,
    )
    if not m:
        return None
    mods = m.group(1)
    f = _Field()
    f.span = (start, end)
    f.type = re.sub(r"\s+", " ", m.group(2)).strip()
    f.name = m.group(3)
    f.is_static = "static" in mods
    f.is_final = "final" in mods
    f.has_init = bool(m.group(4))
    f.annots = ann_text
    f.relation = bool(_RELATION_RE.search(ann_text))
    for am in _LOMBOK_ANNOT_RE.finditer(ann_text):
        kind, args = am.group(1), am.group(2) or ""
        none = "AccessLevel.NONE" in args
        if kind == "Getter":
            f.want_getter, f.no_getter = not none, none
        elif kind == "Setter":
            f.want_setter, f.no_setter = not none, none
    return f


def _getter_name(f: _Field) -> str:
    if f.type == "boolean":
        return f.name if re.match(r"^is[A-Z]", f.name) else "is" + _cap(f.name)
    return "get" + _cap(f.name)


def _setter_name(f: _Field) -> str:
    n = f.name
    if f.type == "boolean" and re.match(r"^is[A-Z]", n):
        n = n[2:]
    return "set" + _cap(n)


def _has_method(body_mask: str, name: str) -> bool:
    return re.search(r"\b" + re.escape(name) + r"\s*\(", body_mask) is not None


# ---------------------------------------------------------------------------
# code generation
# ---------------------------------------------------------------------------

def _gen_ctor(name: str, fields: list[_Field], access: str = "public ") -> str:
    params = ", ".join(f"{f.type} {f.name}" for f in fields)
    body = "".join(f"        this.{f.name} = {f.name};\n" for f in fields)
    return f"    {access}{name}({params}) {{\n{body}    }}\n"


def _gen_builder(name: str, ctor_fields: list[_Field]) -> str:
    b = f"{name}Builder"
    lines = [f"    public static {b} builder() {{\n        return new {b}();\n    }}\n",
             f"    public static class {b} {{\n"]
    for f in ctor_fields:
        lines.append(f"        private {f.type} {f.name};\n")
    lines.append("\n")
    for f in ctor_fields:
        lines.append(
            f"        public {b} {f.name}({f.type} {f.name}) {{\n"
            f"            this.{f.name} = {f.name};\n            return this;\n        }}\n\n"
        )
    args = ", ".join(f.name for f in ctor_fields)
    lines.append(f"        public {name} build() {{\n            return new {name}({args});\n        }}\n    }}\n")
    return "".join(lines)


def _gen_to_string(name: str, fields: list[_Field]) -> str:
    parts = [f'"{name}{{"']
    for i, f in enumerate(fields):
        prefix = "" if i == 0 else ", "
        parts.append(f'"{prefix}{f.name}=" + {f.name}')
    parts.append('"}"')
    return ("    @Override\n    public String toString() {\n        return "
            + " + ".join(parts) + ";\n    }\n")


def _gen_equals_hash(name: str, fields: list[_Field]) -> str:
    cmp_ = " && ".join(f"java.util.Objects.equals({f.name}, other.{f.name})" for f in fields) or "true"
    hash_args = ", ".join(f.name for f in fields)
    return (
        "    @Override\n    public boolean equals(Object o) {\n"
        "        if (this == o) return true;\n"
        "        if (o == null || getClass() != o.getClass()) return false;\n"
        f"        {name} other = ({name}) o;\n"
        f"        return {cmp_};\n    }}\n\n"
        f"    @Override\n    public int hashCode() {{\n        return java.util.Objects.hash({hash_args});\n    }}\n"
    )


def _members_for(info, want_builder: bool, builder_only: bool = False) -> str:
    """Plain-Java members that replace the Lombok annotations of this class."""
    name = info["name"]
    annots = {a[0]: a[1] for a in info["annots"]}
    fields = info["fields"]
    body_mask = info["body_mask"]
    arities = set(info["arities"])
    inst = [f for f in fields if not f.is_static]
    ctor_fields = [f for f in inst if not (f.is_final and f.has_init)]
    required = [f for f in inst if f.is_final and not f.has_init]
    out: list[str] = []

    is_data = "Data" in annots
    class_getter = is_data or "Getter" in annots
    class_setter = is_data or "Setter" in annots

    def access_of(args: str) -> str:
        am = re.search(r"AccessLevel\.(\w+)", args)
        return _ACCESS.get(am.group(1), "public ") if am else "public "

    if not builder_only:
        # constructors
        explicit = set(arities)
        if "NoArgsConstructor" in annots and 0 not in explicit:
            out.append(_gen_ctor(name, [], access_of(annots["NoArgsConstructor"])))
            explicit.add(0)
        if "AllArgsConstructor" in annots and len(ctor_fields) not in explicit:
            out.append(_gen_ctor(name, ctor_fields, access_of(annots["AllArgsConstructor"])))
            explicit.add(len(ctor_fields))
        if "RequiredArgsConstructor" in annots and len(required) not in explicit:
            out.append(_gen_ctor(name, required, access_of(annots["RequiredArgsConstructor"])))
            explicit.add(len(required))
        no_ctor_annot = not any(k in annots for k in ("NoArgsConstructor", "AllArgsConstructor", "RequiredArgsConstructor"))
        if is_data and no_ctor_annot and not arities and "Builder" not in annots and len(required) not in explicit:
            out.append(_gen_ctor(name, required))
            explicit.add(len(required))
        if "Builder" in annots and len(ctor_fields) not in explicit:
            out.append(_gen_ctor(name, ctor_fields))
            explicit.add(len(ctor_fields))

        # getters / setters
        for f in inst:
            if (class_getter and not f.no_getter) or f.want_getter:
                if not _has_method(body_mask, _getter_name(f)):
                    out.append(f"    public {f.type} {_getter_name(f)}() {{\n        return this.{f.name};\n    }}\n")
            if ((class_setter and not f.no_setter) or f.want_setter) and not f.is_final:
                if not _has_method(body_mask, _setter_name(f)):
                    out.append(f"    public void {_setter_name(f)}({f.type} {f.name}) {{\n        this.{f.name} = {f.name};\n    }}\n")

        # toString / equals / hashCode (JPA relations are left out to avoid infinite recursion)
        plain = [f for f in inst if not f.relation and "transient" not in f.annots]
        if (is_data or "ToString" in annots) and not _has_method(body_mask, "toString"):
            out.append(_gen_to_string(name, plain))
        if (is_data or "EqualsAndHashCode" in annots) and not _has_method(body_mask, "equals"):
            out.append(_gen_equals_hash(name, plain))

    if want_builder and not _has_method(body_mask, "builder"):
        if builder_only and len(ctor_fields) not in arities:
            out.append(_gen_ctor(name, ctor_fields))
        out.append(_gen_builder(name, ctor_fields))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# public: source level
# ---------------------------------------------------------------------------

def delombok_source(src: str) -> tuple[str, bool]:
    """Rewrite a Java source file that uses Lombok into plain Java.

    Returns (new_source, ok). ok is False when the file uses a Lombok feature that is not
    translated (the original text is returned unchanged). A file without Lombok is returned
    unchanged with ok True."""
    if "lombok" not in src and not re.search(r"@(Data|Getter|Setter|Builder|Slf4j|NoArgsConstructor|AllArgsConstructor|RequiredArgsConstructor|ToString|EqualsAndHashCode)\b", src):
        return src, True
    has_lombok_import = bool(re.search(r"import\s+lombok\.", src)) or "@lombok." in src
    if not has_lombok_import:
        return src, True  # same-named annotations from another library

    mask = _mask(src)
    no_imports = _LOMBOK_IMPORT_RE.sub("", mask)
    if _LOMBOK_UNSUPPORTED_RE.search(no_imports):
        return src, False
    if re.search(r"@Value\b(?!\s*\()", no_imports) and not re.search(r"import\s+org\.springframework[\w.]*\.Value\s*;", mask):
        return src, False  # Lombok @Value (immutable class) is not translated

    info = _parse_class(src)
    if info is None:
        return src, False

    annots = {a[0]: a[1] for a in info["annots"]}
    members = _members_for(info, want_builder="Builder" in annots)

    edits: list[tuple[int, int, str]] = []
    for _name, _args, s, e in info["annots"]:
        edits.append((*_removal_span(src, s, e), ""))
    # field level lombok annotations (and lombok @NonNull) anywhere inside the class body
    body_open, body_close = info["body_open"], info["body_close"]
    nonnull_ok = bool(re.search(r"import\s+lombok\.(NonNull|\*)", mask)) and not re.search(r"import\s+org\.springframework\.lang\.NonNull", mask)
    for f_info in info["fields"]:
        # only annotations that sit on a FIELD are translated; one on a nested class or a
        # method stays in the text and makes the final check below bail out.
        fs, fe = f_info.span
        for am in _LOMBOK_ANNOT_RE.finditer(mask, fs, fe):
            edits.append((*_removal_span(src, am.start(), am.end()), ""))
        if nonnull_ok:
            for nm in _LOMBOK_NONNULL_RE.finditer(mask, fs, fe):
                edits.append((*_removal_span(src, nm.start(), nm.end()), ""))
    for im in _LOMBOK_IMPORT_RE.finditer(src):
        edits.append((im.start(), im.end(), ""))

    if "Slf4j" in annots and not re.search(r"\blog\b\s*=", info["body_mask"]):
        logger = (f"\n    private static final org.slf4j.Logger log = "
                  f"org.slf4j.LoggerFactory.getLogger({info['name']}.class);\n")
        edits.append((body_open + 1, body_open + 1, logger))
    if members.strip():
        edits.append((body_close, body_close, "\n" + members + "\n"))

    new_src = _apply_edits(src, edits)
    # Anything Lombok-related still left (nested classes, odd placement) -> not safe to translate.
    left = _mask(new_src)
    if re.search(r"\blombok\b", left) or _LOMBOK_ANNOT_RE.search(left) or \
            (nonnull_ok and _LOMBOK_NONNULL_RE.search(left)):
        return src, False
    return new_src, True


def add_builder_to_source(src: str) -> str:
    """Add a builder() (and the all-args constructor it needs) to a plain class that has none."""
    info = _parse_class(src)
    if info is None or _has_method(info["body_mask"], "builder"):
        return src
    members = _members_for(info, want_builder=True, builder_only=True)
    if not members.strip():
        return src
    return _apply_edits(src, [(info["body_close"], info["body_close"], "\n" + members + "\n")])


def remove_lombok_from_pom(pom: str) -> str:
    """Drop the Lombok dependency (and any compiler-plugin / boot-plugin references)."""
    new = re.sub(r"[ \t]*<dependency>\s*<groupId>\s*org\.projectlombok\s*</groupId>.*?</dependency>[ \t]*\r?\n?",
                 "", pom, flags=re.S)
    new = re.sub(r"[ \t]*<path>\s*<groupId>\s*org\.projectlombok\s*</groupId>.*?</path>[ \t]*\r?\n?",
                 "", new, flags=re.S)
    new = re.sub(r"[ \t]*<exclude>\s*<groupId>\s*org\.projectlombok\s*</groupId>.*?</exclude>[ \t]*\r?\n?",
                 "", new, flags=re.S)
    new = re.sub(r"[ \t]*<lombok\.version>[^<]*</lombok\.version>[ \t]*\r?\n?", "", new)
    return new


# ---------------------------------------------------------------------------
# public: test runtime (Mockito / ByteBuddy on new JDKs)
# ---------------------------------------------------------------------------

_SUREFIRE_ARGLINE = ("-XX:+IgnoreUnrecognizedVMOptions -XX:+EnableDynamicAgentLoading "
                     "-Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true")
_SUREFIRE_RE = re.compile(
    r"<plugin>\s*<groupId>\s*org\.apache\.maven\.plugins\s*</groupId>\s*"
    r"<artifactId>\s*maven-surefire-plugin\s*</artifactId>.*?</plugin>", re.S)
MOCKMAKER_RESOURCE = "src/test/resources/mockito-extensions/org.mockito.plugins.MockMaker"


def harden_pom_for_tests(pom: str) -> str:
    """Give the surefire test JVM the flags that let Mockito's agent attach on newer JDKs:
    allow self-attach, allow dynamic agent loading, and let ByteBuddy accept a JDK newer than
    it knows. -XX:+IgnoreUnrecognizedVMOptions keeps the flags harmless on older JDKs."""
    if "jdk.attach.allowAttachSelf" in pom:
        return pom
    argline = f"<argLine>{_SUREFIRE_ARGLINE}</argLine>"

    m = _SUREFIRE_RE.search(pom)
    if m:
        block = m.group(0)
        if "<argLine>" in block:
            new_block = re.sub(r"<argLine>(.*?)</argLine>",
                               lambda x: "<argLine>" + x.group(1).strip() + " " + _SUREFIRE_ARGLINE + "</argLine>",
                               block, count=1, flags=re.S)
        elif "<configuration>" in block:
            new_block = block.replace("<configuration>", "<configuration>\n                    " + argline, 1)
        else:
            new_block = block.replace(
                "</plugin>",
                "    <configuration>\n                    " + argline + "\n                </configuration>\n"
                "            </plugin>", 1)
        return pom.replace(block, new_block, 1)

    plugin = (
        "            <plugin>\n"
        "                <groupId>org.apache.maven.plugins</groupId>\n"
        "                <artifactId>maven-surefire-plugin</artifactId>\n"
        "                <configuration>\n"
        f"                    {argline}\n"
        "                </configuration>\n"
        "            </plugin>\n"
    )
    last_plugins = pom.rfind("</plugins>")
    mgmt_end = pom.rfind("</pluginManagement>")
    if last_plugins != -1 and last_plugins > mgmt_end:
        return pom[:last_plugins] + plugin + "        " + pom[last_plugins:]
    if "</build>" in pom:
        i = pom.rfind("</build>")
        return pom[:i] + "    <plugins>\n" + plugin + "        </plugins>\n    " + pom[i:]
    if "</project>" in pom:
        i = pom.rfind("</project>")
        return pom[:i] + "    <build>\n        <plugins>\n" + plugin + "        </plugins>\n    </build>\n" + pom[i:]
    return pom


def use_subclass_mock_maker(project_root: str, developer_output) -> bool:
    """Fallback that needs no Java agent: tell Mockito to use its subclass mock maker. Returns
    True when it was newly applied, False when it was already in place."""
    path = os.path.join(project_root, *MOCKMAKER_RESOURCE.split("/"))
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("mock-maker-subclass\n")
    files = developer_output.files
    if files and not any(_normalize_key(f.path) == MOCKMAKER_RESOURCE for f in files):
        files.append(type(files[0])(path=MOCKMAKER_RESOURCE, content="mock-maker-subclass\n"))
    return True


# ---------------------------------------------------------------------------
# public: project level
# ---------------------------------------------------------------------------

def postprocess_generated_project(project_root: str, developer_output, plan=None) -> list[str]:
    """Apply every deterministic clean-up to the files on disk AND in developer_output.
    Returns a list of human-readable notes, empty when nothing needed changing."""
    notes: list[str] = []
    files = list(developer_output.files)

    def disk_path(gf) -> str:
        return os.path.join(project_root, _normalize_key(gf.path))

    def read(gf) -> str:
        p = disk_path(gf)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    return fh.read()
            except OSError:
                pass
        return gf.content or ""

    def write(gf, text: str) -> None:
        p = disk_path(gf)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        gf.content = text

    java = [gf for gf in files if gf.path.endswith(".java")]
    text = {id(gf): read(gf) for gf in java}

    # 1. Lombok -> plain Java
    for gf in java:
        src = text[id(gf)]
        new, ok = delombok_source(src)
        if ok and new != src:
            write(gf, new)
            text[id(gf)] = new
            notes.append(f"removed Lombok from {os.path.basename(gf.path)}")
        elif not ok:
            notes_unsupported = f"{os.path.basename(gf.path)} uses a Lombok feature that is not translated; Lombok kept"
            print(f"  [postprocess] {notes_unsupported}")

    still_uses_lombok = any(re.search(r"import\s+lombok\.|@lombok\.", t) for t in text.values())
    if not still_uses_lombok:
        for gf in files:
            if os.path.basename(gf.path) == "pom.xml":
                pom = read(gf)
                new_pom = remove_lombok_from_pom(pom)
                if new_pom != pom:
                    write(gf, new_pom)
                    notes.append("removed the Lombok dependency from pom.xml")

    # 2. builder() calls on classes without a builder
    wanted = set(re.findall(r"\b([A-Z]\w*)\.builder\(\)", "\n".join(text.values())))
    for gf in java:
        cls = os.path.basename(gf.path).removesuffix(".java")
        if cls in wanted and "src/main/" in _normalize_key(gf.path):
            src = text[id(gf)]
            new = add_builder_to_source(src)
            if new != src:
                write(gf, new)
                text[id(gf)] = new
                notes.append(f"added builder() to {cls} (it is called but was never defined)")

    # 3. a route prefix the plan never asked for
    paths = []
    for ep in (getattr(plan, "endpoints", None) or []):
        paths.append(str(getattr(ep, "path", "") or ""))
    if paths and not any(p.startswith("/api") for p in paths):
        for gf in java:
            src = text[id(gf)]
            new = src.replace('"/api/', '"/').replace('"/api"', '"/"')
            if new != src:
                write(gf, new)
                text[id(gf)] = new
                notes.append(f"removed the unplanned /api route prefix in {os.path.basename(gf.path)}")

    # 4. surefire flags so Mockito's agent can attach on newer JDKs
    for gf in files:
        if os.path.basename(gf.path) == "pom.xml":
            pom = read(gf)
            hardened = harden_pom_for_tests(pom)
            if hardened != pom:
                write(gf, hardened)
                notes.append("added surefire flags so Mockito can attach its agent on newer JDKs")

    return notes