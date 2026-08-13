// 内容确认列表页 - 带状态筛选 Tab
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

// 状态 Tab 配置
const TABS = [
  { key: '', label: '全部' },
  { key: 'pending', label: '待确认' },
  { key: 'package_ready', label: '待领取' },
  { key: 'confirmed', label: '已确认' },
  { key: 'rejected', label: '已驳回' },
]

// 状态映射
const STATUS_MAP = {
  pending: { label: '待确认', cls: 'status-pending' },
  package_ready: { label: '待领取', cls: 'status-package' },
  confirmed: { label: '已确认', cls: 'status-confirmed' },
  rejected: { label: '已驳回', cls: 'status-rejected' },
  published: { label: '已发布', cls: 'status-published' },
}

Page({
  data: {
    tabs: TABS,
    activeTab: '',
    list: [],
    loading: true,
    isEmpty: false,
    stats: null,
  },

  onLoad() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
  },

  onShow() {
    if (auth.isLoggedIn()) {
      this.loadAll()
    }
  },

  // 合并加载统计数据和列表，并行请求
  loadAll() {
    this.setData({ loading: true })
    var status = this.data.activeTab || null
    return Promise.all([
      api.getStats(),
      api.getPublications(status),
    ]).then(function(results) {
      var statsRes = results[0]
      var pubsRes = results[1]
      var raw = (pubsRes && pubsRes.items) || []
      var list = raw.map(function(item) {
        var info = STATUS_MAP[item.status] || { label: item.status, cls: 'status-pending' }
        return Object.assign({}, item, {
          statusLabel: info.label,
          statusClass: info.cls,
        })
      })
      this.setData({
        stats: statsRes,
        list: list,
        isEmpty: list.length === 0,
        loading: false,
      })
    }.bind(this)).catch(function(err) {
      var msg = (err && err.data && err.data.detail) || '加载失败'
      wx.showToast({ title: msg, icon: 'none' })
      this.setData({ loading: false, isEmpty: true, list: [] })
    }.bind(this))
  },

  // 切换 Tab
  onTabChange(e) {
    var key = e.currentTarget.dataset.key
    if (this.data.activeTab === key) return
    this.setData({ activeTab: key, loading: true })
    var status = key || null
    api.getPublications(status).then(function(res) {
      var raw = (res && res.items) || []
      var list = raw.map(function(item) {
        var info = STATUS_MAP[item.status] || { label: item.status, cls: 'status-pending' }
        return Object.assign({}, item, {
          statusLabel: info.label,
          statusClass: info.cls,
        })
      })
      this.setData({ list: list, isEmpty: list.length === 0, loading: false })
    }.bind(this)).catch(function() {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }.bind(this))
  },

  // 点击卡片跳转详情页
  onTapCard(e) {
    var id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?publication_id=' + id })
  },

  // 下拉刷新（强制清除缓存，等请求完成再停止刷新动画）
  onPullDownRefresh() {
    api.clearCache()
    this.loadAll().finally(function() {
      wx.stopPullDownRefresh()
    })
  },
})
