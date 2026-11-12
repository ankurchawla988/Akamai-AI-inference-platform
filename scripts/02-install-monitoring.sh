#!/usr/bin/env bash
set -euo pipefail
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo update >/dev/null
kubectl apply -f k8s/00-namespaces.yaml
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f k8s/monitoring/kube-prometheus-values.yaml
kubectl apply -f k8s/monitoring/grafana-dashboard.yaml
echo "Apply ServiceMonitors AFTER the app is deployed:  kubectl apply -f k8s/monitoring/servicemonitors.yaml"
