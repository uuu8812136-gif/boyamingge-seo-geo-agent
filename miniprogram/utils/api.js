// 后端 API 封装：统一处理请求头、token 注入、错误拦截、缓存与防重复
const auth = require('./auth.js')

// 后端服务地址，部署时请修改为线上 HTTPS 域名
const BASE_URL = 'http://localhost:8000/api/v1'

// ── 缓存与防重复 ──────────────────────────────
const CACHE_TTL = 30000 // 缓存有效期 30 秒
const _cache = {}       // url -> { data, ts }
const _pending = {}     // url -> Promise（防重复请求）

function _cacheKey(url, method, data) {
  return method + ':' + url + ':' + (data ? JSON.stringify(data) : '')
}

// 读取缓存，过期返回 null
function _getCache(key) {
  const c = _cache[key]
  if (!c) return null
  if (Date.now() - c.ts > CACHE_TTL) {
    delete _cache[key]
    return null
  }
  return c.data
}

// 写入缓存
function _setCache(key, data) {
  _cache[key] = { data: data, ts: Date.now() }
}

// 清除缓存（数据变更后调用）
function clearCache(prefix) {
  if (!prefix) {
    Object.keys(_cache).forEach(function(k) { delete _cache[k] })
    return
  }
  Object.keys(_cache).forEach(function(k) {
    if (k.indexOf(prefix) === 0) delete _cache[k]
  })
}

// 统一请求封装，自动注入 Bearer token，带缓存与防重复
function request(options) {
  var url = options.url
  var method = options.method || 'GET'
  var data = options.data
  var header = options.header || {}
  var useCache = options.cache !== false && method === 'GET'

  var cacheKey = _cacheKey(url, method, data)

  // 1) 命中缓存直接返回
  if (useCache) {
    var cached = _getCache(cacheKey)
    if (cached) return Promise.resolve(cached)
  }

  // 2) 防重复：相同请求正在进行中则复用 Promise
  if (_pending[cacheKey]) return _pending[cacheKey]

  var token = auth.getToken()
  var reqHeader = Object.assign({ 'Content-Type': 'application/json' }, header)
  if (token) {
    reqHeader['Authorization'] = 'Bearer ' + token
  }

  var p = new Promise(function(resolve, reject) {
    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      header: reqHeader,
      success: function(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (useCache) _setCache(cacheKey, res.data)
          resolve(res.data)
        } else if (res.statusCode === 401) {
          auth.clearToken()
          wx.reLaunch({ url: '/pages/login/login' })
          reject(res)
        } else {
          reject(res)
        }
      },
      fail: function(err) {
        reject(err)
      },
      complete: function() {
        delete _pending[cacheKey]
      },
    })
  })

  _pending[cacheKey] = p
  return p
}

// 登录：OAuth2 表单提交（不走缓存）
function login(username, password) {
  return new Promise(function(resolve, reject) {
    wx.request({
      url: BASE_URL + '/auth/token',
      method: 'POST',
      header: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: { username: username, password: password },
      success: function(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: function(err) {
        reject(err)
      },
    })
  })
}

// ── 内容确认 ──────────────────────────────

function getProfile() {
  return request({ url: '/dealer/profile' })
}

function getPublications(status) {
  var query = status ? '?status=' + status : ''
  return request({ url: '/dealer/publications' + query })
}

function getStats() {
  return request({ url: '/dealer/stats' })
}

function getPublicationDetail(id) {
  return request({ url: '/dealer/publications/' + id })
}

// 确认/驳回内容（写操作，清除列表缓存）
function confirmPublication(id, action) {
  clearCache('GET:/dealer/publications')
  clearCache('GET:/dealer/stats')
  return request({
    url: '/dealer/publications/' + id + '/confirm',
    method: 'POST',
    data: { action: action },
    cache: false,
  })
}

// ── 我的线索 ──────────────────────────────

function getLeads() {
  return request({ url: '/dealer/leads' })
}

// 更新线索状态（写操作，清除线索缓存）
function updateLeadStatus(leadId, status) {
  clearCache('GET:/dealer/leads')
  return request({
    url: '/dealer/leads/' + leadId,
    method: 'PATCH',
    data: { status: status },
    cache: false,
  })
}

// ── 素材上传 ──────────────────────────────

function getMaterials() {
  return request({ url: '/dealer/materials' })
}

// 上传素材文件（不走缓存）
function uploadMaterial(filePath, onProgress) {
  return new Promise(function(resolve, reject) {
    var token = auth.getToken()
    var task = wx.uploadFile({
      url: BASE_URL + '/dealer/materials/upload',
      filePath: filePath,
      name: 'file',
      header: token ? { Authorization: 'Bearer ' + token } : {},
      success: function(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          clearCache('GET:/dealer/materials')
          try {
            resolve(JSON.parse(res.data))
          } catch (e) {
            resolve(res.data)
          }
        } else {
          reject(res)
        }
      },
      fail: function(err) {
        reject(err)
      },
    })
    if (onProgress && task.onProgressUpdate) {
      task.onProgressUpdate(function(res) {
        onProgress(res.progress)
      })
    }
  })
}

module.exports = {
  BASE_URL: BASE_URL,
  request: request,
  login: login,
  getProfile: getProfile,
  getPublications: getPublications,
  getStats: getStats,
  getPublicationDetail: getPublicationDetail,
  confirmPublication: confirmPublication,
  getLeads: getLeads,
  updateLeadStatus: updateLeadStatus,
  getMaterials: getMaterials,
  uploadMaterial: uploadMaterial,
  clearCache: clearCache,
}
