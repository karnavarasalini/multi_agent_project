from rag.knowledge_base import retrieve_patterns

results = retrieve_patterns("Add user login with token authentication", "Need secure endpoint")

for r in results:
    print(f"\n--- {r['title']} (score: {r['score']:.3f}) ---")
    print(r['snippet'])