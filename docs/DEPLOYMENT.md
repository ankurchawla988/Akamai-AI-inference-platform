# Deployment guide — Akamai LKE (GPU)

## 0. Prerequisites
- An LKE cluster with **one GPU node pool** (RTX 4000 Ada) and ideally one small CPU pool for gateway/UI/monitoring
- `kubectl`, `helm`, `kustomize` (or `kubectl >= 1.14` for `-k`), Docker (only if building locally)
- A GitHub repo with Actions enabled (images publish to GHCR)
- Optional: Hugging Face token (`HF_TOKEN`) if the Mistral repo requires accepting terms

```bash
export KUBECONFIG=~/Downloads/<cluster>-kubeconfig.yaml
kubectl get nodes
```

## 1. Publish images (GitHub Actions)
Push to `main`. The `build-and-push-images` workflow builds `ai-gateway` and `ai-ui` and pushes them to
`ghcr.io/<your-user>/…`. In GitHub → *Packages*, set both packages to **Public** (or create an image-pull secret).

## 2. GPU Operator
```bash
make gpu
# verify the GPU is schedulable:
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```
If your GPU nodes already have NVIDIA drivers, run `./scripts/01-install-gpu-operator.sh --set driver.enabled=false`.

## 3. Monitoring (Prometheus + Grafana)
```bash
make monitoring
```
Edit `adminPassword` in `k8s/monitoring/kube-prometheus-values.yaml` first.

## 4. Deploy the platform
```bash
make deploy GH_USER=<your-github-user> HF_TOKEN=<optional>
make logs        # first start downloads ~15 GB — wait for "Application startup complete"
make status
```
Get the public UI address (an Akamai NodeBalancer):
```bash
kubectl -n ai-platform get svc ui
```

## 5. Verify end to end
```bash
make pf-gateway &
curl localhost:8080/health
curl -s localhost:8080/chat -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Say hello in one line"}],"max_tokens":40}'
curl -N localhost:8080/stream -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Count to five"}],"max_tokens":40}'
```

## 6. Grafana
```bash
kubectl -n monitoring get svc monitoring-grafana     # LoadBalancer address, or: make pf-grafana
```
Dashboard: **AI Inference Platform — Live Demo** (auto-loaded). Panels: GPU util, VRAM, tokens/s, queue depth,
TTFT p95, e2e p95, active streams, ready pods.

## Troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| vLLM pod `Pending` | No allocatable `nvidia.com/gpu` — GPU Operator not ready, or toleration/taint mismatch |
| vLLM `CrashLoopBackOff` with CUDA OOM | Lower `--max-model-len` or `--gpu-memory-utilization` |
| Pod stuck `Running 0/1` for minutes | Normal on first start (model download); watch `make logs`; startupProbe allows ~15 min |
| 401/403 downloading model | Create the `hf-token` secret (`make deploy HF_TOKEN=...`) and accept the model terms on Hugging Face |
| No GPU panels in Grafana | DCGM exporter ServiceMonitor not scraped — confirm `serviceMonitorSelectorNilUsesHelmValues: false` |
| No vLLM panels | Apply `k8s/monitoring/servicemonitors.yaml` after the monitoring stack exists |
| `ImagePullBackOff` | GHCR package is private, or `YOUR_GH_USER` not replaced |
