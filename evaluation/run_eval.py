import json, requests, time

dataset = json.load(open("chatbot_eval_dataset.json"))
results = []

for q in dataset["queries"]:
    resp = requests.post("http://localhost:8000/chat", json={
        "query": q["query"],
        "session_id": "eval-batch-001"
    })
    data = resp.json()
    results.append({
        "id": q["id"],
        "query": q["query"],
        "expected_intent": q["expected"]["intent"],
        "actual_intent": data.get("intent"),
        "confidence": data.get("confidence"),
        "trace_id": data.get("trace_id"),
        "passed": data.get("intent") == q["expected"]["intent"]
    })
    time.sleep(1)  # avoid rate-limiting LiteLLM

passed = sum(1 for r in results if r["passed"])
print(f"Intent classification: {passed}/{len(results)} correct")
for r in results:
    status = "✓" if r["passed"] else "✗"
    print(f"  {status} [{r['id']}] expected={r['expected_intent']} got={r['actual_intent']} conf={r['confidence']:.2f}")
