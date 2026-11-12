#!/usr/bin/env bash
set -euo pipefail
GH_USER="${1:?usage: 03-deploy.sh <github-user> [hf-token]}"
HF_TOKEN="${2:-}"
kubectl apply -f k8s/00-namespaces.yaml
if [ -n "$HF_TOKEN" ]; then
  kubectl -n ai-platform create secret generic hf-token --from-literal=token="$HF_TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -
fi
# Point manifests at your GHCR images without editing files
cd k8s
kustomize edit set image ghcr.io/YOUR_GH_USER/ai-gateway=ghcr.io/$GH_USER/ai-gateway:latest \
                          ghcr.io/YOUR_GH_USER/ai-ui=ghcr.io/$GH_USER/ai-ui:latest 2>/dev/null || \
  sed -i "s#YOUR_GH_USER#$GH_USER#g" 02-gateway.yaml 03-ui.yaml kustomization.yaml
cd ..
kubectl apply -k k8s/
kubectl apply -f k8s/monitoring/servicemonitors.yaml || echo "ServiceMonitor CRD missing — run 02-install-monitoring.sh first"
echo "First start downloads model weights (~15GB). Watch:  kubectl -n ai-platform logs -f deploy/vllm"
echo "UI address (NodeBalancer):  kubectl -n ai-platform get svc ui"
