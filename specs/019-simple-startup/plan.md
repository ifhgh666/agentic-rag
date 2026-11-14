# Implementation Plan: 019 简化本地启动

**Branch** 当前工作分支 · **Date** 2026-11-14 · [规格](spec.md)

## Summary

阶段 A 提供仓库根目录的单命令启动器。启动器初始化缺失的配置、准备依赖并运行前后端。专用后端入口设置本地固定演示登录，复用现有 FastAPI 应用和鉴权。

## Technical Context

Python 3.11+、Node.js 22+、Uvicorn 和 Vite。模型使用已有提供方，示例预设 OpenAI 兼容接口。Dense 模型使用 fastembed 的本地缓存。Python 依赖保存在项目虚拟环境。Windows Conda 使用当前解释器和项目隔离依赖目录，保留可用的 DLL 加载路径。前端依赖由现有锁文件管理。

## Constitution Check

改动限于阶段 A 的本地开发入口和文档。固定账号仅用于监听本机的专用入口，密码在启动时哈希，JWT 密钥在进程内生成。保留既有配置、索引和认证契约。隔离测试使用合成数据，真实模型调用不属于启动验证。

## Project Structure

- `start.py` 准备配置、依赖及前后端进程。
- `backend/scripts/start_local.py` 配置本地登录、准备嵌入模型并启动现有应用。
- `backend/.env.example` 和 `README.md` 提供新的快速开始路径。
- [调研](research.md)、[状态](data-model.md)、[启动契约](contracts/startup.md)和[验证说明](quickstart.md)。
