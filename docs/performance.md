# MusicStream 性能优化指南

## 目录

1. [Uvicorn 参数优化](#uvicorn-参数优化)
2. [数据库优化](#数据库优化)
3. [文件系统优化](#文件系统优化)
4. [缓存策略](#缓存策略)
5. [网络优化](#网络优化)
6. [监控指标](#监控指标)

## Uvicorn 参数优化

### 推荐配置 (10-100 并发)

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http h11 \
    --limit-concurrency 100 \
    --backlog 2048 \
    --timeout-keep-alive 5 \
    --access-log
```

### 参数说明

| 参数 | 说明 | 建议值 |
|-----|------|--------|
| `--workers` | 工作进程数 | CPU 核数 |
| `--loop` | 事件循环 | uvloop (Linux) |
| `--limit-concurrency` | 最大并发 | 50-100 |
| `--backlog` | 连接队列 | 2048 |
| `--timeout-keep-alive` | 长连接超时 | 5秒 |

## 数据库优化

### SQLite 优化

```python
# 在 database.py 中添加
engine = create_async_engine(
    database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    pool_pre_ping=True,
)

# WAL 模式（提高并发）
# 在数据库初始化后执行
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  # 64MB 缓存
```

### 索引建议

已在 Alembic 迁移中创建的索引：
- `ix_tracks_path` - 路径索引
- `ix_tracks_title` - 标题索引
- `ix_tracks_artist` - 艺术家索引
- `ix_tracks_album` - 专辑索引
- `ix_events_timestamp` - 事件时间索引

## 文件系统优化

### 流式读取

```python
# 使用较大的块大小
CHUNK_SIZE = 512 * 1024  # 512KB

async def stream_file(path, start, end):
    async with aiofiles.open(path, 'rb') as f:
        await f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = await f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
```

### 封面缓存

- 生成多尺寸缩略图 (sm/md/lg)
- 使用 ETag 和 Cache-Control
- 推荐缓存时间: 7 天

## 缓存策略

### HTTP 缓存头

| 资源类型 | Cache-Control |
|---------|---------------|
| 音频流 | `public, max-age=86400` |
| 封面图 | `public, max-age=604800, immutable` |
| 歌词 | `public, max-age=3600` |
| Router 响应 | `no-cache` |

### 前端缓存

- 使用 localStorage 存储令牌
- 使用 Pinia 持久化用户偏好
- 封面 URL 添加版本参数

## 网络优化

### Nginx 配置

```nginx
# 启用 gzip
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;

# 启用 sendfile
sendfile on;
tcp_nopush on;
tcp_nodelay on;

# 连接复用
keepalive_timeout 65;
keepalive_requests 1000;
```

### HTTP/2 (可选)

在 HTTPS 环境下启用 HTTP/2 以提升性能。

## 监控指标

### 关键指标

1. **响应时间**: P50 < 100ms, P99 < 500ms
2. **并发连接**: 监控活跃连接数
3. **内存使用**: 每个 worker 约 100-200MB
4. **CPU 使用**: 空闲时 < 5%

### 健康检查

```bash
# 简单健康检查
curl -w "%{time_total}s\n" http://localhost:8000/healthz

# 压力测试
wrk -t4 -c100 -d30s http://localhost:8000/api/tracks
```