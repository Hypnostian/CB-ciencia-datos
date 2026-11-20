#!/usr/bin/env bash
# Preparacion de una instancia EC2 con Ubuntu 24.04 para el servidor MCP.
# Uso:
#   1) Copie la carpeta del proyecto a la instancia (git clone o scp) y entre a infra/
#   2) cp .env.example .env && nano .env      (DATABASE_URL, GEMINI_API_KEY, MCP_API_KEY)
#   3) sudo bash ec2_setup.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then echo "Ejecute con sudo: sudo bash $0"; exit 1; fi
cd "$(dirname "$0")"
[[ -f .env ]] || { echo "Falta infra/.env (copie .env.example y complete los valores)"; exit 1; }
[[ -d ../mcp-server ]] || { echo "No se encuentra ../mcp-server"; exit 1; }

echo "==> Actualizando paquetes"
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Instalando Docker Engine"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi
if [[ -n "${SUDO_USER:-}" ]]; then usermod -aG docker "$SUDO_USER" || true; fi

echo "==> Firewall local (ufw): solo 22 y 9000"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 9000/tcp
ufw --force enable

echo "==> Construyendo y levantando el servidor MCP"
docker compose -f docker-compose.ec2.yml up -d --build
sleep 5
docker compose -f docker-compose.ec2.yml ps

IP=$(curl -s --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 || true)
echo
echo "Listo. URL MCP para n8n:  http://${IP:-IP_PUBLICA_EC2}:9000/mcp   (encabezado X-API-Key obligatorio)"
echo "Recuerde abrir el puerto 9000 en el Security Group de la instancia (ver SECURITY_GROUPS.md)."
