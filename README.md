# Enterprise AI Inference Platform on Akamai LKE

GPU-accelerated LLM inference on Kubernetes, built as a live cloud-event demo.

```
User ─► Streamlit UI ─► FastAPI Gateway ─► vLLM (Mistral-7B-Instruct) ─► NVIDIA RTX 4000 Ada
                              │                     │
                              └──── Prometheus ◄────┴── NVIDIA GPU Operator (DCGM) ──► Grafana
```

| Layer | Tech |
|---|---|
| UI | Streamlit — streaming chat with live TTFT / tokens-per-second |
| Gateway | FastAPI — `/health`, `/chat`, `/stream` (SSE proxy), Prometheus metrics |
| Runtime | vLLM — OpenAI-compatible API, PagedAttention, continuous batching |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` (fp16) |
| GPU | NVIDIA RTX 4000 Ada + NVIDIA GPU Operator |
| Platform | Akamai Linode Kubernetes Engine (LKE), namespaces `ai-platform` / `monitoring` |
| Observability | kube-prometheus-stack, DCGM exporter, pre-built Grafana dashboard |
| CI | GitHub Actions → GHCR images |

Visual diagram: [`docs/architecture.html`](docs/architecture.html) (open in a browser).

## Quick start
```bash
make gpu          # NVIDIA GPU Operator
make monitoring   # Prometheus + Grafana + dashboard
make deploy GH_USER=<you> HF_TOKEN=<optional>
make status
```
Full walkthrough and troubleshooting: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) · Stage script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)

## Repo layout
```
gateway/   FastAPI gateway + Dockerfile
ui/        Streamlit app + Dockerfile
k8s/       Manifests (kustomize) + monitoring values, ServiceMonitors, Grafana dashboard
scripts/   GPU operator / monitoring / deploy helpers, load_test.py
docs/      Architecture page, deployment guide, demo script
.github/   CI: build & push images, validate manifests
```

## Design notes
- **vLLM uses `Recreate`, not `RollingUpdate`** — one GPU means a surge pod can never schedule.
- Model weights live on a persistent volume, so restarts don't re-download ~15 GB.
- The gateway exposes TTFT and end-to-end latency histograms; vLLM and DCGM supply queue depth, tokens/s and GPU metrics.

## Roadmap
HPA/KEDA on queue depth · multi-model routing · TLS + auth + rate limiting · vision/audio models.

## License
MIT
