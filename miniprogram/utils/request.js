const env = require('../config/env')

let resourceCloudClient = null
let resourceCloudInitPromise = null

const DEFAULT_REQUEST_TIMEOUT_MS = 60000
const MAX_RETRY_ATTEMPTS = 3
const RETRY_BASE_DELAY_MS = 800

function getRequestTimeout() {
  return env.timeout || DEFAULT_REQUEST_TIMEOUT_MS
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function getRawErrorMessage(error) {
  return error && error.errMsg ? error.errMsg : error && error.message ? error.message : ''
}

function isTimeoutError(error) {
  return getRawErrorMessage(error).toLowerCase().includes('timeout')
}

function isNetworkFailure(error) {
  const message = getRawErrorMessage(error).toLowerCase()
  return (
    (error && error.code === 'NETWORK_ERROR') ||
    isTimeoutError(error) ||
    message.includes('fail') ||
    message.includes('socket') ||
    message.includes('network') ||
    message.includes('interrupted') ||
    message.includes('connection') ||
    message.includes('reset') ||
    message.includes('refused')
  )
}

function isRetryableStatus(statusCode) {
  return statusCode === 408 || statusCode === 429 || statusCode >= 500
}

function getRetryDelay(attempt) {
  return RETRY_BASE_DELAY_MS * attempt * attempt
}

function withRetry(operation, context, shouldRetry) {
  let attempt = 1

  function run() {
    return operation(attempt).catch((error) => {
      const retryable = typeof shouldRetry === 'function' ? shouldRetry(error) : isNetworkFailure(error)
      if (!retryable || attempt >= MAX_RETRY_ATTEMPTS) {
        throw error
      }

      console.warn('[request:retry]', {
        transport: context.transport,
        path: context.path,
        method: context.method,
        attempt,
        nextAttempt: attempt + 1,
        error
      })
      attempt += 1
      return wait(getRetryDelay(attempt)).then(run)
    })
  }

  return run()
}

function isCloudContainerTransport() {
  return env.transport === 'cloud-container'
}

function isResourceCloudTransport() {
  return Boolean(env.cloudResourceAppid && env.cloudResourceEnv)
}

function getEndpointDisplay() {
  if (isCloudContainerTransport()) {
    const cloudEnv = isResourceCloudTransport() ? env.cloudResourceEnv : env.cloudEnv
    return `cloud://${cloudEnv}/${env.cloudService}`
  }
  return env.baseURL
}

function normalizeErrorMessage(error) {
  // 优先识别来自云调用 SDK 的数值型错误码（例如 102002 系统错误），返回更明确的建议。
  if (error && (error.errCode === 102002 || error.errcode === 102002 || error.code === 102002)) {
    return '云托管系统错误 (102002)：请检查云托管服务是否已部署、服务名和环境是否与小程序关联正确，并查看云端日志以获取详细信息。'
  }

  const rawMessage = getRawErrorMessage(error)
  if (isTimeoutError(error)) {
    return '请求超时，请检查网络或稍后重试'
  }
  if (rawMessage.includes('INVALID_HOST') || rawMessage.includes('-501000')) {
    return `云托管主机无效，请核对环境 ${env.cloudEnv || '(默认)'} 和服务 ${env.cloudService}`
  }
  if (rawMessage.includes('request:fail')) {
    return '网络请求失败，请检查云托管服务、小程序环境关联和云开发初始化配置。'
  }
  if (rawMessage.includes('callContainer')) {
    return '云托管调用失败，请检查 cloudEnv、服务名和小程序关联环境。'
  }
  return rawMessage || '网络请求失败'
}

function unwrapCloudResponse(response) {
  const body =
    response && Object.prototype.hasOwnProperty.call(response, 'result')
      ? response.result
      : response && Object.prototype.hasOwnProperty.call(response, 'data')
        ? response.data
        : response

  const statusCode =
    (response && (response.statusCode || response.status)) ||
    (body && typeof body === 'object' && body.success !== undefined ? 200 : 200)

  return {
    statusCode,
    header: (response && response.header) || {},
    data: body
  }
}

function buildRequestError({ statusCode, message, code, data, raw }) {
  return {
    statusCode,
    message: message || normalizeErrorMessage(raw),
    code: code || (isRetryableStatus(statusCode) ? 'NETWORK_RETRYABLE' : 'REQUEST_ERROR'),
    data: data || {},
    raw
  }
}

function stringToArrayBuffer(text) {
  if (typeof TextEncoder !== 'undefined') {
    return new TextEncoder().encode(text).buffer
  }

  const encoded = unescape(encodeURIComponent(text))
  const buffer = new ArrayBuffer(encoded.length)
  const view = new Uint8Array(buffer)
  for (let index = 0; index < encoded.length; index += 1) {
    view[index] = encoded.charCodeAt(index)
  }
  return buffer
}

function buildSseEvent(event, data) {
  return `event: ${event}\ndata: ${JSON.stringify(data || {})}\n\n`
}

function buildChatSseFromCloudPayload(payload) {
  const data = payload && payload.data ? payload.data : null
  const assistantMessage = data && data.assistant_message ? data.assistant_message : null
  if (!payload || !payload.success || !data || !assistantMessage) {
    return ''
  }

  return [
    buildSseEvent('meta', {
      consultation_id: data.consultation_id,
      created: data.created
    }),
    buildSseEvent('delta', {
      delta: assistantMessage.content || ''
    }),
    buildSseEvent('done', data)
  ].join('')
}

function buildCloudCallOptions(options) {
  if (!wx.cloud || typeof wx.cloud.callContainer !== 'function') {
    throw new Error('wx.cloud.callContainer is unavailable')
  }
  if (!env.cloudEnv || !env.cloudService) {
    throw new Error('cloudEnv or cloudService is not configured')
  }

  const header = {
    'X-WX-SERVICE': env.cloudService,
    'Content-Type': 'application/json',
    ...(options.header || {})
  }

  const callOptions = {
    path: options.url,
    method: (options.method || 'GET').toUpperCase(),
    header,
    data: options.data || {},
    dataType: options.dataType,
    timeout: getRequestTimeout()
  }

  if (!isResourceCloudTransport()) {
    callOptions.config = {
      env: env.cloudEnv
    }
  }

  return callOptions
}

function getCloudCaller() {
  if (!isResourceCloudTransport()) {
    return Promise.resolve(wx.cloud)
  }

  if (!wx.cloud || typeof wx.cloud.Cloud !== 'function') {
    return Promise.reject(new Error('wx.cloud.Cloud is unavailable'))
  }

  if (!resourceCloudClient) {
    resourceCloudClient = new wx.cloud.Cloud({
      resourceAppid: env.cloudResourceAppid,
      resourceEnv: env.cloudResourceEnv
    })
    resourceCloudInitPromise = resourceCloudClient.init()
  }

  return resourceCloudInitPromise.then(() => resourceCloudClient)
}

function callCloudContainer(cloud, callOptions) {
  return cloud.callContainer(callOptions).then((response) => {
    const normalized = unwrapCloudResponse(response)
    if (isRetryableStatus(normalized.statusCode)) {
      throw buildRequestError({
        statusCode: normalized.statusCode,
        message: `Server returned ${normalized.statusCode}`,
        code: 'NETWORK_RETRYABLE',
        data: normalized.data || {},
        raw: response
      })
    }
    return response
  })
}

function requestByCloudContainer(options) {
  return new Promise((resolve, reject) => {
    let callOptions = null
    try {
      callOptions = buildCloudCallOptions(options)
    } catch (error) {
      reject({
        message: normalizeErrorMessage(error),
        code: 'NETWORK_ERROR',
        raw: error
      })
      return
    }

    console.info('[cloud:request:start]', {
      path: callOptions.path,
      method: callOptions.method,
      service: env.cloudService,
      env: env.cloudEnv,
      timeout: callOptions.timeout,
      data: callOptions.data
    })

    getCloudCaller()
      .then((cloud) =>
        withRetry(
          () => callCloudContainer(cloud, callOptions),
          {
            transport: 'cloud-container',
            path: callOptions.path,
            method: callOptions.method
          },
          (error) => isNetworkFailure(error) || isRetryableStatus(error && error.statusCode)
        )
      )
      .then((response) => {
        const normalized = unwrapCloudResponse(response)
        const payload = normalized.data || {}

        console.info('[cloud:request:success]', {
          path: callOptions.path,
          method: callOptions.method,
          statusCode: normalized.statusCode,
          payload
        })

        if (normalized.statusCode >= 200 && normalized.statusCode < 300 && payload.success) {
          resolve(payload.data)
          return
        }

        reject({
          statusCode: normalized.statusCode,
          message: payload.message || '请求失败',
          code: payload.code || 'REQUEST_ERROR',
          data: payload.data || {}
        })
      })
      .catch((error) => {
        console.error('[cloud:request:fail]', {
          path: callOptions.path,
          method: callOptions.method,
          error
        })
        reject({
          statusCode: error.statusCode,
          message: normalizeErrorMessage(error),
          code: error.code || 'NETWORK_ERROR',
          data: error.data || {},
          raw: error
        })
      })
  })
}

function requestByHttp(options) {
  return new Promise((resolve, reject) => {
    const method = (options.method || 'GET').toUpperCase()
    const url = `${env.baseURL}${options.url}`

    console.info('[request:start]', {
      method,
      url,
      data: options.data || {}
    })

    wx.request({
      url,
      method,
      timeout: getRequestTimeout(),
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...(options.header || {})
      },
      success: (res) => {
        const payload = res.data || {}
        console.info('[request:success]', {
          method,
          url,
          statusCode: res.statusCode,
          payload
        })
        if (res.statusCode >= 200 && res.statusCode < 300 && payload.success) {
          resolve(payload.data)
          return
        }

        reject({
          statusCode: res.statusCode,
          message: payload.message || '请求失败',
          code: payload.code || 'REQUEST_ERROR',
          data: payload.data || {}
        })
      },
      fail: (error) => {
        console.error('[request:fail]', {
          method,
          url,
          error
        })
        reject({
          message: normalizeErrorMessage(error),
          code: 'NETWORK_ERROR'
        })
      }
    })
  })
}

function request(options) {
  if (isCloudContainerTransport()) {
    return requestByCloudContainer(options)
  }
  return withRetry(
    () => requestByHttp(options),
    {
      transport: 'http',
      path: options.url,
      method: (options.method || 'GET').toUpperCase()
    },
    (error) => isNetworkFailure(error) || isRetryableStatus(error && error.statusCode)
  )
}

function streamRequestByCloudContainer(options) {
  let aborted = false
  let callOptions = null
  try {
    const requestUrl = options.url === '/api/chat/stream' ? '/api/chat' : options.url
    callOptions = buildCloudCallOptions({
      ...options,
      url: requestUrl,
      dataType: 'text',
      header: {
        Accept: 'text/event-stream',
        ...(options.header || {})
      }
    })
  } catch (error) {
    if (typeof options.fail === 'function') {
      options.fail({
        message: normalizeErrorMessage(error),
        code: 'NETWORK_ERROR',
        raw: error
      })
    }
    if (typeof options.complete === 'function') {
      options.complete()
    }
    return {
      abort() {}
    }
  }

  console.info('[cloud:stream:start]', {
    path: callOptions.path,
    method: callOptions.method,
    service: env.cloudService,
    env: env.cloudEnv,
    data: callOptions.data
  })

  getCloudCaller()
    .then((cloud) =>
      withRetry(
        () => callCloudContainer(cloud, callOptions),
        {
          transport: 'cloud-container-stream',
          path: callOptions.path,
          method: callOptions.method
        },
        (error) => isNetworkFailure(error) || isRetryableStatus(error && error.statusCode)
      )
    )
    .then((response) => {
      if (aborted) {
        return
      }

      const normalized = unwrapCloudResponse(response)
      const simulatedStreamText = buildChatSseFromCloudPayload(normalized.data)
      const bodyText =
        simulatedStreamText ||
        (typeof normalized.data === 'string'
          ? normalized.data
          : JSON.stringify(normalized.data || {}))

      if (typeof options.onChunkReceived === 'function' && bodyText) {
        options.onChunkReceived({ data: stringToArrayBuffer(bodyText) })
      }

      if (typeof options.success === 'function') {
        options.success({
          statusCode: normalized.statusCode,
          data: bodyText,
          header: normalized.header
        })
      }
    })
    .catch((error) => {
      if (aborted) {
        return
      }

      console.error('[cloud:stream:fail]', {
        path: callOptions.path,
        method: callOptions.method,
        error
      })
      if (typeof options.fail === 'function') {
        options.fail({
          statusCode: error.statusCode,
          message: normalizeErrorMessage(error),
          code: error.code || 'NETWORK_ERROR',
          data: error.data || {},
          raw: error
        })
      }
    })
    .finally(() => {
      if (!aborted && typeof options.complete === 'function') {
        options.complete()
      }
    })

  return {
    abort() {
      aborted = true
    }
  }
}

function streamRequestByHttp(options) {
  const method = (options.method || 'GET').toUpperCase()
  const url = `${env.baseURL}${options.url}`

  console.info('[stream:start]', {
    method,
    url,
    data: options.data || {}
  })

  const requestTask = wx.request({
    url,
    method,
    timeout: getRequestTimeout(),
    enableChunked: true,
    responseType: 'arraybuffer',
    data: options.data || {},
    header: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...(options.header || {})
    },
    success: (res) => {
      console.info('[stream:success]', {
        method,
        url,
        statusCode: res.statusCode
      })
      if (typeof options.success === 'function') {
        options.success(res)
      }
    },
    fail: (error) => {
      console.error('[stream:fail]', {
        method,
        url,
        error
      })
      if (typeof options.fail === 'function') {
        options.fail({
          message: normalizeErrorMessage(error),
          code: 'NETWORK_ERROR',
          raw: error
        })
      }
    },
    complete: (res) => {
      if (typeof options.complete === 'function') {
        options.complete(res)
      }
    }
  })

  if (requestTask && typeof requestTask.onChunkReceived === 'function' && typeof options.onChunkReceived === 'function') {
    requestTask.onChunkReceived((chunk) => {
      options.onChunkReceived(chunk)
    })
  }

  if (requestTask && typeof requestTask.onHeadersReceived === 'function' && typeof options.onHeadersReceived === 'function') {
    requestTask.onHeadersReceived((headers) => {
      options.onHeadersReceived(headers)
    })
  }

  return requestTask
}

function streamRequest(options) {
  if (isCloudContainerTransport()) {
    return streamRequestByCloudContainer(options)
  }
  return streamRequestByHttp(options)
}

module.exports = {
  getEndpointDisplay,
  request,
  streamRequest
}
