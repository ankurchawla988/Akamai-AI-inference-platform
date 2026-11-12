GH_USER ?= YOUR_GH_USER
.PHONY: help gpu monitoring deploy status logs pf-ui pf-gateway pf-grafana load-test chaos destroy

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1 | sed 's/^/  make /'

gpu:         ; ./scripts/01-install-gpu-operator.sh
monitoring:  ; ./scripts/02-install-monitoring.sh
deploy:      ; ./scripts/03-deploy.sh $(GH_USER) $(HF_TOKEN)
status:      ; kubectl get pods,svc -n ai-platform -o wide && kubectl get pods -n monitoring
logs:        ; kubectl -n ai-platform logs -f deploy/vllm
pf-ui:       ; kubectl -n ai-platform port-forward svc/ui 8501:80
pf-gateway:  ; kubectl -n ai-platform port-forward svc/gateway 8080:8080
pf-grafana:  ; kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
load-test:   ; python scripts/load_test.py --url http://localhost:8080 --concurrency 16 --duration 90
chaos:       ; kubectl -n ai-platform delete pod $$(kubectl -n ai-platform get pods -l app=gateway -o name | head -1)
destroy:     ; kubectl delete ns ai-platform --ignore-not-found
