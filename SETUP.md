# Proxmox + k3s Setup Guide

## 1. Create Debian 12 VM in Proxmox

In the Proxmox web UI:

1. Download Debian 12 (Bookworm) ISO: `local` → `ISO Images` → `Download from URL`
   ```
   https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.9.0-amd64-netinst.iso
   ```

2. Create VM:
   - **CPU**: 2 cores
   - **RAM**: 4096 MB
   - **Disk**: 50 GB (or more if storing photos locally)
   - **Network**: vmbr0 (bridged)
   - **OS**: Linux 6.x kernel

3. Install Debian 12 minimal (no desktop environment, enable SSH server)

4. After install, note the VM's IP address:
   ```bash
   ip addr show
   ```

## 2. Initial VM Setup

SSH into the VM:

```bash
ssh user@<VM_IP>
```

Update and install essentials:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git htop
```

Set a static IP (optional but recommended). Edit `/etc/network/interfaces`:

```
auto ens18
iface ens18 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    dns-nameservers 1.1.1.1 8.8.8.8
```

Adjust the address/gateway to match your network.

## 3. Install k3s

```bash
curl -sfL https://get.k3s.io | sh -
```

Verify it's running:

```bash
sudo k3s kubectl get nodes
```

Set up kubectl for your user:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
```

Verify:

```bash
kubectl get nodes
kubectl get pods -A
```

You should see Traefik, CoreDNS, and local-path-provisioner running.

## 4. Access kubectl from your workstation (optional)

Copy the kubeconfig to your local machine:

```bash
scp user@<VM_IP>:~/.kube/config ~/.kube/config-k3s
```

Edit `~/.kube/config-k3s` and replace `127.0.0.1` with the VM's IP address.

```bash
export KUBECONFIG=~/.kube/config-k3s
kubectl get nodes
```

## 5. Router / Network Setup

For external access:

1. **Port forward** 80 and 443 from your router to the VM's IP
2. **DNS**: Point `marco-silva.com` A record to your public IP
3. **Dynamic DNS** (if your IP changes):
   ```bash
   sudo apt install -y ddclient
   ```
   Configure `/etc/ddclient.conf` for your DNS provider.

## 6. Deploy the Application

```bash
# Clone the repo on the VM
git clone https://github.com/marco-silva0000/marco-silva.com.git
cd marco-silva.com

# Switch to v2 worktree/branch
git checkout v2

# Build the container image (k3s uses containerd, import via ctr)
sudo k3s ctr images import <image-tar>

# Or build with podman/docker and import:
podman build -t marco-silva.com:latest -f Containerfile .
podman save marco-silva.com:latest -o marco-silva.tar
sudo k3s ctr images import marco-silva.tar

# Apply k8s manifests
kubectl apply -k k8s/overlays/prod

# Run Django migrations
kubectl exec -n marco-silva deploy/django -- python manage.py migrate
kubectl exec -n marco-silva deploy/django -- python manage.py createsuperuser
```

## 7. Verify

```bash
kubectl get pods -n marco-silva
kubectl get svc -n marco-silva
kubectl get ingress -n marco-silva
```

Visit `https://marco-silva.com` (or `http://<VM_IP>` for local testing).

## 8. Useful Commands

```bash
# Logs
kubectl logs -n marco-silva deploy/django -f

# Shell into a pod
kubectl exec -n marco-silva deploy/django -it -- /bin/bash

# Restart a deployment
kubectl rollout restart -n marco-silva deploy/django

# Check storage
kubectl get pvc -n marco-silva
```
