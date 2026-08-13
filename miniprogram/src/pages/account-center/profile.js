// 个人中心页
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    profile: null,
    stats: null,
    loading: true,
    avatarText: '',
    statusText: '',
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadAll()
  },

  // 并行加载个人信息和统计数据
  loadAll() {
    this.setData({ loading: true })
    Promise.all([
      api.getProfile(),
      api.getStats(),
    ]).then(function(results) {
      var profileRes = results[0]
      var statsRes = results[1]
      this.setData({
        profile: profileRes,
        stats: statsRes,
        avatarText: (profileRes.name || '').substring(0, 1),
        statusText: profileRes.status === 'active' ? '正常' : profileRes.status,
        loading: false,
      })
    }.bind(this)).catch(function(err) {
      var msg = (err && err.data && err.data.detail) || '加载失败'
      wx.showToast({ title: msg, icon: 'none' })
      this.setData({ loading: false })
    }.bind(this))
  },

  // 退出登录
  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确认退出登录吗？',
      success: function(res) {
        if (!res.confirm) return
        auth.clearToken()
        api.clearCache()
        wx.reLaunch({ url: '/pages/login/login' })
      },
    })
  },

  goToContent() {
    wx.switchTab({ url: '/pages/content/content' })
  },

  goToLeads() {
    wx.switchTab({ url: '/pages/leads/leads' })
  },

  goToUpload() {
    wx.switchTab({ url: '/pages/upload/upload' })
  },
})
