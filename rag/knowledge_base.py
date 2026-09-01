from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

SPRING_BOOT_PATTERNS = [
    {
        "title": "JPA Entity Pattern",
        "snippet": """@Entity
@Table(name = "example")
public class Example {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    // getters and setters
}"""
    },
    {
        "title": "Repository Pattern",
        "snippet": """@Repository
public interface ExampleRepository extends JpaRepository<Example, Long> {
    Optional<Example> findByName(String name);
}"""
    },
    {
        "title": "REST Controller Pattern",
        "snippet": """@RestController
@RequestMapping("/api/examples")
public class ExampleController {

    private final ExampleService service;

    public ExampleController(ExampleService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<List<Example>> getAll() {
        return ResponseEntity.ok(service.findAll());
    }

    @PostMapping
    public ResponseEntity<Example> create(@RequestBody @Valid ExampleDto dto) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.create(dto));
    }
}"""
    },
    {
        "title": "Service Layer Pattern",
        "snippet": """@Service
public class ExampleServiceImpl implements ExampleService {

    private final ExampleRepository repository;

    public ExampleServiceImpl(ExampleRepository repository) {
        this.repository = repository;
    }

    @Override
    public List<Example> findAll() {
        return repository.findAll();
    }
}"""
    },
    {
        "title": "Spring Security JWT Config Pattern",
        "snippet": """@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .anyRequest().authenticated())
            .sessionManagement(sess -> sess.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
        return http.build();
    }
}"""
    },
    {
        "title": "DTO with Validation Pattern",
        "snippet": """public class ExampleDto {

    @NotBlank(message = "Name is required")
    private String name;

    // getters and setters
}"""
    },
    {
        "title": "Global Exception Handler Pattern",
        "snippet": """@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<String> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ex.getMessage());
    }
}"""
    },
]

# Load embedding model once at import time
_model = SentenceTransformer("all-MiniLM-L6-v2")

# Build embeddings for each pattern (title + snippet gives richer semantic signal)
_corpus_texts = [f"{p['title']}. {p['snippet']}" for p in SPRING_BOOT_PATTERNS]
_embeddings = _model.encode(_corpus_texts, normalize_embeddings=True)

# Build FAISS index (inner product on normalized vectors = cosine similarity)
_dimension = _embeddings.shape[1]
_index = faiss.IndexFlatIP(_dimension)
_index.add(np.array(_embeddings, dtype=np.float32))


def retrieve_patterns(task_title: str, task_description: str, top_k: int = 2) -> list[dict]:
    """Semantic retrieval over the pattern knowledge base using embeddings."""
    query = f"{task_title} {task_description}"
    query_embedding = _model.encode([query], normalize_embeddings=True)

    scores, indices = _index.search(np.array(query_embedding, dtype=np.float32), top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        pattern = SPRING_BOOT_PATTERNS[idx]
        results.append({**pattern, "score": float(score)})
    return results
# ============================================================
# SELF-IMPROVING RAG: learned patterns from successful debug fixes
# Kept in a SEPARATE index from SPRING_BOOT_PATTERNS to avoid
# breaking existing retrieve_patterns() index alignment.
# ============================================================

import json
import os
from datetime import datetime

_LEARNED_PATTERNS_PATH = "rag/learned_patterns.json"

def _load_learned_patterns() -> list[dict]:
    if os.path.exists(_LEARNED_PATTERNS_PATH):
        with open(_LEARNED_PATTERNS_PATH, "r") as f:
            return json.load(f)
    return []

def _save_learned_patterns(patterns: list[dict]):
    os.makedirs(os.path.dirname(_LEARNED_PATTERNS_PATH), exist_ok=True)
    with open(_LEARNED_PATTERNS_PATH, "w") as f:
        json.dump(patterns, f, indent=2)

# In-memory state for learned patterns (mirrors the _model/_index pattern above)
_learned_patterns: list[dict] = _load_learned_patterns()
_learned_dimension = _model.get_sentence_embedding_dimension()
_learned_index = faiss.IndexFlatIP(_learned_dimension)

# Rebuild the learned index from disk on startup, if any patterns exist
if _learned_patterns:
    _learned_texts = [f"{p['error_message']} {p['root_cause']}" for p in _learned_patterns]
    _learned_embeddings = _model.encode(_learned_texts, normalize_embeddings=True)
    _learned_index.add(np.array(_learned_embeddings, dtype=np.float32))


def add_fix_as_pattern(error_message: str, root_cause: str, fixed_code: str, file_type: str):
    """Call this from debugger_agent.py after a fix is confirmed to work (Tester passed)."""
    pattern_text = f"{error_message} {root_cause}"
    embedding = _model.encode([pattern_text], normalize_embeddings=True)
    _learned_index.add(np.array(embedding, dtype=np.float32))

    _learned_patterns.append({
        "id": len(_learned_patterns),
        "error_message": error_message,
        "root_cause": root_cause,
        "fixed_code": fixed_code,
        "file_type": file_type,
        "learned_at": datetime.now().isoformat(),
        "times_reused": 0
    })
    _save_learned_patterns(_learned_patterns)
    print(f"[RAG] Learned new pattern for: {error_message[:60]}...")


def retrieve_known_fix(error_message: str, threshold: float = 0.80) -> dict | None:
    """Call this from debugger_agent.py BEFORE calling the LLM."""
    if not _learned_patterns:
        return None

    query_embedding = _model.encode([error_message], normalize_embeddings=True)
    scores, indices = _learned_index.search(np.array(query_embedding, dtype=np.float32), 1)

    if len(indices[0]) == 0 or indices[0][0] == -1:
        return None

    score = float(scores[0][0])  # cosine similarity, since vectors are normalized
    if score >= threshold:
        match = _learned_patterns[indices[0][0]]
        match["times_reused"] += 1
        _save_learned_patterns(_learned_patterns)
        return {**match, "similarity": score}
    return None