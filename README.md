# 医疗预问诊小程序 MVP / Medical Pre-visit Mini Program MVP

## 中文说明

### 项目简介

这是一个可本地运行、可演示的端到端 MVP：

- 前端：原生微信小程序
- 后端：Python Flask
- 数据库：SQLite 默认，本地零配置启动；生产可切换到 MySQL 兼容连接串
- AI：通过 `LLMService` 抽象外部模型提供方，当前支持 `mock` 和阿里云百炼 Bailian 的 OpenAI 兼容模式
- 部署目标：本地验证后可迁移到微信云托管

### 当前已完成能力

- 患者通过聊天界面输入症状
- 后端保存用户、问诊、消息、报告
- 紧急关键词命中时优先走本地高风险拦截，不调用模型
- 普通场景可调用 Qwen 生成预问诊辅助回复
- 可根据会话生成结构化预问诊报告
- 所有患者侧输出均包含免责声明，不作为最终诊断
- 小程序支持中英文界面切换
- 小程序切换语言后，后端聊天回复、报告内容、免责声明也会同步切换语言
- 聊天页支持“发送后即时落消息 + AI 思考中占位 + 失败回滚”
- 报告页支持“返回继续问诊 / 重新生成报告 / 开始新问诊”

### 目录结构

```text
.
├─ backend/                 # Flask 后端
├─ miniprogram/             # 微信小程序前端
├─ requirements.txt
└─ README.md
```

### 后端接口

- `GET /`
- `GET /api/health`
- `POST /api/auth/wx-login`
- `POST /api/chat`
- `GET /api/consultations/<id>/messages`
- `POST /api/report/generate`
- `GET /api/report/<consultation_id>`

统一返回格式：

```json
{
  "success": true,
  "code": "OK",
  "message": "OK",
  "data": {}
}
```

### 本地运行

#### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

#### 2. 配置环境变量

在项目根目录新建 `.env` 并按需填写。

本地最小可运行配置：

```env
FLASK_ENV=development
SECRET_KEY=replace-me
DATABASE_URL=sqlite:///pre_diagnosis.db
LOG_LEVEL=INFO

LLM_PROVIDER=mock
LLM_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
```

如果要接入阿里云百炼 Bailian：

```env
LLM_PROVIDER=qwen
LLM_API_KEY=YOUR_REAL_KEY_HERE
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
```

说明：

- 不要把真实密钥写入代码、README 或版本库
- `LLM_BASE_URL` 默认就是 Bailian 兼容模式地址
- 当前实现仍兼容旧变量名 `LLM_API_URL`，但建议统一使用 `LLM_BASE_URL`

#### 3. 启动后端

```bash
python backend/run.py
```

默认地址：

- 根路径：[http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- 健康检查：[http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

#### 4. 运行测试

```bash
python -m pytest backend/tests -q
```

### 无需微信 GUI 的本地接口测试

先启动后端，再用以下示例验证。

#### 1. 模拟登录

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/auth/wx-login" `
  -ContentType "application/json" `
  -Body '{"code":"local-test-code","nickname":"本地测试用户"}'

$userId = $login.data.user.id
$userId
```

#### 2. 中文 `/api/chat` 示例

```powershell
$chat = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/chat" `
  -ContentType "application/json" `
  -Body (@{
    user_id = $userId
    message = "我发烧两天，喉咙痛，还有一点咳嗽"
    locale = "zh-CN"
  } | ConvertTo-Json)

$chat
```

#### 3. 英文 `/api/chat` 示例

```powershell
$chatEn = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/chat" `
  -ContentType "application/json" `
  -Body (@{
    user_id = $userId
    message = "I have had a fever for two days and a sore throat"
    locale = "en-US"
  } | ConvertTo-Json)

$chatEn
```

#### 4. `/api/report/generate` 示例

```powershell
$consultationId = $chat.data.consultation_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/report/generate" `
  -ContentType "application/json" `
  -Body (@{
    consultation_id = $consultationId
    locale = "zh-CN"
  } | ConvertTo-Json)
```

### Qwen/Bailian 集成说明

当前 `LLMService` 使用原生 `requests` 调用 OpenAI 兼容接口，不增加额外 SDK 依赖。

- Provider 标识：`LLM_PROVIDER=qwen`
- Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- Chat 接口：`/chat/completions`
- 模型默认值：`qwen3.6-plus`

聊天回复：

- 高风险症状先走本地规则拦截
- 非高风险时才调用模型
- 模型超时时会自动重试 1 次
- 模型失败时自动降级到本地安全回复
- 聊天文本进入小程序前会去掉 Markdown 标记
- 支持按 `locale` 输出中英文内容

报告生成：

- 使用 `response_format={"type":"json_object"}`
- 提示词显式要求输出 `JSON`
- 安全解析响应
- 字段缺失时自动补安全默认值并记录 warning
- 解析失败时自动返回降级报告，不会导致接口崩溃
- 支持按 `locale` 输出中英文内容

### 微信小程序联调说明

使用微信开发者工具打开 `miniprogram/` 目录。

#### 1. 需要确认的本地配置

- [env.js](/d:/Users/Admin/Desktop/Wechat%20program/miniprogram/config/env.js) 中的 `baseURL`
- [project.config.json](/d:/Users/Admin/Desktop/Wechat%20program/miniprogram/project.config.json) 中的 `appid`

如果开发者工具不能访问 `127.0.0.1`，把 `baseURL` 改成你电脑的局域网 IP，例如：

```js
baseURL: 'http://192.168.1.10:5000'
```

#### 2. 开发者工具设置

- 本地调试时关闭或放开“合法域名校验”
- 修改配置后建议执行一次“清缓存并编译”

#### 3. 当前小程序交互

聊天页：

- 发送后用户消息立即入列
- 同时显示 `AI 正在思考` 占位
- 请求失败时会完整回滚到发送前状态
- 支持 `开始新问诊`
- 支持 `中 / EN` 切换
- 显示消息时间和发送状态

报告页：

- 展示结构化摘要字段
- 支持 `返回继续问诊`
- 支持 `重新生成报告`
- 支持 `开始新问诊`
- 支持 `中 / EN` 切换

#### 4. 推荐联调步骤

1. 启动后端
2. 打开微信开发者工具并导入 `miniprogram/`
3. 先验证 mock 登录
4. 发送一条普通症状，确认聊天回复正常
5. 测试一条高风险症状，确认本地拦截生效
6. 点击“生成医生摘要”，确认报告页正常
7. 切换到 `EN`，再测一条英文症状，确认前后端一起切换

### 安全边界

- 本产品是预问诊辅助工具，不是诊断系统
- 不输出最终诊断
- 保留本地紧急症状拦截，优先级高于任何模型调用
- 患者侧始终保留免责声明
- 高风险症状如胸痛、严重呼吸困难、失去意识、严重出血等会优先走本地升级路径

### 当前已知限制

- 登录仍是 stub，尚未接入真实微信 `code2Session`
- 英文模式下的真实模型输出质量仍取决于 Qwen 实际返回，不是完全固定模板
- 当前未加入数据库迁移工具，模型结构变更仍以 MVP 方式处理
- 前端仍以原生小程序为主，未接入更复杂的富文本渲染

### 已留出的 TODO

- `TODO: replace stubbed login with real WeChat code2Session flow.`
- `TODO_REPLACE_WITH_REAL_WECHAT_APPID`
- `TODO_REPLACE_WITH_REAL_MINIPROGRAM_APPID`
- 微信合法 request 域名配置
- 生产环境数据库与云托管部署参数

---

## English

### Overview

This is a locally runnable, demo-ready end-to-end MVP:

- Frontend: native WeChat Mini Program
- Backend: Python Flask
- Database: SQLite by default for zero-setup local development; can switch to a MySQL-compatible connection string in production
- AI: external LLM providers are abstracted behind `LLMService`; currently supports `mock` and Alibaba Cloud Bailian via the OpenAI-compatible API
- Deployment target: can be migrated to WeChat Cloud Hosting after local validation

### Implemented Features

- Patients can describe symptoms in a chat-style interface
- The backend stores users, consultations, messages, and reports
- Emergency keywords are intercepted locally before any model call
- Normal conversations can use Qwen for pre-visit assistance
- The system can generate a structured pre-visit report from consultation history
- All patient-facing outputs include a disclaimer and never present a final diagnosis
- The Mini Program supports Chinese/English UI switching
- When the UI language changes, backend chat replies, report content, and disclaimers switch language as well
- The chat page supports optimistic message insertion, AI thinking placeholders, and rollback on send failure
- The report page supports back-to-chat, regenerate report, and start-new-consultation actions

### Repository Structure

```text
.
├─ backend/                 # Flask backend
├─ miniprogram/             # WeChat Mini Program frontend
├─ requirements.txt
└─ README.md
```

### Backend APIs

- `GET /`
- `GET /api/health`
- `POST /api/auth/wx-login`
- `POST /api/chat`
- `GET /api/consultations/<id>/messages`
- `POST /api/report/generate`
- `GET /api/report/<consultation_id>`

Unified response shape:

```json
{
  "success": true,
  "code": "OK",
  "message": "OK",
  "data": {}
}
```

### Local Run

#### 1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

#### 2. Configure environment variables

Create a `.env` file at the project root and fill in the values as needed.

Minimal local configuration:

```env
FLASK_ENV=development
SECRET_KEY=replace-me
DATABASE_URL=sqlite:///pre_diagnosis.db
LOG_LEVEL=INFO

LLM_PROVIDER=mock
LLM_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
```

To connect Alibaba Cloud Bailian:

```env
LLM_PROVIDER=qwen
LLM_API_KEY=YOUR_REAL_KEY_HERE
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
```

Notes:

- Never hardcode real secrets in code, the README, or the repository
- `LLM_BASE_URL` defaults to the Bailian compatible-mode endpoint
- The implementation still accepts the legacy `LLM_API_URL` name, but `LLM_BASE_URL` is preferred

#### 3. Start the backend

```bash
python backend/run.py
```

Default addresses:

- Root: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- Health check: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

#### 4. Run tests

```bash
python -m pytest backend/tests -q
```

### Local API Checks Without WeChat GUI

Start the backend first, then use the following examples.

#### 1. Mock login

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/auth/wx-login" `
  -ContentType "application/json" `
  -Body '{"code":"local-test-code","nickname":"Local Test User"}'

$userId = $login.data.user.id
$userId
```

#### 2. English `/api/chat` example

```powershell
$chatEn = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/chat" `
  -ContentType "application/json" `
  -Body (@{
    user_id = $userId
    message = "I have had a fever for two days and a sore throat"
    locale = "en-US"
  } | ConvertTo-Json)

$chatEn
```

#### 3. `/api/report/generate` example

```powershell
$consultationId = $chatEn.data.consultation_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/report/generate" `
  -ContentType "application/json" `
  -Body (@{
    consultation_id = $consultationId
    locale = "en-US"
  } | ConvertTo-Json)
```

### Qwen/Bailian Integration

`LLMService` uses raw `requests` against the OpenAI-compatible API, without adding an extra SDK dependency.

- Provider id: `LLM_PROVIDER=qwen`
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Chat endpoint: `/chat/completions`
- Default model: `qwen3.6-plus`

Chat behavior:

- Emergency symptoms are intercepted locally before model calls
- Non-emergency conversations go to the model
- Timeouts are retried once automatically
- Provider failures fall back to a safe local reply
- Markdown is normalized before the content reaches the Mini Program
- Output language follows `locale`

Report behavior:

- Uses `response_format={"type":"json_object"}`
- Prompts explicitly require `JSON`
- Provider responses are parsed safely
- Missing fields are filled with safe defaults and logged as warnings
- Invalid JSON falls back to a safe degraded report instead of crashing
- Output language follows `locale`

### WeChat Mini Program Debugging

Open the `miniprogram/` directory in WeChat DevTools.

#### 1. Local configuration to check

- `baseURL` in [env.js](/d:/Users/Admin/Desktop/Wechat%20program/miniprogram/config/env.js)
- `appid` in [project.config.json](/d:/Users/Admin/Desktop/Wechat%20program/miniprogram/project.config.json)

If DevTools cannot access `127.0.0.1`, switch `baseURL` to your machine's LAN IP, for example:

```js
baseURL: 'http://192.168.1.10:5000'
```

#### 2. DevTools settings

- Disable or relax legal-domain checks for local debugging
- After changing config, use “Clear cache and recompile”

#### 3. Current frontend interactions

Chat page:

- User messages appear immediately after tapping send
- An AI thinking placeholder is shown while waiting
- Failed sends roll back to the previous UI state
- Supports starting a new consultation
- Supports `中 / EN` language switching
- Shows message timestamps and send status

Report page:

- Shows structured report fields
- Supports back-to-chat
- Supports regenerate report
- Supports start new consultation
- Supports `中 / EN` language switching

#### 4. Recommended debug flow

1. Start the backend
2. Open WeChat DevTools and import `miniprogram/`
3. Verify mock login first
4. Send one normal symptom message and confirm chat replies work
5. Test one emergency symptom and confirm local escalation triggers
6. Generate a doctor summary and confirm the report page works
7. Switch to `EN`, then send an English symptom and confirm frontend and backend both switch together

### Safety Boundaries

- This product is a pre-visit assistance tool, not a diagnosis system
- It never returns a definitive diagnosis
- Local emergency interception always takes precedence over model calls
- Patient-facing outputs always include a disclaimer
- High-risk symptoms such as chest pain, severe breathing difficulty, loss of consciousness, or severe bleeding trigger a local escalation path first

### Known Limitations

- Login is still stubbed and does not use real WeChat `code2Session`
- In English mode, real model output quality still depends on the actual Qwen response, not only on fixed templates
- There is no migration tool yet; schema changes are still handled in MVP style
- The frontend still uses native Mini Program rendering and does not include advanced rich-text rendering

### TODO

- `TODO: replace stubbed login with real WeChat code2Session flow.`
- `TODO_REPLACE_WITH_REAL_WECHAT_APPID`
- `TODO_REPLACE_WITH_REAL_MINIPROGRAM_APPID`
- WeChat legal request domain configuration
- Production database and cloud-hosting deployment parameters
