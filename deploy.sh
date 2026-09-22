#!/usr/bin/env bash
# ==============================================================================
# x-analytics 本地一键发布脚本
#
# 核心优势：
# 1. 本机国内常用 IP 直连免密 SSH，彻底消除 GitHub Actions 境外 IP 导致的【ECS非常用地登录】邮件告警
# 2. 自动检查未提交/未推送代码并推送
# 3. 实时监听 GitHub Actions 镜像构建状态 (gh run watch)
# 4. 构建完成后，秒级直连阿里云 ECS 拉取最新镜像并平滑重启容器
# 5. 自动多轮健康检查，确保上线成功
# ==============================================================================

set -e

# --- 服务器与服务配置 ---
SERVER_HOST="8.129.84.229"
SERVER_USER="root"
REMOTE_DIR="/opt/xera"
CONTAINER_NAME="xanalytics"
HEALTH_CHECK_URL="http://8.129.84.229:2012/?tab=qdii"
REPO_NAME="xera-2011/x-analytics"

# --- 颜色定义 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }
title() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}\n"; }

show_help() {
  cat << EOF
x-analytics 部署管理工具

用法:
  ./deploy.sh [选项]

选项:
  (无参数)          全自动发布流程: 检查Git -> 推送 -> 监听构建 -> 远程更新 -> 健康检查
  -s, --skip-build   跳过 GitHub 构建等待，直接登录服务器拉取最新 ACR 镜像并重启
  -r, --restart      仅在服务器上重启 xanalytics 容器 (不拉取镜像)
  -l, --logs         查看服务器上 xanalytics 容器的实时运行日志
  --status           查看服务器上全部容器运行状态 (docker compose ps)
  -h, --help         显示此帮助信息

示例:
  ./deploy.sh              # 正常发布新代码
  ./deploy.sh --skip-build # 镜像已构建好，仅在服务器拉取并生效
  ./deploy.sh --logs       # 查看线上实时日志
EOF
}

# 1. 检查 SSH 连接
check_ssh() {
  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${SERVER_USER}@${SERVER_HOST}" "echo ok" >/dev/null 2>&1; then
    error "无法免密连接到服务器 ${SERVER_USER}@${SERVER_HOST}，请检查 ~/.ssh 密钥配置。"
    exit 1
  fi
}

# 2. 远程执行拉取与重启
do_remote_deploy() {
  title "正在连接服务器执行容器更新"
  info "目标主机: ${SERVER_USER}@${SERVER_HOST}"
  
  ssh "${SERVER_USER}@${SERVER_HOST}" "
    set -e
    cd ${REMOTE_DIR}
    echo '>>> 1/3 拉取最新镜像...'
    docker compose pull ${CONTAINER_NAME}
    echo '>>> 2/3 重建并启动容器...'
    docker compose up -d --force-recreate --remove-orphans ${CONTAINER_NAME}
    echo '>>> 3/3 清理旧版本悬空镜像...'
    docker image prune -f >/dev/null 2>&1 || true
    echo '>>> 远程容器更新完成'
  "
  success "远程 Docker 容器已更新并启动！"
}

# 3. 健康检查
do_health_check() {
  title "执行线上健康检查"
  info "请求地址: ${HEALTH_CHECK_URL}"
  
  local max_retries=15
  local retry_count=0
  local wait_seconds=2

  while [ $retry_count -lt $max_retries ]; do
    retry_count=$((retry_count + 1))
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_CHECK_URL}" 2>/dev/null || echo "000")
    
    if [ "$code" = "200" ]; then
      success "服务健康检查通过 (HTTP 200)！(耗时 $((retry_count * wait_seconds)) 秒)"
      return 0
    elif [ "$code" = "502" ] || [ "$code" = "000" ]; then
      echo -e "  ⏳ 等待应用启动中 (HTTP $code)... [$retry_count/$max_retries]"
    else
      echo -e "  ⏳ 等待应用响应 (HTTP $code)... [$retry_count/$max_retries]"
    fi
    sleep $wait_seconds
  done

  warn "健康检查在 30 秒内未返回 HTTP 200。请排查日志: ./deploy.sh --logs"
  return 1
}

# 处理不同子命令
case "$1" in
  -h|--help)
    show_help
    exit 0
    ;;
  -l|--logs)
    check_ssh
    info "正在连接服务器查看 ${CONTAINER_NAME} 实时日志 (Ctrl+C 退出)..."
    exec ssh -t "${SERVER_USER}@${SERVER_HOST}" "docker logs -f --tail 100 ${CONTAINER_NAME}"
    ;;
  --status)
    check_ssh
    title "服务器容器运行状态"
    ssh "${SERVER_USER}@${SERVER_HOST}" "cd ${REMOTE_DIR} && docker compose ps"
    exit 0
    ;;
  -r|--restart)
    check_ssh
    title "重启服务器上的 ${CONTAINER_NAME} 容器"
    ssh "${SERVER_USER}@${SERVER_HOST}" "cd ${REMOTE_DIR} && docker compose restart ${CONTAINER_NAME}"
    do_health_check
    exit 0
    ;;
  -s|--skip-build)
    check_ssh
    do_remote_deploy
    do_health_check
    title "部署完成"
    success "🎉 发布成功！在线访问: ${HEALTH_CHECK_URL}"
    exit 0
    ;;
  "")
    # 默认全自动流程
    ;;
  *)
    error "未知参数: $1"
    show_help
    exit 1
    ;;
esac

# ================= 全自动发布流程 =================
START_TIME=$(date +%s)
title "开始全自动本地发布流程"
check_ssh

# 1. 检查工作区是否有未提交修改
if [ -n "$(git status --porcelain)" ]; then
  warn "检测到本地有未提交的代码修改:"
  git status -s
  echo ""
  read -p "是否现在提交所有变更并发布? (y/N): " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "请输入 Commit 提交信息: " COMMIT_MSG
    if [ -z "$COMMIT_MSG" ]; then
      COMMIT_MSG="chore: update $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    git add -A
    git commit -m "$COMMIT_MSG"
    success "已完成本地提交: $COMMIT_MSG"
  else
    error "发布中止：请先处理未提交的更改。"
    exit 1
  fi
fi

# 2. 检查是否有未推送的提交
LOCAL_AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")
if [ "$LOCAL_AHEAD" -gt 0 ]; then
  info "发现 $LOCAL_AHEAD 个未推送到 GitHub 的本地提交，正在推送..."
  git push origin main
  success "代码推送完成！"
else
  info "本地代码已与 GitHub origin/main 保持同步。"
fi

CURRENT_COMMIT=$(git rev-parse HEAD)
SHORT_COMMIT=$(git rev-parse --short HEAD)
info "当前发布版本 Commit: ${SHORT_COMMIT}"

# 3. 查找 GitHub Actions 构建任务
info "正在监听 GitHub Actions 镜像构建任务..."
RUN_ID=""
for i in {1..20}; do
  RUN_ID=$(gh run list -R "$REPO_NAME" --commit "$CURRENT_COMMIT" --json databaseId -q '.[0].databaseId' 2>/dev/null || true)
  if [ -n "$RUN_ID" ]; then
    break
  fi
  sleep 2
done

if [ -z "$RUN_ID" ]; then
  warn "未在 40 秒内匹配到 Commit (${SHORT_COMMIT}) 对应的 GitHub 构建任务。"
  warn "可能是此 Commit 未包含触发构建的文件，或者构建稍有延迟。"
  read -p "是否直接在服务器上拉取最新镜像部署? (Y/n): " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    do_remote_deploy
    do_health_check
    exit 0
  else
    exit 1
  fi
fi

info "锁定 GitHub 构建任务 ID: $RUN_ID"
info "正在实时监控构建进度（该步骤使用 GitHub 算力打包，完成后走阿里云容器镜像服务，不触发 ECS 告警）..."

if ! gh run watch "$RUN_ID" -R "$REPO_NAME" --compact --exit-status; then
  error "GitHub Actions 构建失败！请检查错误日志: gh run view $RUN_ID --log-failed"
  exit 1
fi

success "GitHub 镜像构建并推送到阿里云 ACR 成功！"

# 4. 本地直连 SSH 执行服务器拉取与更新
do_remote_deploy

# 5. 健康检查
do_health_check

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

title "发布完成"
success "🎉 全流程发布成功！总耗时: ${DURATION}s"
info "线上访问地址: ${HEALTH_CHECK_URL}"
