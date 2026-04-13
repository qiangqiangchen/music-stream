# MusicStream - 局域网音乐流媒体

一个功能完整的局域网音乐流媒体 Web 应用，支持在线播放、歌词同步、播放列表管理等功能。

## 功能特性

- 🎵 **音乐播放**：支持 MP3、FLAC、M4A、OGG、WAV 等格式
- 📝 **歌词支持**：外部 LRC 文件、内嵌歌词（USLT/SYLT），支持同步显示和偏移调整
- 📚 **媒体库管理**：自动扫描、元数据提取、封面缓存
- 🔐 **用户认证**：JWT 认证，支持用户/管理员角色
- 📊 **数据分析**：播放统计、下载统计、用户活跃度
- 📱 **响应式设计**：支持桌面和移动端浏览器

## 技术栈

### 后端
- Python 3.11+
- FastAPI + Uvicorn
- SQLModel + SQLite（可切换 PostgreSQL）
- JWT 认证
- mutagen（音频元数据）

### 前端
- Vue 3（CDN ESM）
- Pinia 状态管理
- Vue Router
- Bootstrap 5
- HTML5 Audio Router

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd music-stream
```

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 编辑 .env 配置（特别是 MEDIA_DIR 和 JWT_SECRET）

# 初始化数据库和种子数据
python ../scripts/seed_data.py

# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 前端设置

```bash
# 新开一个终端
cd frontend

# 使用 Python 内置服务器
python -m http.server 5500

# 或使用 Node.js 服务器
# npx serve -l 5500
```

### 4. 访问应用

- 前端：http://localhost:5500
- 后端 Router：http://localhost:8000
- Router 文档：http://localhost:8000/docs

### 默认管理员账户

- 邮箱：admin@localhost
- 密码：admin123

## 目录结构

```
music-stream/
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码
│   ├── alembic/      # 数据库迁移
│   ├── tests/        # 测试
│   └── data/         # SQLite 数据库
├── frontend/         # Vue 3 前端
│   ├── js/           # JavaScript 模块
│   └── css/          # 样式文件
├── scripts/          # 运维脚本
└── media/            # 媒体文件目录
```

## 配置说明

编辑 `backend/.env` 文件：

```env
# 媒体目录（放置音乐文件的位置）
MEDIA_DIR=../media

# JWT 密钥（生产环境请更换）
JWT_SECRET=your-secret-key

# 前端地址（CORS 白名单）
FRONTEND_ORIGIN=http://localhost:5500
```

## 添加音乐

1. 将音乐文件放入 `media/` 目录
2. 登录管理员账户
3. 点击右上角菜单 -> "扫描媒体库"

## Router 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 测试

```bash
cd backend
pytest
```

## 部署

### 使用 systemd（Linux）

```bash
sudo cp scripts/musicstream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable musicstream
sudo systemctl start musicstream
```

### 使用 Nginx 反向代理

参考 `scripts/nginx.conf.example`

## 许可证

MIT License


---

### Day 1 验收清单

```markdown
## Day 1 验收清单

### 后端功能
- [x] 项目结构完整（api/schemas/services/repositories/core）
- [x] SQLModel 数据模型定义
- [x] Alembic 迁移配置
- [x] JWT 认证（注册/登录/刷新/当前用户）
- [x] CORS 配置（仅允许前端 Origin）
- [x] 媒体扫描服务（mutagen 读取标签/封面/歌词）
- [x] 流媒体端点（Range/206、HEAD 支持）
- [x] 歌词服务（外部 LRC、USLT 解析）
- [x] 歌词接口（/lyrics/{track_id}?format=lrc|json）
- [x] 埋点事件（play_start、play_end）
- [x] 路径安全检查

### 前端功能
- [x] Vue 3 CDN 版本配置
- [x] Pinia 状态管理
- [x] Vue Router 路由
- [x] 登录/注册页面
- [x] 曲目列表页面
- [x] 播放器组件（播放/暂停/上一曲/下一曲/进度/音量）
- [x] 歌词面板（同步高亮、偏移调整）
- [x] 封面显示

### 文档和测试
- [x] README 文档
- [x] .env 示例文件
- [x] 管理员创建脚本
- [x] 种子数据脚本
- [x] 启动脚本（Linux/Windows）
- [x] 认证测试
- [x] 歌词解析测试
- [x] 流媒体测试

### 验证步骤
1. 启动后端：`cd backend && uvicorn app.main:app --reload`
2. 启动前端：`cd frontend && python -m http.server 5500`
3. 访问 http://localhost:5500
4. 使用 admin@localhost / admin123 登录
5. 放入音乐文件，执行扫描
6. 播放音乐，验证歌词显示

--- 

# MusicStream - 局域网音乐流媒体

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.4-brightgreen.svg" alt="Vue">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

一个功能完整的局域网音乐流媒体 Web 应用，支持在线播放、歌词同步、播放列表管理等功能。

## ✨ 功能特性

- 🎵 **音乐播放** - 支持 MP3、FLAC、M4A、OGG、WAV 等格式
- 📝 **歌词同步** - 外部 LRC、内嵌歌词 (USLT/SYLT)，支持偏移调整
- 📚 **媒体管理** - 自动扫描、元数据提取、封面缓存
- 🔐 **用户系统** - JWT 认证，用户/管理员角色
- 📊 **数据分析** - 播放统计、趋势图表、用户活跃度
- 📱 **响应式设计** - 支持桌面和移动端

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 现代浏览器

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd music-stream

# 后端设置
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置

# 初始化
python ../scripts/seed_data.py

# 启动后端
uvicorn app.main:app --reload

# 新终端，启动前端
cd frontend
python -m http.server 5500
```

### 访问

- 前端: http://localhost:5500
- Router: http://localhost:8000
- 文档: http://localhost:8000/docs

### 默认账户

- 邮箱: `admin@localhost`
- 密码: `admin123`

## 📖 文档

- [部署指南](docs/deployment.md)
- [性能优化](docs/performance.md)
- [安全指南](docs/security.md)
- [项目总结](docs/SUMMARY.md)

## 🏗️ 技术栈

**后端**
- FastAPI + Uvicorn
- SQLModel + SQLite
- JWT + bcrypt
- mutagen + Pillow

**前端**
- Vue 3 (CDN)
- Pinia + Vue Router
- Bootstrap 5
- Chart.js

## 📁 项目结构

```
music-stream/
├── backend/          # FastAPI 后端
├── frontend/         # Vue 3 前端
├── scripts/          # 运维脚本
├── docs/             # 文档
└── media/            # 媒体目录
```

## 🔧 配置

编辑 `backend/.env`:

```env
MEDIA_DIR=../media              # 媒体目录
JWT_SECRET=your-secret-key      # JWT 密钥
FRONTEND_ORIGIN=http://localhost:5500  # 前端地址
```

## 📊 并发支持

| 并发用户 | Workers | 内存需求 |
|---------|---------|----------|
| 10-30   | 1       | 512MB    |
| 30-50   | 2       | 1GB      |
| 50-100  | 2-4     | 2GB      |

## 🧪 测试

```bash
cd backend
pytest
```

## 📝 许可证

[MIT License](LICENSE)