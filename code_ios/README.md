# 智能面试助手 iOS 轻量版

这是一个 SwiftUI iOS 客户端，所有 AI 能力通过文字对话调用后端统一入口：

- 登录：`POST /api/admin/auth/login`
- 注册：`POST /api/admin/auth/register`
- Token 校验：`GET /api/admin/auth/me`
- 智能助手：`POST /api/assistant/chat`

## 功能范围

- 登录 / 注册 / 退出登录
- Keychain 保存 Token，并在启动或“我的”页面校验 Token
- 首页 Agent 快捷入口：简历评估、模拟面试、求职信、职业规划、谈薪助手、邮件润色
- 统一文字对话页
- 本地历史记录，保存生成过的报告和对话
- 我的页面，展示账号和基础设置

本版本不包含文件上传、音频上传、管理员后台、知识库管理、录音审核入库、SMTP 群发、复杂数据看板、PDF/DOCX 导出。

## 打开方式

用 Xcode 打开：

```bash
open code_ios/AIInterviewLite.xcodeproj
```

默认后端地址是：

```text
http://127.0.0.1:8000
```

iOS 端按要求使用固定默认地址，登录页和“我的”页不展示该端点，也不提供用户编辑入口。若需要真机访问 Mac 后端，请在 `AIInterviewLite/AppSettings.swift` 中调整默认值后重新构建。

## 后端兼容

为支持轻量版纯文本输入，后端 `/api/assistant/chat` 已兼容：

- 简历评估：无 `file_id` 时将用户消息作为简历文本
- 面试题生成：无 `file_id` 时将用户消息作为简历/岗位/项目文本
- 面试对话分析：无音频文件时读取粘贴的面试对话文本

旧的文件上传和音频分析流程仍保留。
