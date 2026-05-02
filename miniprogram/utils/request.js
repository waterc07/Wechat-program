const env = require('../config/env')

let resourceCloudClient = null
let resourceCloudInitPromise = null

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
  const rawMessage = error && error.errMsg ? error.errMsg : error && error.message ? error.message : ''
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
    dataType: options.dataType
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
      data: callOptions.data
    })

    getCloudCaller()
      .then((cloud) => cloud.callContainer(callOptions))
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
          message: normalizeErrorMessage(error),
          code: 'NETWORK_ERROR',
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
      timeout: env.timeout,
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
  return requestByHttp(options)
}

function streamRequestByCloudContainer(options) {
  let aborted = false
  let callOptions = null
  try {
    callOptions = buildCloudCallOptions({
      ...options,
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
    .then((cloud) => cloud.callContainer(callOptions))
    .then((response) => {
      if (aborted) {
        return
      }

      const normalized = unwrapCloudResponse(response)
      const bodyText =
        typeof normalized.data === 'string'
          ? normalized.data
          : JSON.stringify(normalized.data || {})

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
          message: normalizeErrorMessage(error),
          code: 'NETWORK_ERROR',
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
    timeout: env.timeout,
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
