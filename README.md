# 智能面试助手

这个助手可以帮求职者检查简历、练习面试、复盘录音，也能准备求职信、投递邮件和谈薪方案。网页和三个手机端共用一个 FastAPI 后端。

## 团队与版本记录

仓库维护账号为 [Yan-c-c](https://github.com/Yan-c-c)。

现有源码按功能分成 53 次提交。9 月 2 日到 11 月 17 日的日期和时间是整理代码时补写的，原始开发时间已无法通过 Git 核实。

## 助手分工


- `ResumeEvaluationAgent`：DeepSeek 多专家圆桌会议简历评估。
- `InterviewQuestionGenerationAgent`：基于简历画像、面试知识库和 DeepSeek 的模拟面试。
- `InterviewAudioAnalysisAgent`：基于百度音频文件转写、DeepSeek、面试知识库和百度 AI 搜索的面试录音分析。
- `CoverLetterAgent`：基于简历画像、目标公司、目标岗位和 JD 生成多版本个性化求职信。
- `CareerPlanningAgent`：基于简历/个人背景、职业目标和偏好生成学习路径、项目补强与投递策略。
- `EmailCampaignAgent`：支持用户自填 SMTP、多收件人管理、DeepSeek 生成/润色邮件、附件、预览确认和群发记录。

- SalaryNegotiationAgent 根据演示数据估算薪资区间，模拟报价并给出沟通建议。

## 当前功能

- 上传文件：支持 PDF、DOCX、TXT、MD，以及 MP3、WAV、M4A、AMR、PCM、FLAC、AAC、OGG 等音频。
- 统一助手接口：`POST /api/assistant/chat`。
- 简历评估：保留“多专家圆桌会议 / Reflector 整合”机制。
- 模拟面试：简历画像提取、知识库检索、个性化提问、语音/文字回答和面试报告。
- 面试知识库：文档管理、题库检索、知识图谱查看，底层适配 LightRAG 能力。
- 面试录音分析：录音转写、话者识别、问答切分、正确答案生成、回答准确性评估、讲师快速审核和审核通过后自动入库。
- 求职信生成：DeepSeek 生成标准版、邮件精简版、技术岗位版、校招/实习版，支持改写、导出和邮件发送/草稿。
- 职业规划：DeepSeek 分析能力画像、岗位匹配、短中长期计划、学习路径、项目补强和投递策略，支持改写和导出。
- 邮件群发：用户配置自己的 SMTP，添加多个 HR 收件人，DeepSeek 生成或润色求职邮件，支持变量、附件、预览确认和逐封发送状态记录。

## 整体架构

```text
自然语言 + 文件上传
        ↓
IntentRouter 识别意图
        ↓
AgentDispatcher 调度 Agent
        ↓
简历评估 / 模拟面试 / 录音分析 / 求职信 / 职业规划 / 邮件群发 / 谈薪模拟
        ↓
DeepSeek + 本地工具 + 面试知识库 + 百度能力
        ↓
结构化 JSON
        ↓
前端 iOS 风格工作台展示
```

## 面试录音分析流程

`InterviewAudioAnalysisAgent` 位于 `backend/app/agents/interview_audio_agent.py`。

1. 用户上传面试录音并发送“请分析这段面试录音”。
2. 后端调用百度智能云音频文件转写异步任务接口，配置 `pid=8953` 开启话者分离。
3. 转写结果保留原始文本、时间戳、speaker 标识和原始结果。
4. DeepSeek 判断每个 speaker 是面试官还是面试者。
5. DeepSeek 切分出“面试官问题 + 面试者回答”。
6. 每道题优先通过 `KnowledgeBaseService` 检索本地面试宝典和真实题库。
7. 本地知识库不足时调用百度 AI 搜索补充互联网公开答案。
8. 如果仍无可靠证据，DeepSeek 兜底生成参考答案，并标记 `deepseek_generated`。
9. DeepSeek 综合学生回答、题库证据、百度 AI 搜索结果和兜底知识，生成标准答案、评分依据和改进建议。
10. 前端进入讲师快速审核界面，支持播放音频、查看转写、编辑题目和标准答案。
11. 审核通过后，系统将真实面试题和 AI 综合答案写入面试知识库，供后续模拟面试检索。

注意：面试录音分析不复用模拟面试的实时短语音识别接口，必须使用百度音频文件转写异步 API。

## 关键后端模块

- `backend/app/agents/interview_audio_agent.py`
- `backend/app/services/baidu_asr_client.py`
- `backend/app/services/audio_transcription_service.py`
- `backend/app/services/baidu_ai_search_client.py`
- `backend/app/services/public_answer_search_service.py`
- `backend/app/services/audio_review_service.py`
- `backend/app/services/knowledge_base/knowledge_base_service.py`
- `backend/app/api/interview_audio.py`
- `backend/app/api/audio_review.py`

## 关键前端模块

- `web/components/AssistantChat.tsx`
- `web/components/InterviewAudioReviewPanel.tsx`
- `web/components/KnowledgeBasePanel.tsx`
- `web/lib/api/interviewAudio.ts`
- `web/lib/api/knowledgeBase.ts`

## 邮件群发 Agent

`EmailCampaignAgent` 位于 `backend/app/agents/email_campaign_agent.py`。

1. 用户输入“帮我群发求职邮件 / 批量发送求职信 / 给这些 HR 发邮件”。
2. `IntentRouter` 识别为 `email_campaign`，`AgentDispatcher` 打开邮件群发工作台。
3. 用户在前端填写自己的 SMTP 配置，授权码只在测试连接和发送请求中使用，不写入任务历史。
4. 用户手动添加或批量粘贴多个收件人，系统做邮箱格式校验和去重。
5. 邮件正文可手写，也可调用 DeepSeek 结合简历、目标岗位和用途生成，并支持一键润色。
6. 支持 `{{name}}`、`{{company}}`、`{{position}}` 变量，发送前逐封渲染预览。
7. 支持上传简历、求职信或其他 PDF/DOCX/TXT/MD 附件。
8. 群发前必须生成预览并确认，发送后记录每个收件人的 `pending / sending / success / failed / skipped` 状态和失败原因。

关键文件：

- `backend/app/services/email_campaign_service.py`
- `backend/app/services/email_content_service.py`
- `backend/app/services/smtp_service.py`
- `backend/app/api/email_campaign.py`
- `web/components/EmailCampaignPanel.tsx`
- `web/lib/api/emailCampaign.ts`

## 常用接口

- `POST /api/upload`
- `POST /api/assistant/chat`
- `POST /api/resume/evaluate`
- `POST /api/interview-question/generate`
- `POST /api/interview-audio/analyze`
- `GET /api/interview-audio/{task_id}`
- `POST /api/audio-review/{task_id}/approve`
- `POST /api/audio-review/{task_id}/reject`
- `POST /api/audio-review/{task_id}/update`
- `GET /api/knowledge-base/status`
- `POST /api/knowledge-base/query`
- `POST /api/knowledge-base/documents/text`
- `GET /api/knowledge-base/graph`
- `POST /api/cover-letter/generate`
- `POST /api/cover-letter/rewrite`
- `POST /api/cover-letter/export`
- `POST /api/cover-letter/send-email`
- `GET /api/cover-letter/history`
- `POST /api/career-planning/generate`
- `POST /api/career-planning/rewrite`
- `POST /api/career-planning/export`
- `GET /api/career-planning/history`
- `POST /api/email-campaign/test-smtp`
- `POST /api/email-campaign/generate-content`
- `POST /api/email-campaign/polish-content`
- `POST /api/email-campaign/create`
- `POST /api/email-campaign/send`
- `GET /api/email-campaign/{task_id}`
- `GET /api/email-campaign/history`

## 环境变量

DeepSeek / OpenAI 兼容配置：

```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=
OPENAI_BASE_URL=
SMART_MODEL=
FAST_MODEL=
```

面试知识库 / RAG 配置：

```bash
LIGHTRAG_BASE_URL=http://127.0.0.1:9621
LIGHTRAG_API_KEY=
LIGHTRAG_QUERY_MODE=mix
LIGHTRAG_TOP_K=8
LIGHTRAG_CHUNK_TOP_K=8
LIGHTRAG_TIMEOUT_SECONDS=8
LIGHTRAG_INPUT_DIR=./data/interview_kb/inputs
LIGHTRAG_WORKING_DIR=./data/interview_kb/rag_storage
```

百度音频文件转写配置：

```bash
BAIDU_ASR_API_KEY=
BAIDU_ASR_SECRET_KEY=
BAIDU_ASR_BASE_URL=https://aip.baidubce.com
BAIDU_ASR_PID=8953
BAIDU_ASR_RATE=16000
BAIDU_ASR_FORMAT=mp3
BAIDU_ASR_POLL_INTERVAL_SECONDS=3
BAIDU_ASR_POLL_TIMEOUT_SECONDS=45
BAIDU_ASR_PUBLIC_AUDIO_BASE_URL=
```

`BAIDU_ASR_PUBLIC_AUDIO_BASE_URL` 需要配置为百度云可访问的后端公网地址；百度音频文件转写接口接收 `speech_url`，本地 localhost 音频无法被百度云拉取。

如果配置了阿里云 OSS，系统会在分析本地上传录音时自动把音频上传到 OSS，并使用带签名的临时下载 URL 调用百度音频文件转写 API：

```bash
ALIYUN_OSS_ACCESS_KEY_ID=
ALIYUN_OSS_ACCESS_KEY_SECRET=
ALIYUN_OSS_BUCKET=
ALIYUN_OSS_REGION=oss-cn-beijing
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_PREFIX=interview-audio/
ALIYUN_OSS_PUBLIC_READ=0
ALIYUN_OSS_SIGNED_URL_EXPIRES_SECONDS=7200
```

百度 AI 搜索配置：

```bash
BAIDU_AI_SEARCH_API_KEY=
BAIDU_AI_SEARCH_BASE_URL=https://qianfan.baidubce.com/v2/ai_search/chat/completions
BAIDU_AI_SEARCH_MODEL=ernie-4.5-turbo-32k
BAIDU_AI_SEARCH_SOURCE=baidu_search_v1
BAIDU_AI_SEARCH_MAX_RESULTS=5
BAIDU_AI_SEARCH_TIMEOUT_SECONDS=30
```

模拟面试实时语音和 TTS 配置：

```bash
BAIDU_SPEECH_APP_ID=
BAIDU_SPEECH_API_KEY=
BAIDU_SPEECH_SECRET_KEY=
```

邮件服务配置（求职信发送和邮件群发均可复用；邮件群发前端也支持用户临时覆盖 SMTP）：

```bash
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_SSL=1
SMTP_USE_TLS=0
```

如果未配置 SMTP，不影响求职信生成、职业规划、简历评估等能力。邮件群发可以在前端填写用户自己的 SMTP 配置后发送。

## 启动方式

后端建议使用 Python 3.11，网页使用 Node.js 20.9 或以上版本。在一个终端启动后端，在另一个终端启动网页。调用大模型、百度语音和邮件服务时需填写相应的凭据。LightRAG 是可选服务，服务不可用时会走本地检索。新安装的本地题库为空，可在后台导入资料。

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
# 打开 .env 填入所用服务的配置，再运行下面两条命令
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

在首次使用前，可在后端 .env 中设置 ADMIN_DEFAULT_EMAIL 和 ADMIN_DEFAULT_PASSWORD 来创建初始管理员。ADMIN_AUTH_SECRET 可用 openssl rand -hex 32 在本机生成，固定该值可让登录会话跨进程和重启继续使用。

前端：

```bash
cd web
npm ci
npm run dev
```

默认访问：`http://localhost:3000`。

后端健康检查为 http://localhost:8000/health 。如需连接其他后端，可在 web/.env.local 中设置 NEXT_PUBLIC_API_URL。

手机端的安装和连接方式见 [iOS](code_ios/README.md)、[Android](code_android/README.md) 和 [HarmonyOS](code_harmony/README.md)。

## 常见问题

- 只上传文件未说明需求：助手会提示选择简历评估、模拟面试或面试录音分析。
- 百度音频文件转写失败：检查 API Key、Secret Key、`BAIDU_ASR_PUBLIC_AUDIO_BASE_URL` 或请求中的 `audio_url`。
- 面试知识库未命中：题目会降级为 DeepSeek 生成，并标记 `deepseek_generated`，不会伪造来源。
- 审核通过后未被外部 LightRAG 服务处理：系统仍会写入内嵌索引；如果需要外部服务处理，请确认 `LIGHTRAG_BASE_URL` 可用。

## 第三方声明

面试知识库底层适配 LightRAG 的存储格式、检索和图谱能力。相关 MIT License 声明见 `THIRD_PARTY_NOTICES.md`。业务前端不展示原项目品牌视觉。
