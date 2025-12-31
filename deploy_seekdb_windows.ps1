###############################################################################
# SeekDB 自动部署脚本 (适用于 Windows Server / Windows 10/11)
# 用途: 在Windows上自动部署SeekDB数据库
# 使用: 在PowerShell (管理员模式) 中执行: .\deploy_seekdb_windows.ps1
# 注意: 需要先安装Docker Desktop
###############################################################################

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput -Message "[INFO] $Message" -Color "Green"
}

function Write-Warn {
    param([string]$Message)
    Write-ColorOutput -Message "[WARN] $Message" -Color "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput -Message "[ERROR] $Message" -Color "Red"
}

# 检查管理员权限
function Check-Admin {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "请以管理员身份运行此脚本"
        Write-Error "右键点击PowerShell，选择'以管理员身份运行'"
        exit 1
    }
}

# 检查Docker是否安装
function Check-Docker {
    Write-Info "检查Docker安装状态..."

    try {
        $dockerVersion = docker --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Docker已安装: $dockerVersion"
            return $true
        }
    }
    catch {
        # Docker命令可能不存在
    }

    Write-Warn "Docker未安装或未启动"
    Write-Warn "请先安装Docker Desktop: https://www.docker.com/products/docker-desktop"
    return $false
}

# 等待Docker启动
function Wait-Docker {
    Write-Info "等待Docker服务启动..."
    $maxWait = 60
    $waited = 0

    while ($waited -lt $maxWait) {
        try {
            $result = docker ps 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Docker服务已就绪"
                return $true
            }
        }
        catch {
            # 继续等待
        }

        Start-Sleep -Seconds 2
        $waited += 2
        Write-Host "." -NoNewline
    }

    Write-Error "Docker服务启动超时"
    Write-Warn "请手动启动Docker Desktop，然后重试此脚本"
    return $false
}

# 创建必要目录
function Create-Directories {
    Write-Info "创建SeekDB数据目录..."

    $dataDir = "$env:USERPROFILE\seekdb_data"
    $logDir = "$env:USERPROFILE\seekdb_logs"
    $configDir = "C:\oceanbase"

    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
        Write-Info "创建目录: $dataDir"
    }

    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        Write-Info "创建目录: $logDir"
    }

    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        Write-Info "创建目录: $configDir"
    }

    Write-Info "目录创建完成"
}

# 配置SeekDB
function Configure-SeekDB {
    Write-Info "创建SeekDB配置文件..."

    $configFile = "C:\oceanbase\seekdb.cnf"
    $configContent = @"
datafile_size=2G
datafile_next=2G
datafile_maxsize=50G
cpu_count=4
memory_limit=8G
log_disk_size=2G
"@

    Set-Content -Path $configFile -Value $configContent -Encoding UTF8
    Write-Info "配置文件创建完成: $configFile"
}

# 拉取SeekDB镜像
function Pull-SeekDBImage {
    Write-Info "拉取SeekDB Docker镜像..."
    docker pull quay.io/oceanbase/seekdb:latest

    if ($LASTEXITCODE -eq 0) {
        Write-Info "镜像拉取完成"
        return $true
    }
    else {
        Write-Error "镜像拉取失败"
        return $false
    }
}

# 启动SeekDB容器
function Start-SeekDB {
    Write-Info "启动SeekDB容器..."

    # 检查容器是否已存在
    $existingContainer = docker ps -a --filter "name=seekdb" --format "{{.Names}}" 2>&1
    if ($existingContainer -eq "seekdb") {
        Write-Warn "SeekDB容器已存在，先删除旧容器..."
        docker stop seekdb 2>&1 | Out-Null
        docker rm seekdb 2>&1 | Out-Null
    }

    $dataDir = "$env:USERPROFILE\seekdb_data"
    $logDir = "$env:USERPROFILE\seekdb_logs"
    $configFile = "C:\oceanbase\seekdb.cnf"

    docker run -d `
        --name seekdb `
        --restart unless-stopped `
        -p 2881:2881 `
        -p 2886:2886 `
        -e MODE=slim `
        -e CPU_COUNT=4 `
        -e MEMORY_LIMIT=8G `
        -e LOG_DISK_SIZE=2G `
        -e DATAFILE_SIZE=2G `
        -e DATAFILE_NEXT=2G `
        -e DATAFILE_MAXSIZE=50G `
        -v "${configFile}:/etc/oceanbase/seekdb.cnf" `
        -v "${dataDir}:/root/ob" `
        -v "${logDir}:/var/log/oceanbase" `
        quay.io/oceanbase/seekdb:latest

    if ($LASTEXITCODE -eq 0) {
        Write-Info "SeekDB容器启动完成"
        return $true
    }
    else {
        Write-Error "SeekDB容器启动失败"
        return $false
    }
}

# 验证SeekDB状态
function Verify-SeekDB {
    Write-Info "等待SeekDB启动..."
    Start-Sleep -Seconds 30

    $containerStatus = docker ps --filter "name=seekdb" --format "{{.Status}}" 2>&1

    if ($containerStatus) {
        Write-Info "SeekDB容器运行状态: 正常"
        Write-Info "容器状态: $containerStatus"
        Write-Info ""
        Write-Info "最近日志:"
        docker logs seekdb --tail 20

        return $true
    }
    else {
        Write-Error "SeekDB启动失败"
        Write-Warn "请检查日志: docker logs seekdb"
        return $false
    }
}

# 配置Windows防火墙
function Configure-Firewall {
    Write-Info "配置Windows防火墙..."

    try {
        # 允许端口2881
        New-NetFirewallRule -DisplayName "SeekDB 2881" -Direction Inbound -LocalPort 2881 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null

        # 允许端口2886
        New-NetFirewallRule -DisplayName "SeekDB 2886" -Direction Inbound -LocalPort 2886 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null

        Write-Info "防火墙规则已添加"
    }
    catch {
        Write-Warn "防火墙配置失败: $_"
        Write-Warn "请手动添加防火墙规则"
    }
}

# 显示部署信息
function Show-DeploymentInfo {
    $dataDir = "$env:USERPROFILE\seekdb_data"
    $logDir = "$env:USERPROFILE\seekdb_logs"
    $configFile = "C:\oceanbase\seekdb.cnf"

    Write-Host ""
    Write-Host "========================================" -ForegroundColor "Cyan"
    Write-Host "SeekDB 部署完成！" -ForegroundColor "Green"
    Write-Host "========================================" -ForegroundColor "Cyan"
    Write-Host ""
    Write-Host "连接信息:" -ForegroundColor "Yellow"
    Write-Host "  主机: localhost"
    Write-Host "  端口: 2881"
    Write-Host "  用户: root"
    Write-Host "  密码: (默认为空)"
    Write-Host ""
    Write-Host "目录信息:" -ForegroundColor "Yellow"
    Write-Host "  数据目录: $dataDir"
    Write-Host "  日志目录: $logDir"
    Write-Host "  配置文件: $configFile"
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor "Yellow"
    Write-Host "  查看容器状态: docker ps | findstr seekdb"
    Write-Host "  查看容器日志: docker logs -f seekdb"
    Write-Host "  重启容器: docker restart seekdb"
    Write-Host "  停止容器: docker stop seekdb"
    Write-Host ""
    Write-Host "连接数据库 (需要安装MySQL客户端):" -ForegroundColor "Yellow"
    Write-Host "  mysql -h127.0.0.1 -P2881 -uroot -A oceanbase"
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor "Yellow"
    Write-Host "  1. 配置ECS安全组，开放端口 2881"
    Write-Host "  2. 安装MySQL客户端以连接数据库"
    Write-Host "  3. 配置 .env 文件中的数据库连接信息"
    Write-Host "  4. 执行数据库初始化脚本"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor "Cyan"
}

# 主函数
function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor "Cyan"
    Write-Host "SeekDB 自动部署脚本 (Windows)" -ForegroundColor "Green"
    Write-Host "========================================" -ForegroundColor "Cyan"
    Write-Host ""

    # 检查管理员权限
    Check-Admin

    # 检查Docker
    if (-not (Check-Docker)) {
        Write-Error "请先安装并启动Docker Desktop"
        exit 1
    }

    # 等待Docker就绪
    if (-not (Wait-Docker)) {
        exit 1
    }

    # 创建目录
    Create-Directories

    # 配置SeekDB
    Configure-SeekDB

    # 拉取镜像
    if (-not (Pull-SeekDBImage)) {
        exit 1
    }

    # 启动容器
    if (-not (Start-SeekDB)) {
        exit 1
    }

    # 验证状态
    if (-not (Verify-SeekDB)) {
        exit 1
    }

    # 配置防火墙
    Configure-Firewall

    # 显示部署信息
    Show-DeploymentInfo
}

# 执行主函数
try {
    Main
}
catch {
    Write-Error "部署过程中发生错误: $_"
    Write-Host $_.ScriptStackTrace
    exit 1
}
