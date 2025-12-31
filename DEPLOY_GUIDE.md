# SeekDB ECS 部署指南

本指南帮助您在ECS服务器上快速部署SeekDB。

## 前置条件

### Linux 服务器（Ubuntu/CentOS/Rocky Linux）
- 已拥有ECS服务器root权限或sudo权限
- 服务器至少2核CPU、4GB内存（推荐4核、8GB）
- 至少50GB可用磁盘空间

### Windows 服务器
- 已拥有服务器管理员权限
- 已安装Docker Desktop
- 至少4核CPU、8GB内存
- 至少50GB可用磁盘空间

---

## Linux 服务器部署步骤

### 1. 上传部署脚本

将 `deploy_seekdb_ubuntu.sh` 上传到服务器

```bash
# 方法1: 使用scp上传
scp deploy_seekdb_ubuntu.sh root@your-server-ip:/root/

# 方法2: 在服务器上直接下载
wget https://github.com/ft3870122/feedback-tagging-system/raw/main/deploy_seekdb_ubuntu.sh
```

### 2. 执行部署脚本

```bash
# 赋予执行权限
chmod +x deploy_seekdb_ubuntu.sh

# 执行部署（推荐）
sudo bash deploy_seekdb_ubuntu.sh

# 或直接以root用户执行
sudo bash deploy_seekdb_ubuntu.sh
```

### 3. 配置ECS安全组

登录您的云服务提供商控制台（如阿里云、腾讯云、AWS等），添加安全组规则：

- **入方向规则**
  - 协议类型: TCP
  - 端口范围: 2881/2886
  - 授权对象: 0.0.0.0/0（或限制为特定IP）

### 4. 验证部署

```bash
# 检查容器状态
docker ps | grep seekdb

# 查看日志
docker logs seekdb

# 连接数据库测试
mysql -h127.0.0.1 -P2881 -uroot -A oceanbase
```

---

## Windows 服务器部署步骤

### 1. 上传部署脚本

将 `deploy_seekdb_windows.ps1` 上传到服务器，或直接在服务器上创建文件

### 2. 以管理员身份运行PowerShell

右键点击PowerShell，选择"以管理员身份运行"

### 3. 执行部署脚本

```powershell
# 设置执行策略（如果之前未设置）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 执行部署脚本
.\deploy_seekdb_windows.ps1
```

### 4. 配置Windows防火墙

脚本会自动配置防火墙规则，如果失败请手动添加：

```powershell
# 允许端口2881
New-NetFirewallRule -DisplayName "SeekDB 2881" -Direction Inbound -LocalPort 2881 -Protocol TCP -Action Allow

# 允许端口2886
New-NetFirewallRule -DisplayName "SeekDB 2886" -Direction Inbound -LocalPort 2886 -Protocol TCP -Action Allow
```

### 5. 配置ECS安全组

同Linux服务器，需要配置云服务提供商的安全组规则

---

## 常用管理命令

### Docker容器管理

```bash
# 查看容器状态
docker ps | grep seekdb

# 查看容器日志
docker logs seekdb
docker logs -f seekdb  # 实时查看

# 重启容器
docker restart seekdb

# 停止容器
docker stop seekdb

# 启动容器
docker start seekdb

# 删除容器
docker stop seekdb && docker rm seekdb

# 查看资源使用情况
docker stats seekdb
```

### 数据库连接

```bash
# 连接数据库
mysql -h127.0.0.1 -P2881 -uroot -A oceanbase

# 或从远程连接
mysql -h<服务器IP> -P2881 -uroot -A oceanbase
```

### 数据备份

```bash
# 备份数据
docker exec seekdb mysqldump -uroot feedback_db > backup.sql

# 恢复数据
docker exec -i seekdb mysql -uroot feedback_db < backup.sql
```

---

## 配置文件位置

### Linux
- 数据目录: `~/seekdb_data`
- 日志目录: `~/seekdb_logs`
- 配置文件: `/etc/oceanbase/seekdb.cnf`

### Windows
- 数据目录: `C:\Users\YourUsername\seekdb_data`
- 日志目录: `C:\Users\YourUsername\seekdb_logs`
- 配置文件: `C:\oceanbase\seekdb.cnf`

---

## 性能优化建议

### 1. 调整内存配置

编辑配置文件 `/etc/oceanbase/seekdb.cnf` (Linux) 或 `C:\oceanbase\seekdb.cnf` (Windows):

```ini
# 根据服务器配置调整
memory_limit=16G        # 增加到16GB
cpu_count=8            # 增加到8核
log_disk_size=4G       # 增加日志盘
```

重启容器生效：
```bash
docker restart seekdb
```

### 2. 使用SSD存储

将数据目录挂载到SSD分区，可获得更好的性能

### 3. 网络优化

如果使用云服务器，建议：
- 使用内网IP连接（同一地域内的应用）
- 配置专有网络（VPC）
- 使用负载均衡器分发请求

---

## 故障排查

### 1. 容器启动失败

```bash
# 查看日志
docker logs seekdb

# 检查端口占用
netstat -tulpn | grep 2881
```

### 2. 内存不足

```bash
# 检查内存使用
free -h

# 调低配置（编辑配置文件后重启）
docker stop seekdb
docker rm seekdb
# 重新运行部署脚本，使用更低的配置
```

### 3. 连接失败

- 检查安全组规则是否已开放2881端口
- 检查防火墙规则
- 确认容器是否正常运行: `docker ps`

---

## 下一步

部署成功后，您需要：

1. **初始化数据库**
   ```bash
   # 在项目目录中
   mysql -h<服务器IP> -P2881 -uroot -A oceanbase < sql/init_schema.sql
   ```

2. **配置项目环境变量**
   ```bash
   # 复制环境变量模板
   cp .env.example .env

   # 编辑配置
   nano .env
   ```

   配置以下内容：
   ```env
   SEEKDB_HOST=<服务器IP>
   SEEKDB_PORT=2881
   SEEKDB_USER=root
   SEEKDB_PASSWORD=
   SEEKDB_DATABASE=feedback_db
   ```

3. **安装项目依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行项目**
   ```bash
   python scripts/auto_tag_feedback_loop.py
   ```

---

## 联系支持

如有问题，请查看项目README或提交Issue：
https://github.com/ft3870122/feedback-tagging-system
