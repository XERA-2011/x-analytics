#!/usr/bin/env bash
# ==============================================================================
# X-Analytics 本地开发 SSH 数据库安全隧道管理脚本
# 将云端 PostgreSQL (5432) 和 Redis (6379) 映射至本地 127.0.0.1
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 读取配置
if [ -f "${SCRIPT_DIR}/.env.local" ]; then
  # shellcheck disable=SC1091
  set -a
  source "${SCRIPT_DIR}/.env.local"
  set +a
fi

SERVER_HOST="${DEPLOY_SERVER_HOST:-${ALIYUN_HOST}}"
SERVER_USER="${DEPLOY_SERVER_USER:-${ALIYUN_USER:-root}}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$SERVER_HOST" ]; then
  echo -e "${RED}❌ 未检测到远程服务器地址，请在 .env.local 中配置 DEPLOY_SERVER_HOST=\"your-server-ip\"${NC}"
  exit 1
fi

get_tunnel_pids() {
  pgrep -f "ssh.*-L 5432:127.0.0.1:5432.*${SERVER_HOST}" || true
}

check_status() {
  local pids
  pids=$(get_tunnel_pids)
  if [ -n "$pids" ]; then
    echo -e "${GREEN}✅ SSH 数据库安全隧道正在运行 (PID: ${pids})${NC}"
    echo -e "   - PostgreSQL: 127.0.0.1:5432 -> ${SERVER_HOST}:5432"
    echo -e "   - Redis:      127.0.0.1:6379 -> ${SERVER_HOST}:6379"
    return 0
  else
    echo -e "${YELLOW}⚪ SSH 数据库安全隧道未运行${NC}"
    return 1
  fi
}

start_tunnel() {
  if check_status >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  SSH 隧道已在运行中，无需重复启动。${NC}"
    check_status
    return 0
  fi

  echo -e "${CYAN}🚀 正在建立到 ${SERVER_USER}@${SERVER_HOST} 的 SSH 安全隧道...${NC}"
  if ssh -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -f -N \
         -L 5432:127.0.0.1:5432 \
         -L 6379:127.0.0.1:6379 \
         "${SERVER_USER}@${SERVER_HOST}"; then
    sleep 0.5
    echo -e "${GREEN}✅ 隧道已成功在后台启动！${NC}"
    check_status
  else
    echo -e "${RED}❌ 启动 SSH 隧道失败，请检查网络或本地 5432/6379 端口是否被占用。${NC}"
    exit 1
  fi
}

stop_tunnel() {
  local pids
  pids=$(get_tunnel_pids)
  if [ -n "$pids" ]; then
    echo -e "${CYAN}🛑 正在关闭 SSH 隧道 (PID: ${pids})...${NC}"
    kill $pids
    sleep 0.5
    echo -e "${GREEN}✅ SSH 隧道已停止。${NC}"
  else
    echo -e "${YELLOW}⚪ 未检测到运行中的 SSH 隧道。${NC}"
  fi
}

case "$1" in
  start)
    start_tunnel
    ;;
  stop)
    stop_tunnel
    ;;
  restart)
    stop_tunnel
    sleep 0.5
    start_tunnel
    ;;
  status|"")
    check_status
    ;;
  *)
    echo "用法: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
