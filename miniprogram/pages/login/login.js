// 经销商登录页
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    username: 'dealer_gz',
    password: 'dealer123',
    loading: false,
  },

  onShow() {
    if (auth.isLoggedIn()) {
      wx.switchTab({ url: '/pages/content/content' })
    }
  },

  // 绑定输入框（通过 data-field 区分字段）
  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  // 登录
  onLogin() {
    if (this.data.loading) return
    const { username, password } = this.data
    if (!username || !password) {
      wx.showToast({ title: '请输入账号和密码', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    api
      .login(username, password)
      .then((res) => {
        // 保存 token
        auth.setToken(res.access_token)
        if (res.refresh_token) {
          auth.setRefreshToken(res.refresh_token)
        }
        wx.showToast({ title: '登录成功', icon: 'success' })
        // 跳转到内容页（tabBar 页需用 switchTab）
        setTimeout(() => {
          wx.switchTab({ url: '/pages/content/content' })
        }, 500)
      })
      .catch((err) => {
        const msg = (err && err.data && err.data.detail) || '登录失败，请重试'
        wx.showToast({ title: msg, icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },
})
