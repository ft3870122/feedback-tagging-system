# 客服反馈自动打标系统

基于SeekDB + Coze Agent的智能客服反馈自动打标系统，实现动态实体识别、自动打标、闭环优化和AI分析总结。

## 项目架构


### 核心组件

1. **SeekDB数据库**：存储反馈数据、实体标签、向量索引
2. **Coze智能Agent**：低置信度场景下的实体识别兜底
3. **自动打标模块**：SeekDB混合检索匹配+Coze兜底识别
4. **分析总结模块**：统计打标结果，生成业务洞察

## 快速开始

### 环境要求

#### 系统要求
- **操作系统**：Ubuntu 22.04 LTS / CentOS 7.x/8.x / Rocky Linux 9 / 其他主流Linux发行版
- **系统内核**：≥ 3.10.0（部分功能需要更高版本）
- **架构支持**：x86_64（海光）、ARM_64（鲲鹏、飞腾）
- **Python**：3.8+（AI场景推荐3.11+）
- **SeekDB**：最新版本（GitHub仓库：https://github.com/oceanbase/seekdb）
- **Coze Agent**：API 访问权限

#### 硬件要求
- **CPU**：最低1核，推荐4核+
- **内存**：最低2GB（演示环境），推荐4GB+（生产环境），8GB+更佳（同时进行向量生成和查询）
- **磁盘**：最低10GB可用空间，推荐50GB+
  - 日志盘空间需不小于内存容量的1倍
  - 数据盘空间需满足业务数据存储需求
- **存储类型**：推荐SSD存储以获得最佳性能
- **网络**：至少1GE网卡，推荐千兆或万兆网卡

#### 必需依赖项
- **数据库客户端**：MySQL客户端或OBClient（**必需**，用于连接SeekDB数据库）
- **Docker**：20.10+（如使用Docker部署方式）
- **Python库**：pymysql, numpy, sentence-transformers等（AI场景）

### 安装部署

#### 前置条件检查

在安装SeekDB之前，请先检查系统环境是否满足要求：

```bash
# 检查系统内核版本
uname -r

# 检查可用内存
free -h

# 检查可用磁盘空间
df -h

# 检查Python版本
python3 --version

# 检查Docker版本（如使用Docker部署）
docker --version

# 检查SELinux状态（建议测试环境临时关闭）
getenforce
# 临时关闭SELinux
setenforce 0
# 永久关闭SELinux（修改配置文件）
sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
```

1. **系统依赖安装**

```bash
# 更新系统
apt update && apt upgrade -y  # Ubuntu/Debian
# 或
yum update -y  # CentOS/RHEL

# 安装必要工具
apt install -y python3 python3-pip python3-venv git  # Ubuntu/Debian
# 或
yum install -y python3 python3-pip python3-venv git  # CentOS/RHEL

# 安装编译依赖（如需源码编译Python）
apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev  # Ubuntu/Debian
# 或
yum install -y gcc gcc-c++ make zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel  # CentOS/RHEL

# 安装MySQL客户端（必需）
apt install -y mysql-client  # Ubuntu/Debian
# 或
yum install -y mysql  # CentOS/RHEL

# 或安装OBClient（OceanBase专用客户端，推荐）
apt install -y obclient  # Ubuntu/Debian（需添加OceanBase源）
# 或
yum install -y obclient  # CentOS/RHEL（需添加OceanBase源）

# 安装Docker（如使用Docker部署）
apt install -y docker.io  # Ubuntu/Debian
# 或
yum install -y docker-ce docker-ce-cli containerd.io  # CentOS/RHEL

# 启动Docker服务
systemctl start docker
systemctl enable docker

# 配置Docker镜像源（加速下载）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://docker.aityp.com"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

2. **SeekDB 安装（Docker方式）**

SeekDB推荐使用Docker部署，这是最简单和可靠的方式。

#### 部署前准备

##### 创建必要目录
```bash
# 创建SeekDB数据目录
mkdir -p ~/seekdb_data

# 创建SeekDB配置目录
mkdir -p /etc/oceanbase

# 创建日志目录
mkdir -p ~/seekdb_logs
```

##### 配置系统参数（生产环境推荐）
```bash
# 调整系统参数
echo "vm.swappiness = 0" >> /etc/sysctl.conf
echo "fs.file-max = 65535" >> /etc/sysctl.conf
echo "net.core.somaxconn = 4096" >> /etc/sysctl.conf
sysctl -p

# 调整文件描述符限制
echo "* soft nofile 65535" >> /etc/security/limits.conf
echo "* hard nofile 65535" >> /etc/security/limits.conf
```

#### Docker部署步骤

```bash
# 拉取SeekDB镜像
docker pull oceanbase/seekdb:latest

# 创建配置文件（可选，推荐）
cat > /etc/oceanbase/seekdb.cnf <<EOF
datafile_size=2G
datafile_next=2G
datafile_maxsize=50G
cpu_count=4
memory_limit=8G
log_disk_size=2G
EOF

# 启动SeekDB容器（基础版）
docker run -d \
  --name seekdb \
  -p 2881:2881 \
  -e MODE=slim \
  -v ~/seekdb_data:/root/ob \
  oceanbase/seekdb:latest

# 或启动SeekDB容器（完整版，带配置文件和额外端口）
docker run -d \
  --name seekdb \
  -p 2881:2881 \
  -p 2886:2886 \
  -e MODE=slim \
  -e CPU_COUNT=4 \
  -e MEMORY_LIMIT=8G \
  -e LOG_DISK_SIZE=2G \
  -e DATAFILE_SIZE=2G \
  -e DATAFILE_NEXT=2G \
  -e DATAFILE_MAXSIZE=50G \
  -v /etc/oceanbase/seekdb.cnf:/etc/oceanbase/seekdb.cnf \
  -v ~/seekdb_data:/root/ob \
  -v ~/seekdb_logs:/var/log/oceanbase \
  oceanbase/seekdb:latest

# 查看容器状态
docker ps | grep seekdb

# 查看启动日志（确认服务启动成功）
docker logs seekdb
# 或实时查看日志
docker logs -f seekdb
```

**重要提示：**
- 等待约30秒，看到"boot success"表示启动完成
- **数据卷挂载非常重要**，确保容器重启后数据不丢失
- Windows/Mac环境下Docker部署注意文件系统兼容性问题
- 如遇到权限问题，检查挂载目录的权限设置

**支持的环境变量：**
- `ROOT_PASSWORD`：root用户密码（默认空）
- `CPU_COUNT`：CPU核心数（默认4）
- `MEMORY_LIMIT`：内存限制（默认2G）
- `LOG_DISK_SIZE`：日志盘大小（默认2G）
- `DATAFILE_SIZE`：数据文件初始大小（默认2G）
- `DATAFILE_NEXT`：数据文件扩展大小（默认2G）
- `DATAFILE_MAXSIZE`：数据文件最大大小（默认50G）

3. **项目部署**

```bash
# 克隆项目
git clone https://github.com/your-username/feedback-tagging-system.git
cd feedback-tagging-system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装AI相关依赖（如需向量生成功能）
pip install sentence-transformers numpy torch

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填写SeekDB和Coze配置
```

**Python环境优化：**
```bash
# 配置pip镜像源加速安装
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 解决Python版本兼容性问题（如需要）
# 编译安装Python 3.11（CentOS 7示例）
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9
./configure --enable-optimizations --prefix=/usr/local/python311
make -j4
make altinstall

# 使用特定Python版本创建虚拟环境
/usr/local/python311/bin/python3.11 -m venv venv
```

4. **数据库初始化**

#### 验证SeekDB连接

**注意：MySQL客户端或OBClient是必需的，用于连接SeekDB数据库进行初始化和管理操作。**

```bash
# 使用MySQL客户端连接（默认密码为空）
mysql -h127.0.0.1 -P2881 -uroot -A oceanbase

# 或使用OBClient（OceanBase专用客户端，功能更完整）
obclient -h127.0.0.1 -P2881 -uroot -A oceanbase

# 验证连接成功后执行基本命令
SELECT VERSION();
SHOW DATABASES;
SHOW VARIABLES LIKE '%vector%';
```

#### 执行初始化脚本

```bash
# 直接执行SQL文件
mysql -h127.0.0.1 -P2881 -uroot -A oceanbase < sql/init_schema.sql

# 或进入MySQL客户端后执行
mysql -h127.0.0.1 -P2881 -uroot -A oceanbase
source sql/init_schema.sql;
exit;
```

#### 创建向量索引（可选，根据业务需求）

```bash
# 连接数据库后执行
mysql -h127.0.0.1 -P2881 -uroot -A feedback_db

# 创建向量索引示例
CREATE TABLE IF NOT EXISTS entity_vectors (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entity_type VARCHAR(100) NOT NULL,
    entity_value VARCHAR(255) NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_entity (entity_type, entity_value)
);

# 创建HNSW向量索引
CREATE VECTOR INDEX idx_entity_embedding ON entity_vectors(embedding) 
WITH (distance=L2, type=hnsw);

# 创建全文索引
CREATE FULLTEXT INDEX idx_entity_value ON entity_vectors(entity_value);
```

### 配置说明

项目配置通过 `.env` 文件管理：

```env
# SeekDB配置
SEEKDB_HOST=localhost
SEEKDB_PORT=2881
SEEKDB_USER=root
SEEKDB_PASSWORD=your_password
SEEKDB_DATABASE=feedback_db

# Coze配置
COZE_API_KEY=your_coze_api_key
COZE_AGENT_ID=your_coze_agent_id

# 系统配置
CONFIDENCE_THRESHOLD=0.8
BATCH_SIZE=100
LOG_LEVEL=INFO

# 向量生成配置（如使用本地模型）
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

#### SeekDB高级配置

**Docker方式配置：**
- 通过环境变量配置（如上面的启动命令所示）
- 通过挂载配置文件 `/etc/oceanbase/seekdb.cnf`

**关键配置参数说明：**
- `datafile_size`：数据文件初始大小
- `datafile_next`：数据文件扩展大小
- `datafile_maxsize`：数据文件最大大小
- `cpu_count`：使用的CPU核心数
- `memory_limit`：内存使用限制
- `log_disk_size`：日志盘大小

## 使用指南

### 手动运行打标

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行打标脚本
python scripts/auto_tag_feedback_loop.py
```

### 运行分析

```bash
# 运行分析脚本
python scripts/auto_analysis.py
```

### 定时任务配置

```bash
# 编辑crontab
crontab -e

# 添加定时任务
0 */1 * * * /path/to/venv/bin/python /path/to/feedback-tagging-system/scripts/auto_tag_feedback_loop.py >> /path/to/feedback-tagging-system/logs/tag_loop.log 2>&1
0 3 * * * /path/to/venv/bin/python /path/to/feedback-tagging-system/scripts/auto_analysis.py >> /path/to/feedback-tagging-system/logs/analysis.log 2>&1
```

## 项目结构

```
feedback-tagging-system/
├── README.md                  # 项目说明文档
├── requirements.txt           # Python依赖
├── .env.example              # 环境变量示例
├── sql/                      # SQL脚本
│   └── init_schema.sql       # 数据库初始化脚本
├── scripts/                  # 核心脚本
│   ├── auto_tag_feedback_loop.py  # 自动打标主脚本
│   └── auto_analysis.py           # 分析总结脚本
├── logs/                     # 日志目录
└── docs/                     # 文档目录
    └── architecture.md       # 架构设计文档
```

## 性能与成本

### 性能指标

- SeekDB向量检索：毫秒级响应（<10ms）
- 单实例吞吐：≥10万条/小时
- 打标准确率：≥95%（持续优化）

### 成本优势

- Coze调用成本：仅低置信度场景触发（初期约5%，后期≤1%）
- 基础设施成本：单台ECS即可支撑
- 长期维护成本：零人工干预，系统自优化

## 监控与维护

### 日志查看

```bash
# 查看打标日志
tail -f logs/tag_loop.log

# 查看分析日志
tail -f logs/analysis.log
```

### 健康检查

#### 服务状态检查

```bash
# 检查Docker容器状态
docker ps | grep seekdb
docker stats seekdb  # 查看资源使用情况

# 检查端口监听
netstat -tulpn | grep 2881
ss -tulpn | grep 2881
```

#### 数据库连接测试

```bash
# 连接数据库测试
mysql -h127.0.0.1 -P2881 -uroot -e "SELECT VERSION();"
mysql -h127.0.0.1 -P2881 -uroot -e "SHOW DATABASES;"
mysql -h127.0.0.1 -P2881 -uroot -e "SHOW TABLES FROM feedback_db;"

# 性能测试（简单查询）
mysql -h127.0.0.1 -P2881 -uroot -e "SELECT BENCHMARK(1000000, 1+1);"
```

#### 日志检查

```bash
# 查看SeekDB日志（Docker方式）
docker logs seekdb
docker logs -f --tail 100 seekdb

# 查看应用日志
tail -f logs/tag_loop.log
tail -f logs/analysis.log
```

#### 资源使用监控

```bash
# 查看系统资源使用情况
top
htop
vmstat 1
iostat -x 1

# 查看磁盘使用情况
df -h
du -sh ~/seekdb_data/*

# 查看内存使用情况
free -h
cat /proc/meminfo
```

#### 连接数检查

```bash
# 查看数据库连接数
mysql -h127.0.0.1 -P2881 -uroot -e "SHOW PROCESSLIST;"
mysql -h127.0.0.1 -P2881 -uroot -e "SELECT COUNT(*) FROM information_schema.processlist;"
```

## 故障排查

### 常见问题

1. **SeekDB启动失败**
   - 检查容器日志 `docker logs seekdb`
   - 检查端口占用：`netstat -tulpn | grep 2881`
   - 检查数据目录权限：确保数据目录有写权限
   - 内存不足：SeekDB最低需要2G内存，推荐4G+

2. **Coze调用失败**
   - 检查API Key是否正确
   - 确认Coze Agent已发布并开启API调用

3. **打标无结果**
   - 检查SeekDB向量索引是否创建成功
   - 验证反馈文本格式是否正确

## 许可证

MIT License
