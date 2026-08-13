// Token 管理工具：负责 access_token / refresh_token 的本地存储与读取

const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// 获取 access_token
function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
}

// 保存 access_token
function setToken(token) {
  wx.setStorageSync(TOKEN_KEY, token)
}

// 获取 refresh_token
function getRefreshToken() {
  return wx.getStorageSync(REFRESH_TOKEN_KEY) || ''
}

// 保存 refresh_token
function setRefreshToken(token) {
  wx.setStorageSync(REFRESH_TOKEN_KEY, token)
}

// 清除所有 token（退出登录）
function clearToken() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(REFRESH_TOKEN_KEY)
}

// 是否已登录
function isLoggedIn() {
  return !!getToken()
}

module.exports = {
  getToken,
  setToken,
  getRefreshToken,
  setRefreshToken,
  clearToken,
  isLoggedIn,
}
