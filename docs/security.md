```markdown
# MusicStream 安全指南

## 目录

1. [认证安全](#认证安全)
2. [Router 安全](#api-安全)
3. [文件安全](#文件安全)
4. [网络安全](#网络安全)
5. [安全检查清单](#安全检查清单)

## 认证安全

### JWT 配置

```env
# 生产环境必须更改
JWT_SECRET=<至少32位随机字符串>
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7
```

### 密码策略

- 最小长度: 6 字符
- 必须包含数字
- 使用 bcrypt 哈希 (cost=12)

### 登录限流

- IP 限制: 5 次/分钟
- 账户限制: 5 次/分钟
- 超过限制返回 429

## Router 安全

### CORS 配置

```env
# 严格限制允许的源
FRONTEND_ORIGIN=http://localhost:5500
```

### 安全响应头

```python
# 自动添加的安全头
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### 输入验证

- 使用 Pydantic 模型验证
- 限制字符串最大长度
- 验证枚举值范围

## 文件安全

### 路径穿越防护

```python
# PathUtils.is_safe_path() 检查
- 解析绝对路径
- 验证在 MEDIA_DIR 内
- 拒绝符号链接逃逸
- 拒绝 .. 路径
```

### 文件类型限制

只允许以下扩展名:
- `.mp3`, `.flac`, `.m4a`, `.mp4`
- `.ogg`, `.opus`, `.wav`, `.wma`, `.aac`

## 网络安全

### 防火墙建议

```bash
# 仅允许必要端口
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
```

### HTTPS (推荐)

即使在局域网环境，HTTPS 也能防止:
- 中间人攻击
- 数据窃听
- 会话劫持

## 安全检查清单

### 部署前

- [ ] 更改默认 JWT_SECRET
- [ ] 设置强管理员密码
- [ ] 配置 CORS 白名单
- [ ] 禁用调试模式 (DEBUG=false)
- [ ] 检查文件权限

### 运行时

- [ ] 监控失败登录尝试
- [ ] 定期检查日志
- [ ] 定期更新依赖
- [ ] 定期备份数据

### 审计项目

- [ ] 限流正常工作
- [ ] 路径穿越防护有效
- [ ] 认证正确实施
- [ ] 日志不包含敏感信息