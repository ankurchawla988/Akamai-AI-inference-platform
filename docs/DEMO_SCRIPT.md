# Live demo script (≈10 min)

**Setup before going on stage:** UI on the main screen, Grafana on a second screen (or split), a terminal ready with `make load-test`.

1. **Hook (1 min)** — "Most AI demos show a chatbot. This shows the infrastructure underneath it."
   Show `docs/architecture.html`.
2. **Single prompt (2 min)** — Ask a question in the UI. Point out streaming tokens, then the TTFT / tokens-per-second line.
   Switch to Grafana: GPU utilisation jumps the moment the prompt is sent.
3. **Why vLLM (2 min)** — PagedAttention + continuous batching: many users share one GPU without waiting for each other.
4. **Load (3 min)** — Run `make load-test`. Watch GPU util, tokens/s, and queue depth climb on Grafana while the UI stays responsive.
5. **Resilience (1 min)** — `make chaos` kills a gateway pod; requests keep flowing via the second replica.
6. **Close (1 min)** — "GPU scheduling, streaming, and observability on Kubernetes — on Akamai Cloud."

**Backup plan:** keep a screen recording of a successful run in case of venue network issues.
