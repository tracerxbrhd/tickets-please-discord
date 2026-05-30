#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script with sudo on Ubuntu 24.04." >&2
  exit 1
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
else
  echo "/etc/os-release was not found." >&2
  exit 1
fi

if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This installer is intended for Ubuntu. Detected: ${ID:-unknown}" >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

{
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] ' \
    "$(dpkg --print-architecture)"
  printf 'https://download.docker.com/linux/ubuntu %s stable\n' \
    "$VERSION_CODENAME"
} >/etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y \
  containerd.io \
  docker-buildx-plugin \
  docker-ce \
  docker-ce-cli \
  docker-compose-plugin

systemctl enable --now docker

if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
  usermod -aG docker "$SUDO_USER"
  echo "Added $SUDO_USER to the docker group."
  echo "Log out and back in before running docker without sudo."
fi

docker --version
docker compose version
