#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/marco-silva0000/marco-silva.com:latest"
NS="marco-silva"

echo "==> Pulling latest image from ghcr.io..."
k3s ctr images pull "$IMAGE"

echo "==> Applying k8s manifests..."
kubectl apply -k k8s/overlays/prod

echo "==> Restarting deployments..."
kubectl rollout restart -n "$NS" deploy/django deploy/celery-worker deploy/celery-beat
kubectl rollout status -n "$NS" deploy/django --timeout=120s
kubectl rollout status -n "$NS" deploy/celery-worker --timeout=120s
kubectl rollout status -n "$NS" deploy/celery-beat --timeout=120s

echo "==> Done. Pods:"
kubectl get pods -n "$NS"
