#!/usr/bin/env python3
"""Concurrent streaming load test — drives the Grafana GPU-utilisation / queue-depth spike on stage.
usage: python scripts/load_test.py --url http://<gateway-or-port-forward>:8080 --concurrency 16 --duration 90
"""
import argparse, asyncio, json, random, time
import httpx

PROMPTS = ["Explain Kubernetes in three sentences.", "Write a haiku about GPUs.",
           "Summarise the benefits of continuous batching in LLM serving.",
           "Give me 5 tips for reducing cloud costs.", "Explain what a KV cache is to a CTO."]
ok = err = tokens = 0

async def worker(client, url, deadline, max_tokens):
    global ok, err, tokens
    while time.time() < deadline:
        body = {"messages": [{"role": "user", "content": random.choice(PROMPTS)}], "max_tokens": max_tokens}
        try:
            async with client.stream("POST", f"{url}/stream", json=body) as r:
                async for line in r.aiter_lines():
                    if line.startswith("data:") and "[DONE]" not in line:
                        try:
                            if json.loads(line[5:])["choices"][0]["delta"].get("content"): tokens += 1
                        except Exception: pass
            ok += 1
        except Exception:
            err += 1

async def main(a):
    deadline = time.time() + a.duration
    async with httpx.AsyncClient(timeout=300) as c:
        ws = [asyncio.create_task(worker(c, a.url, deadline, a.max_tokens)) for _ in range(a.concurrency)]
        t0 = time.time()
        while time.time() < deadline:
            await asyncio.sleep(3)
            print(f"  t={time.time()-t0:5.0f}s  done={ok}  errors={err}  ~{tokens/(time.time()-t0):6.1f} chunks/s")
        await asyncio.gather(*ws)
    print(f"Finished: {ok} requests, {err} errors")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--max-tokens", type=int, default=200)
    asyncio.run(main(p.parse_args()))
