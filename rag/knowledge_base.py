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