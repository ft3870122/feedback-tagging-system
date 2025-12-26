# 客服反馈自动打标系统

基于SeekDB + Coze Agent的智能客服反馈自动打标系统，实现动态实体识别、自动打标、闭环优化和AI分析总结。

## 项目架构

![系统架构图](https://p3-flow-imagex-sign.byteimg.com/tos-cn-i-a9rns2rl98/b8a9e737ffb343bbada335b547b366b3.png~tplv-a9rns2rl98-image.png?rcl=202512261537438704FE9B01E85643964F&rk3s=8e244e95&rrcfp=dafada99&x-expires=2082958663&x-signature=2Vp8IFewL%2F89Nu%2F612LRLROzUWY%3D)

### 核心组件

1. **SeekDB数据库**：存储反馈数据、实体标签、向量索引
2. **Coze智能Agent**：低置信度场景下的实体识别兜底
3. **自动打标模块**：SeekDB混合检索匹配+Coze兜底识别
4. **分析总结模块**：统计打标结果，生成业务洞察

## 快速开始

### 环境要求

- Ubuntu 22.04 LTS
- Python 3.8+
- SeekDB 最新版本
- Coze Agent API 访问权限

### 安装部署

1. **系统依赖安装**

```bash
# 更新系统
apt update && apt upgrade -y

# 安装必要工具
apt install -y python3 python3-pip python3-venv git
```

2. **SeekDB 安装**

```bash
# 创建SeekDB安装目录
mkdir -p /opt/seekdb && cd /opt/seekdb

# 下载SeekDB（替换为最新版本）
wget https://www.seekdb.com/download/seekdb-linux-amd64-latest.tar.gz

# 解压
tar -zxvf seekdb-linux-amd64-latest.tar.gz

# 启动SeekDB（后台运行）
nohup ./seekdb server --port 2881 --data-dir /opt/seekdb/data &
```

3. **项目部署**

```bash
# 克隆项目
git clone https://github.com/your-username/feedback-tagging-system.git
cd feedback-tagging-system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填写SeekDB和Coze配置
```

4. **数据库初始化**

在SeekDB控制台执行 `sql/init_schema.sql` 中的SQL语句，初始化数据库表结构。

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
```

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

```bash
# 检查SeekDB状态
curl http://localhost:2881/health

# 检查脚本运行状态
ps aux | grep python
```

## 故障排查

### 常见问题

1. **SeekDB启动失败**
   - 检查端口占用：`netstat -tulpn | grep 2881`
   - 检查数据目录权限：`chmod 777 /opt/seekdb/data`

2. **Coze调用失败**
   - 检查API Key是否正确
   - 确认Coze Agent已发布并开启API调用

3. **打标无结果**
   - 检查SeekDB向量索引是否创建成功
   - 验证反馈文本格式是否正确

## 许可证

MIT License