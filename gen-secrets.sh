#!/usr/bin/env bash
set -euo pipefail

# Generates k8s secret YAML files from Bitwarden.
#
# Prerequisites:
#   1. Install Bitwarden CLI: https://bitwarden.com/help/cli/
#      sudo snap install bw  (or npm install -g @bitwarden/cli)
#
#   2. Create a Bitwarden Secure Note named "marco-silva.com/k8s" with these
#      custom fields (type: Hidden):
#        - POSTGRES_DB
#        - POSTGRES_USER
#        - POSTGRES_PASSWORD
#        - DJANGO_SECRET_KEY
#
#   3. Login and unlock:
#        bw login
#        export BW_SESSION=$(bw unlock --raw)
#
# Usage:
#   export BW_SESSION=$(bw unlock --raw)
#   ./gen-secrets.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_BASE="$SCRIPT_DIR/k8s/base"

if [ -z "${BW_SESSION:-}" ]; then
    echo "Error: BW_SESSION not set. Run: export BW_SESSION=\$(bw unlock --raw)"
    exit 1
fi

echo "==> Syncing Bitwarden vault..."
bw sync

echo "==> Fetching secrets from 'marco-silva.com/k8s'..."
ITEM=$(bw get item "marco-silva.com/k8s")

get_field() {
    echo "$ITEM" | jq -r --arg name "$1" '.fields[] | select(.name == $name) | .value'
}

POSTGRES_DB=$(get_field "POSTGRES_DB")
POSTGRES_USER=$(get_field "POSTGRES_USER")
POSTGRES_PASSWORD=$(get_field "POSTGRES_PASSWORD")
DJANGO_SECRET_KEY=$(get_field "DJANGO_SECRET_KEY")

echo "==> Generating postgres/secret.yaml..."
cat > "$K8S_BASE/postgres/secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: marco-silva
type: Opaque
stringData:
  POSTGRES_DB: ${POSTGRES_DB}
  POSTGRES_USER: ${POSTGRES_USER}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
EOF

echo "==> Generating django/secret.yaml..."
cat > "$K8S_BASE/django/secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: django-secret
  namespace: marco-silva
type: Opaque
stringData:
  SECRET_KEY: ${DJANGO_SECRET_KEY}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
EOF

echo "==> Done. Secret files generated:"
echo "    $K8S_BASE/postgres/secret.yaml"
echo "    $K8S_BASE/django/secret.yaml"
echo ""
echo "These files are gitignored. Apply with:"
echo "    kubectl apply -k k8s/overlays/prod"
