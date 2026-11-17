# 智能面试助手 Harmony 轻量用户版

该目录是一个 Stage 模型 HarmonyOS ArkTS 项目，入口模块为 `entry`。

## 功能范围

- 登录 / 注册 / 退出登录
- Token 与账号信息本地保存，启动和“我的”页支持 `/api/admin/auth/me` 校验
- 首页 Agent 快捷入口：简历评估、模拟面试、求职信、职业规划、谈薪助手、邮件润色
- 统一智能助手对话页，调用 `/api/assistant/chat`
- 本地历史记录，保存用户生成过的报告和对话
- 我的页面展示账号信息、自动保存历史设置

本版本不包含文件上传、音频上传、管理员后台、知识库管理、录音审核入库、SMTP 群发、复杂看板、PDF/DOCX 导出。

## UI 参考

参考 Tuniao UI 与 uView Pro 风格，在 `entry/src/main/ets/components/TnLiteControls.ets` 内实现了轻量自包含控件：

- `TnLiteButton`：胶囊按钮、渐变按钮、朴素按钮、loading/disabled 状态
- `TnLiteInput` / `TnLiteTextArea`：圆角输入框、文本域、字数统计
- `TnLiteTag`：轻量标签
- `AgentGradientCard`：双列渐变快捷卡片
- `GlassBottomTab`：毛玻璃底部导航
- `TnLiteEmpty`：空状态

这样不依赖参考工程的绝对路径，拷贝 `code_harmony` 后仍可独立打开。

## 后端地址

Harmony 端会在 Hvigor 构建时自动执行：

```bash
node scripts/update-backend-config.mjs
```

脚本会读取电脑当前局域网 IPv4，并写入：

```text
entry/src/main/ets/services/GeneratedConfig.ets
```

默认后端地址会自动生成，例如：

```text
http://192.168.1.10:8000
```

客户端登录页和“我的”页不展示该地址，也不提供手动设置入口。真机或模拟器调试时不要使用 `127.0.0.1` / `localhost`，它们会指向手机或模拟器自身。

需要覆盖自动检测结果时，可在构建前设置：

```bash
export AI_INTERVIEW_BACKEND_URL=http://你的电脑IP:8000
```

后端需要监听所有网卡：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 后端接口

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/register`
- `GET /api/admin/auth/me`
- `POST /api/assistant/chat`

后端已支持轻量版纯文本输入：简历评估、面试题生成和粘贴面试对话分析可不传 `file_id`。
