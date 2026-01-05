#!/bin/bash
###############################################################################
# SeekDB 自动部署脚本 (适用于 Ubuntu/Debian/CentOS/Rocky Linux)
# 用途: 在ECS服务器上自动部署SeekDB数据库
# 使用: sudo bash deploy_seekdb_ubuntu.sh
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root用户或sudo执行此脚本"
        exit 1
    fi
}

# 检测操作系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi
    log_info "检测到操作系统: $OS $VERSION"
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt update && apt upgrade -y
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rocky" ]] || [[ "$OS" == "rhel" ]]; then
        yum update -y
    fi
}

# 安装Docker
install_docker() {
    log_info "检查Docker安装状态..."

    if command -v docker &> /dev/null; then
        log_info "Docker已安装，版本: $(docker --version)"
        return 0
    fi

    log_info "开始安装Docker..."

    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt install -y docker.io docker-compose
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rocky" ]] || [[ "$OS" == "rhel" ]]; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi

    # 启动Docker服务
    systemctl start docker
    systemctl enable docker

    # 配置Docker镜像加速
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://docker.aityp.com"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

    systemctl daemon-reload
    systemctl restart docker

    log_info "Docker安装完成: $(docker --version)"
}

# 创建必要目录
create_directories() {
    log_info "创建SeekDB数据目录..."

    mkdir -p ~/seekdb_data
    mkdir -p ~/seekdb_logs
    mkdir -p /etc/oceanbase

    log_info "目录创建完成"
}

# 配置系统参数（生产环境）
configure_system() {
    log_info "配置系统参数..."

    # 调整系统参数
    cat >> /etc/sysctl.conf <<EOF
vm.swappiness = 0
fs.file-max = 65535
net.core.somaxconn = 4096
EOF

    sysctl -p

    # 调整文件描述符限制
    cat >> /etc/security/limits.conf <<EOF
* soft nofile 65535
* hard nofile 65535
EOF

    log_info "系统参数配置完成"
}

# 拉取SeekDB镜像
pull_seekdb_image() {
    log_info "拉取SeekDB Docker镜像..."
    docker pull quay.io/oceanbase/seekdb:latest
    log_info "镜像拉取完成"
}

# 配置SeekDB（可选）
configure_seekdb() {
    log_info "创建SeekDB配置文件..."

    cat > /etc/oceanbase/seekdb.cnf <<EOF
datafile_size=2G
datafile_next=2G
datafile_maxsize=50G
cpu_count=4
memory_limit=8G
log_disk_size=2G
EOF

    log_info "配置文件创建完成"
}

# 启动SeekDB容器
start_seekdb() {
    log_info "启动SeekDB容器..."

    # 检查容器是否已存在
    if docker ps -a | grep -q "seekdb"; then
        log_warn "SeekDB容器已存在，先删除旧容器..."
        docker stop seekdb 2>/dev/null || true
        docker rm seekdb 2>/dev/null || true
    fi

    docker run -d \
      --name seekdb \
      --restart unless-stopped \
      -p 2881:2881 \
      -p 2886:2886 \
      -e MODE=slim \
      -e CPU_COUNT=4 \
      -e MEMORY_LIMIT=8G \
      -e LOG_DISK_SIZE=2G \
      -e DATAFILE_SIZE=2G \
      -e DATAFILE_NEXT=2G \
      -e DATAFILE_MAXSIZE=50G \
      -v ~/seekdb_data:/root/ob \
      -v ~/seekdb_logs:/var/log/oceanbase \
      quay.io/oceanbase/seekdb:latest

    log_info "SeekDB容器启动完成"
}

# 验证SeekDB状态
verify_seekdb() {
    log_info "等待SeekDB启动..."

    sleep 30

    if docker ps | grep -q "seekdb"; then
        log_info "SeekDB容器运行状态: 正常"
        docker logs seekdb | tail -20
        log_info "SeekDB已成功启动！"
        log_info "连接信息: localhost:2881"
        log_info "默认用户: root"
        log_info "查看日志: docker logs -f seekdb"
    else
        log_error "SeekDB启动失败，请检查日志: docker logs seekdb"
        exit 1
    fi
}

# 安装MySQL客户端
install_mysql_client() {
    log_info "检查MySQL客户端..."

    if command -v mysql &> /dev/null || command -v obclient &> /dev/null; then
        log_info "MySQL客户端已安装"
        return 0
    fi

    log_info "安装MySQL客户端..."

    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt install -y mysql-client
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rocky" ]] || [[ "$OS" == "rhel" ]]; then
        yum install -y mysql
    fi

    log_info "MySQL客户端安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙规则..."

    # 检查防火墙类型
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=2881/tcp
        firewall-cmd --permanent --add-port=2886/tcp
        firewall-cmd --reload
        log_info "firewalld规则已添加"
    elif command -v ufw &> /dev/null; then
        ufw allow 2881/tcp
        ufw allow 2886/tcp
        log_info "ufw规则已添加"
    else
        log_warn "未检测到防火墙，跳过防火墙配置"
        log_warn "请手动开放端口: 2881, 2886"
    fi
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "========================================"
    echo "SeekDB 部署完成！"
    echo "========================================"
    echo ""
    echo "连接信息:"
    echo "  主机: localhost"
    echo "  端口: 2881"
    echo "  用户: root"
    echo "  密码: (默认为空)"
    echo ""
    echo "常用命令:"
    echo "  查看容器状态: docker ps | grep seekdb"
    echo "  查看容器日志: docker logs -f seekdb"
    echo "  重启容器: docker restart seekdb"
    echo "  停止容器: docker stop seekdb"
    echo ""
    echo "连接数据库:"
    echo "  mysql -h127.0.0.1 -P2881 -uroot -A oceanbase"
    echo ""
    echo "下一步:"
    echo "  1. 修改安全组规则，开放端口 2881"
    echo "  2. 配置 .env 文件中的数据库连接信息"
    echo "  3. 执行数据库初始化脚本"
    echo ""
    echo "========================================"
}

# 主函数
main() {
    echo "========================================"
    echo "SeekDB 自动部署脚本"
    echo "========================================"
    echo ""

    check_root
    detect_os
    update_system
    install_docker
    create_directories
    configure_system
    pull_seekdb_image
    configure_seekdb
    start_seekdb
    verify_seekdb
    install_mysql_client
    configure_firewall
    show_deployment_info
}

# 执行主函数
main