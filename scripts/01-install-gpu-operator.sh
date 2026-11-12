#!/usr/bin/env bash
# Installs the NVIDIA GPU Operator (device plugin, DCGM exporter, GPU feature discovery).
# If your LKE GPU nodes already ship with NVIDIA drivers, add: --set driver.enabled=false
# (check Akamai's LKE GPU docs for your node plan).
set -euo pipefail
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia >/dev/null
helm repo update >/dev/null
helm upgrade --install gpu-operator nvidia/gpu-operator \
  -n gpu-operator --create-namespace \
  --set dcgmExporter.serviceMonitor.enabled=true \
  "$@"
echo "Waiting for GPU capacity to appear on nodes..."
kubectl wait --for=condition=Ready pod -l app=nvidia-device-plugin-daemonset -n gpu-operator --timeout=600s || true
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
