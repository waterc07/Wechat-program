# 医疗预问诊微信小程序 MVP

这是一个可本地运行、可部署到微信云托管的医疗预问诊 MVP。项目包含原生微信小程序前端、Flask 后端、SQLite/MySQL 数据存储、Qwen/百炼兼容模型调用，以及面向患者侧的安全免责声明和高风险症状本地拦截。

> 本项目用于就诊前信息整理，不提供最终诊断，也不能替代医生面诊。

## 当前能力

- 微信小程序聊天式问诊，支持中文和英文界面切换。
- 后端保存用户、问诊、消息、结构化报告。
- 支持历史问诊列表、继续问诊、重新生成报告、开始新问诊。
- 普通消息可通过 Qwen/百炼 OpenAI 兼容接口生成回复。
- 高风险症状命中本地规则时优先返回就医提醒，不调用模型。
- 聊天支持普通请求和 SSE 流式接口；云托管模式下会用普通云容器返回模拟流式片段。
- 前端请求支持 `wx.request` 和 `wx.cloud.callContainer` 两种传输模式。
- 网络请求带可恢复错误重试；聊天 POST 会带 `client_request_id`，后端可复用重复请求的既有回复，避免重复写入。
- 生产环境启动时会校验 `SECRET_KEY`、数据库、LLM Provider 和微信云 OpenID 来源。

## 技术栈

- 前端：原生微信小程序
- 后端：Python Flask
- ORM：Flask-SQLAlchemy
- 数据库：本地默认 SQLite，生产建议 MySQL 兼容数据库
- 模型：`mock` 或 Qwen/百炼 OpenAI 兼容接口
- 部署：本地运行或微信云托管 Docker 部署

## 目录结构

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ models/              # User / Consultation / Message / Report
│  │  ├─ routes/              # auth / chat / consultations / report / health
│  │  ├─ schemas/             # 请求校验和统一响应
│  │  ├─ services/            # 业务逻辑、LLM、报告、风险判断
│  │  └─ utils/
│  ├─ tests/
│  ├─ run.py                  # 本地启动入口
│  └─ wsgi.py                 # gunicorn / 云托管入口
├─ miniprogram/
│  ├─ config/env.js           # 小程序传输和云托管配置
│  ├─ pages/chat/             # 聊天和历史问诊
│  ├─ pages/report/           # 报告页
│  └─ utils/                  # api / request / i18n / disclaimer
├─ Dockerfile
├─ requirements.txt
└─ README.md
```

## 后端接口

所有 JSON 接口默认返回统一结构：

```json
{
  "success": true,
  "code": "OK",
  "message": "OK",
  "data": {}
}
```

主要接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 服务根路径 |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/auth/wx-login` | 小程序登录 |
| `POST` | `/api/chat` | 非流式聊天 |
| `POST` | `/api/chat/stream` | SSE 流式聊天 |
| `GET` | `/api/consultations?user_id=<id>` | 查询用户历史问诊 |
| `GET` | `/api/consultations/<id>/messages` | 查询问诊消息 |
| `POST` | `/api/report/generate` | 生成或重新生成报告 |
| `GET` | `/api/report/<consultation_id>` | 查询最新报告 |

### `/api/auth/wx-login`

请求体：

```json
{
  "code": "wx-login-code",
  "nickname": "微信用户"
}
```

本地测试也可以传：

```json
{
  "mock_openid": "local-user-1",
  "nickname": "本地测试用户"
}
```

生产环境下，后端要求云托管注入 `X-WX-OPENID` 或 `X-WX-FROM-OPENID` 请求头；否则返回 `WECHAT_OPENID_REQUIRED`。

### `/api/chat`

请求体：

```json
{
  "user_id": 1,
  "consultation_id": null,
  "message": "我发烧两天，喉咙痛",
  "locale": "zh-CN",
  "client_request_id": "chat-unique-id"
}
```

字段说明：

- `user_id`：必填，登录接口返回的用户 ID。
- `consultation_id`：可选；为空时创建新问诊，传已有 ID 时继续问诊。
- `message`：必填，最多 2000 字符。
- `locale`：可选，支持 `zh-CN` 和 `en-US`，其他值会归一到默认语言。
- `client_request_id`：可选但推荐；用于 POST 重试幂等。

### `/api/chat/stream`

返回 `text/event-stream`，事件包括：

- `meta`：返回 `consultation_id`、是否新建、用户消息 ID。
- `delta`：增量文本。
- `done`：完整 assistant 消息和风险等级。
- `error`：流式过程中发生错误。

微信云托管 `wx.cloud.callContainer` 不是真正的 chunk 级流式通道。当前小程序在云托管模式下会把 `/api/chat/stream` 映射到 `/api/chat`，再在前端转换为近似 SSE 片段。需要真正逐 token 流式时，应改用 `wx.cloud.connectContainer` / WebSocket 类方案。

### `/api/report/generate`

请求体：

```json
{
  "consultation_id": 1,
  "locale": "zh-CN"
}
```

报告字段：

- `symptoms_summary`
- `possible_conditions`
- `recommended_department`
- `urgency_level`
- `next_step_advice`
- `disclaimer`

报告免责声明由本地逻辑覆盖，避免模型输出替换安全边界。

## 本地运行后端

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 创建 `.env`

在项目根目录创建 `.env`。本地最小配置：

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
CHAT_LLM_TIMEOUT_SECONDS=8

WECHAT_USE_REAL_AUTH=false
WECHAT_APPID=
WECHAT_APPSECRET=
```

接入 Qwen/百炼时：

```env
LLM_PROVIDER=qwen
LLM_API_KEY=YOUR_REAL_KEY_HERE
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
CHAT_LLM_TIMEOUT_SECONDS=8
```

注意：

- 不要把真实密钥写入代码、README 或提交到 Git。
- `LLM_BASE_URL` 是推荐变量名；代码仍兼容旧的 `LLM_API_URL`。
- `CHAT_LLM_TIMEOUT_SECONDS` 会限制聊天接口的快速回复超时；报告生成仍使用 `LLM_TIMEOUT_SECONDS`。

### 3. 启动服务

```bash
python backend/run.py
```

默认地址：

- 根路径：[http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- 健康检查：[http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

### 4. 运行测试

```bash
python -m pytest backend/tests -q
```

## PowerShell 接口自测

先启动后端，再在 PowerShell 执行以下命令。

### 登录

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/auth/wx-login" `
  -ContentType "application/json" `
  -Body (@{
    mock_openid = "local-user-1"
    nickname = "本地测试用户"
  } | ConvertTo-Json)

$userId = $login.data.user.id
$userId
```

### 发送中文聊天

```powershell
$chat = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/chat" `
  -ContentType "application/json" `
  -Body (@{
    user_id = $userId
    message = "我发烧两天，喉咙痛，还有一点咳嗽"
    locale = "zh-CN"
    client_request_id = "local-chat-zh-1"
  } | ConvertTo-Json)

$chat.data.consultation_id
$chat.data.assistant_message.content
```

### 继续同一问诊

```powershell
$consultationId = $chat.data.consultation_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/chat" `
  -ContentType "application/json" `
  -Body (@{
    user_id = $userId
    consultation_id = $consultationId
    message = "最高体温 38.5 度，已经吃过退烧药"
    locale = "zh-CN"
    client_request_id = "local-chat-zh-2"
  } | ConvertTo-Json)
```

### 生成报告

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/report/generate" `
  -ContentType "application/json" `
  -Body (@{
    consultation_id = $consultationId
    locale = "zh-CN"
  } | ConvertTo-Json)
```

### 查询历史问诊

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:5000/api/consultations?user_id=$userId"
```

## 微信小程序配置

使用微信开发者工具导入 `miniprogram/` 目录。

核心配置在 [miniprogram/config/env.js](/d:/Users/Admin/Desktop/Wechat%20program/miniprogram/config/env.js)：

```js
const env = {
  transport: 'cloud-container',
  cloudEnv: 'prod-d5g1plnin0443c04a',
  cloudService: 'test',
  cloudResourceAppid: '',
  cloudResourceEnv: '',
  baseURL: 'https://test-249099-6-1424293714.sh.run.tcloudbase.com/',
  timeout: 70000
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `transport` | `'cloud-container'` 使用 `wx.cloud.callContainer`；其他值走 `wx.request` |
| `cloudEnv` | 小程序关联的云开发环境 ID |
| `cloudService` | 云托管服务名，会作为 `X-WX-SERVICE` |
| `cloudResourceAppid` | 跨账号资源方 AppID；为空表示使用当前小程序云环境 |
| `cloudResourceEnv` | 跨账号资源方环境 ID |
| `baseURL` | `wx.request` 模式下的后端基础 URL |
| `timeout` | 小程序请求超时时间，毫秒 |

### 本地联调模式

如果要在微信开发者工具中连本地 Flask：

```js
const env = {
  transport: 'http',
  cloudEnv: '',
  cloudService: '',
  cloudResourceAppid: '',
  cloudResourceEnv: '',
  baseURL: 'http://127.0.0.1:5000',
  timeout: 60000
}
```

如果开发者工具无法访问 `127.0.0.1`，把 `baseURL` 改成电脑局域网 IP，例如：

```js
baseURL: 'http://192.168.1.10:5000'
```

本地调试时通常还需要在微信开发者工具中关闭或放开“合法域名校验”，修改配置后执行“清缓存并编译”。

### 云托管模式

当前默认配置走云托管私有调用：

- 小程序启动时执行 `wx.cloud.init({ env: env.cloudEnv, traceUser: true })`。
- 普通请求调用 `wx.cloud.callContainer`。
- 请求头包含 `X-WX-SERVICE: env.cloudService`。
- 后端生产环境通过云托管注入的 OpenID 请求头识别用户来源。

云托管常见错误：

- `cloud.callContainer:fail system error. code: 102002`：优先检查云托管服务是否已部署、服务名是否正确、小程序是否关联了正确云环境、云端日志是否有容器启动失败。
- `INVALID_HOST` 或 `-501000`：通常是云环境 ID、服务名或资源方配置不匹配。
- `options.timeout == 15000`：旧版小程序请求曾把云托管请求限制在 15 秒；当前配置使用 `env.timeout`，默认示例为 70 秒。

## 微信云托管部署

推荐云托管服务配置：

- 服务端口：`80`
- 目标目录：项目根目录 `.`
- Dockerfile：根目录 [Dockerfile](/d:/Users/Admin/Desktop/Wechat%20program/Dockerfile)

生产环境变量至少应包含：

```env
FLASK_ENV=production
SECRET_KEY=a-new-strong-random-secret
DATABASE_URL=mysql+pymysql://username:password@host:3306/dbname?charset=utf8mb4
LOG_LEVEL=INFO

LLM_PROVIDER=qwen
LLM_API_KEY=YOUR_REAL_KEY_HERE
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-plus
LLM_TIMEOUT_SECONDS=30
CHAT_LLM_TIMEOUT_SECONDS=8

WECHAT_USE_REAL_AUTH=false
WECHAT_APPID=your-mini-program-appid
WECHAT_APPSECRET=your-mini-program-appsecret
```

生产启动校验：

- `SECRET_KEY` 不能为空或 `replace-me`。
- `DATABASE_URL` 不能使用 SQLite。
- `LLM_PROVIDER` 不能是 `mock`。
- `LLM_PROVIDER=qwen` 时必须提供 `LLM_API_KEY`。
- 如果 `WECHAT_USE_REAL_AUTH=true`，必须提供 `WECHAT_APPID` 和 `WECHAT_APPSECRET`。

数据库建议：

```env
DATABASE_URL=mysql+pymysql://username:password@host:3306/dbname?charset=utf8mb4
```

保留 `charset=utf8mb4`，避免中文和 emoji 存储问题。如果数据库要求 SSL，按服务商要求追加连接参数。

## LLM 行为

`LLMService` 使用 `requests` 直接调用 OpenAI 兼容接口，不额外引入 SDK。

Qwen/百炼默认信息：

- Provider：`qwen`
- Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- Endpoint：`/chat/completions`
- 默认模型：`qwen3.6-plus`

聊天行为：

- 高风险症状先走本地规则。
- 非高风险消息才调用外部模型。
- 聊天接口使用较短的 `CHAT_LLM_TIMEOUT_SECONDS`，失败时降级到本地安全回复。
- 模型输出会清理 Markdown 标记，避免小程序原生文本渲染异常。
- 输出语言跟随 `locale`。

报告行为：

- 请求模型时使用 `response_format={"type":"json_object"}`。
- Prompt 明确要求 JSON 输出。
- 解析失败时降级到本地安全报告。
- 缺失字段会用安全默认值补齐。
- `disclaimer` 始终使用本地免责声明。

## 安全边界

- 本项目只做预问诊信息整理，不做最终诊断。
- 患者侧输出必须包含免责声明。
- 高风险症状本地拦截优先级高于模型调用。
- 胸痛、严重呼吸困难、意识丧失、严重出血等症状应触发升级提醒。
- 生产环境不要使用 mock 模型、默认密钥或 SQLite。

## 已知限制

- 当前登录依赖微信云托管注入的 OpenID 或本地 mock openid；还没有完整实现传统 `code2Session` 主动换取流程。
- 云托管 `callContainer` 不提供真实 chunk 级 SSE；当前为兼容小程序体验做了近似流式。
- 数据库表结构由 `db.create_all()` 和运行时 schema 补齐处理，尚未接入 Alembic 等迁移工具。
- 小程序仍使用原生文本渲染，没有复杂富文本渲染。
- 英文真实回复质量取决于外部模型输出，不是完全固定模板。

## TODO

- 完整接入真实微信 `code2Session` 流程，或明确只依赖云托管 OpenID 注入。
- 为数据库变更引入正式 migration。
- 根据正式部署环境替换 `cloudEnv`、`cloudService`、`baseURL` 和小程序 `appid`。
- 配置微信合法域名和云托管服务权限。
- 如需真实流式体验，设计 `wx.cloud.connectContainer` / WebSocket 通道。

---

## English Summary

This repository is a WeChat Mini Program MVP for medical pre-visit intake. It includes a native Mini Program frontend, a Flask backend, SQLite/MySQL persistence, Qwen/Bailian OpenAI-compatible LLM integration, local emergency-risk interception, structured report generation, and WeChat Cloud Hosting support.

Quick start:

```bash
python -m pip install -r requirements.txt
python backend/run.py
python -m pytest backend/tests -q
```

Core configuration:

- Backend environment variables are loaded from `.env`.
- Mini Program transport is configured in `miniprogram/config/env.js`.
- Use `transport: 'http'` for local `wx.request` debugging.
- Use `transport: 'cloud-container'` for `wx.cloud.callContainer` private Cloud Hosting access.
- Production must use a non-default `SECRET_KEY`, a MySQL-compatible `DATABASE_URL`, and a real LLM provider.

Main endpoints:

- `GET /`
- `GET /api/health`
- `POST /api/auth/wx-login`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/consultations?user_id=<id>`
- `GET /api/consultations/<id>/messages`
- `POST /api/report/generate`
- `GET /api/report/<consultation_id>`

Safety scope: this project organizes information before a visit. It does not provide a final diagnosis and must not replace in-person medical evaluation.
