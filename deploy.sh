#!/usr/bin/env bash
set -euo pipefail

IMAGE="marco-silva.com:latest"
OVERLAY="${1:-prod}"
NS="marco-silva"

echo "==> Building container image..."
podman build -t "$IMAGE" -f Containerfile .

echo "==> Exporting image for k3s..."
podman save "$IMAGE" -o /tmp/marco-silva.tar
sudo k3s ctr images import /tmp/marco-silva.tar
rm /tmp/marco-silva.tar

# Generate secrets from Bitwarden if they don't exist
if [ ! -f k8s/base/postgres/secret.yaml ] || [ ! -f k8s/base/django/secret.yaml ]; then
    echo "==> Secret files missing, generating from Bitwarden..."
    ./gen-secrets.sh
fi

echo "==> Applying k8s manifests (overlay: $OVERLAY)..."
kubectl apply -k "k8s/overlays/$OVERLAY"

echo "==> Restarting django deployment..."
kubectl rollout restart -n "$NS" deploy/django

echo "==> Waiting for rollout..."
kubectl rollout status -n "$NS" deploy/django --timeout=120s

echo "==> Done. Pods:"
kubectl get pods -n "$NS"
