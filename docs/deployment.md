# MusicStream 部署指南

## 目录

1. [系统要求](#系统要求)
2. [快速部署](#快速部署)
3. [生产环境部署](#生产环境部署)
4. [反向代理配置](#反向代理配置)
5. [SSL/HTTPS 配置](#sslhttps-配置)
6. [备份与恢复](#备份与恢复)
7. [监控与日志](#监控与日志)

## 系统要求

### 硬件要求
- CPU: 双核及以上
- 内存: 2GB+ (建议 4GB)
- 存储: 根据媒体库大小，建议 SSD

### 软件要求
- Python 3.10+
- Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) 或 Windows 10+
- Nginx/Caddy (可选，反向代理)

## 快速部署

### Linux

```bash
# 1. 克隆项目
git clone <repository> /opt/musicstream
cd /opt/musicstream

# 2. 运行安装脚本
sudo bash scripts/install.sh

# 3. 创建管理员
sudo -u musicstream /opt/musicstream/backend/venv/bin/python scripts/create_admin.py

# 4. 启动服务
sudo systemctl start musicstream
sudo systemctl status musicstream
```

### Windows

```batch
# 1. 解压项目到任意目录

# 2. 运行安装脚本
scripts\setup_windows.bat

# 3. 创建管理员
scripts\create_admin.bat

# 4. 启动服务
scripts\start_windows.bat
```

## 生产环境部署

### Uvicorn 参数建议

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \          # CPU 核心数
    --loop uvloop \        # 高性能事件循环
    --http h11 \           # HTTP/1.1
    --limit-concurrency 100 \
    --backlog 2048 \
    --access-log \
    --log-level warning
```

### 并发能力估算

| 并发用户 | Workers | 内存需求 | CPU 需求 |
|---------|---------|----------|----------|
| 10-30   | 1       | 512MB    | 1 核     |
| 30-50   | 2       | 1GB      | 2 核     |
| 50-100  | 2-4     | 2GB      | 2-4 核   |

## 反向代理配置

### Nginx

参考 `scripts/nginx.conf.example`

### Caddy

参考 `scripts/caddy.example`

## SSL/HTTPS 配置

### 局域网自签名证书

```bash
# 生成自签名证书（10年有效期）
openssl req -x509 -nodes -days 3650 \
    -newkey rsa:2048 \
    -keyout /etc/ssl/private/musicstream.key \
    -out /etc/ssl/certs/musicstream.crt \
    -subj "/CN=music.local"
```

### Let's Encrypt (公网)

使用 Caddy 自动获取证书，或使用 certbot。

## 备份与恢复

### 自动备份 (Cron)

```bash
# 每天凌晨 3 点备份
0 3 * * * /opt/musicstream/scripts/backup.sh >> /var/log/musicstream-backup.log 2>&1
```

### 手动恢复

```bash
bash scripts/restore.sh /path/to/backup.tar.gz
```

## 监控与日志

### 查看日志

```bash
# systemd 日志
sudo journalctl -u musicstream -f

# 应用日志
tail -f /opt/musicstream/backend/logs/app.log
```

### 健康检查

```bash
curl http://localhost:8000/healthz
```

### Prometheus 监控 (可选)

可添加 `prometheus-fastapi-instrumentator` 扩展。

