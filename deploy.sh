#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/marco-silva0000/marco-silva.com:latest"
NS="marco-silva"

echo "==> Pulling image from ghcr.io..."
k3s ctr images pull "$IMAGE"

echo "==> Restarting deployment..."
kubectl set image -n "$NS" deploy/django django="$IMAGE" collectstatic="$IMAGE"
kubectl rollout restart -n "$NS" deploy/django
kubectl rollout status -n "$NS" deploy/django --timeout=120s

echo "==> Done. Pods:"
kubectl get pods -n "$NS"
