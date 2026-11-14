# 文脉前端

完整工作台在仓库根目录运行 `python start.py`。[快速开始](../README.md#快速开始)

## 本地开发

需要 Node.js 22+。在 `frontend/` 执行以下命令。

```powershell
npm ci
npm run dev
```

开发服务器默认使用 `http://localhost:5173`，并将 `/api` 请求转发到本机 `8000` 端口。联调时先启动后端。[后端启动说明](../backend/README.md#单独运行)

## 测试与构建

```powershell
npm test
npm run build
```
