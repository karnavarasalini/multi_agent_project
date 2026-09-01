# benchmark_runner.py — new file at project root

import json
import time
from datetime import datetime
from pathlib import Path

TEST_REQUIREMENTS = [
    "user management REST API with JWT auth",
    "product catalog API with CRUD and pagination",
    "order management system with status tracking",
    "simple blog API with comments",
    "inventory tracking API with low-stock alerts",
    "task management API with due dates and priorities",
    "book library API with borrow/return logic",
    "expense tracker API with category filtering",
    # add more if time allows — 5-8 is a legitimate minimum
]

def run_benchmark(pipeline_fn):
    """pipeline_fn = your main.py's end-to-end run function"""
    results = []

    for req in TEST_REQUIREMENTS:
        print(f"\n[BENCHMARK] Running: {req}")
        start = time.time()

        result = {
            "requirement": req,
            "first_pass_compile_success": False,
            "final_success": False,
            "debug_iterations": 0,
            "rag_hits": 0,
            "error_categories": [],
            "time_seconds": 0
        }

        try:
            run_output = pipeline_fn(req)  # must return ProjectState or similar
            result["first_pass_compile_success"] = run_output.first_pass_success
            result["final_success"] = run_output.status == "success"
            result["debug_iterations"] = run_output.iteration
            result["rag_hits"] = getattr(run_output, "rag_cache_hits", 0)
            result["error_categories"] = getattr(run_output, "error_types", [])
        except Exception as e:
            result["final_success"] = False
            result["error_categories"] = [f"CRASH: {str(e)[:100]}"]

        result["time_seconds"] = round(time.time() - start, 2)
        results.append(result)

    save_and_report(results)
    return results

def save_and_report(results):
    Path("benchmark_results").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(f"benchmark_results/run_{ts}.json", "w") as f:
        json.dump(results, f, indent=2)

    total = len(results)
    first_pass = sum(r["first_pass_compile_success"] for r in results)
    final_pass = sum(r["final_success"] for r in results)
    avg_iters = sum(r["debug_iterations"] for r in results) / total
    total_rag_hits = sum(r["rag_hits"] for r in results)

    print("\n" + "="*50)
    print("BENCHMARK REPORT")
    print("="*50)
    print(f"Total tasks:              {total}")
    print(f"First-pass compile rate:  {first_pass}/{total} ({100*first_pass/total:.1f}%)")
    print(f"Final success rate:       {final_pass}/{total} ({100*final_pass/total:.1f}%)")
    print(f"Avg debug iterations:     {avg_iters:.2f}")
    print(f"RAG cache hits:           {total_rag_hits}")
    print("="*50)

    generate_chart(results)

def generate_chart(results):
    import matplotlib.pyplot as plt
    labels = [f"T{i+1}" for i in range(len(results))]
    first_pass = [int(r["first_pass_compile_success"]) for r in results]
    final = [int(r["final_success"]) for r in results]

    x = range(len(labels))
    plt.figure(figsize=(10, 5))
    plt.bar([i - 0.2 for i in x], first_pass, width=0.4, label="First-pass compile")
    plt.bar([i + 0.2 for i in x], final, width=0.4, label="Final (after debug)")
    plt.xticks(x, labels)
    plt.ylabel("Success (1=pass)")
    plt.title("Compile Success: Before vs After Debugger")
    plt.legend()
    plt.tight_layout()
    plt.savefig("benchmark_results/success_chart.png")
    print("[Benchmark] Chart saved to benchmark_results/success_chart.png")

if __name__ == "__main__":
    from main import run_pipeline  # your existing entry point
    run_benchmark(run_pipeline)