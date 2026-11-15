# Harmony Android 轻量用户版

这是“智能面试助手 Harmony”的 Android 轻量客户端。所有核心 AI 能力均通过文字对话调用现有后端，默认统一入口为：

- 登录：`POST /api/admin/auth/login`
- 注册：`POST /api/admin/auth/register`
- Token 校验：`GET /api/admin/auth/me`
- 智能助手：`POST /api/assistant/chat`

## 功能范围

- 登录 / 注册 / 退出登录
- 本地保存 Token，并在启动和“我的”页校验 Token
- 首页 Agent 快捷入口：简历评估、模拟面试、求职信、职业规划、谈薪助手、邮件润色
- 统一智能助手文字对话页
- 本地历史记录，保存生成过的报告和对话
- “我的”页展示账号信息、自动保存历史等基础设置

本版本不包含文件上传、音频上传、管理员后台、知识库管理、录音审核入库、SMTP 群发、复杂数据看板、PDF/DOCX 导出。

## 后端地址

Android 端不在 App 内展示或编辑后端地址。默认地址由脚本自动生成：

```bash
./scripts/update-backend-config.sh
```

脚本会自动判断目标：

- 当前有 Android 模拟器运行时，生成 `http://10.0.2.2:8000`
- 真机调试时，生成当前电脑的 Wi-Fi/默认网卡 IP，例如 `http://192.168.x.x:8000`

生成结果会写入：

```text
app/src/main/java/com/harmony/interviewlite/data/GeneratedConfig.kt
```

默认端口为 `8000`。如需改端口，可在运行脚本时设置环境变量：

```bash
BACKEND_PORT=9000 ./scripts/update-backend-config.sh
```

如需强制指定目标类型：

```bash
ANDROID_TARGET=emulator ./scripts/update-backend-config.sh
ANDROID_TARGET=device ./scripts/update-backend-config.sh
```

如果没有检测到本机 IP，脚本会回退到 Android 模拟器访问宿主机的 `http://10.0.2.2:8000`。后端需允许 HTTP 明文访问；本工程已在 `AndroidManifest.xml` 中启用 `usesCleartextTraffic`。

## 打开与构建

用 Android Studio 打开 `code_android` 目录，或在该目录执行：

```bash
./gradlew assembleDebug
```

构建前 Gradle 会自动执行 `./scripts/update-backend-config.sh`。后端服务启动后即可登录或注册账号，所有 Agent 入口会预填对应文字模板并发送到 `/api/assistant/chat`。
