const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

const STATUS_MAP = {
  new: { text: '新线索', cls: 'status-new' },
  queued: { text: '已分配', cls: 'status-assigned' },
  contacted: { text: '已联系', cls: 'status-contacted' },
  converted: { text: '已成交', cls: 'status-converted' },
}

const SOURCE_MAP = {
  website: '官网',
  seo: 'SEO',
  geo: 'GEO',
}

Page({
  data: {
    list: [],
    loading: false,
    isEmpty: false,
    total: 0,
    newCount: 0,
    convertedCount: 0,
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadLeads()
  },

  onPullDownRefresh() {
    api.clearCache('GET:/dealer/leads')
    this.loadLeads().finally(function() {
      wx.stopPullDownRefresh()
    })
  },

  loadLeads() {
    this.setData({ loading: true })
    return api.getLeads().then(function(res) {
      var items = (res && res.items) || []
      var newCount = 0
      var convertedCount = 0
      var list = items.map(function(item) {
        var st = STATUS_MAP[item.status] || { text: item.status, cls: 'status-new' }
        if (item.status === 'new') newCount++
        if (item.status === 'converted') convertedCount++
        return Object.assign({}, item, {
          statusText: st.text,
          statusCls: st.cls,
          sourceText: SOURCE_MAP[item.source] || item.source || '官网',
        })
      })
      this.setData({
        list: list,
        total: (res && res.total) || list.length,
        isEmpty: list.length === 0,
        newCount: newCount,
        convertedCount: convertedCount,
        loading: false,
      })
    }.bind(this)).catch(function() {
      wx.showToast({ title: '线索加载失败', icon: 'none' })
      this.setData({ isEmpty: true, list: [], loading: false })
    }.bind(this))
  },

  updateStatus(e) {
    var leadId = e.currentTarget.dataset.id
    var newStatus = e.currentTarget.dataset.status
    var st = STATUS_MAP[newStatus]
    if (!st) return

    var idx = -1
    var list = this.data.list
    var leadIdNum = Number(leadId)
    for (var i = 0; i < list.length; i++) {
      if (Number(list[i].lead_id) === leadIdNum) { idx = i; break }
    }
    if (idx === -1) return

    var oldItem = list[idx]
    if (oldItem.status === newStatus) return

    // 增量计算统计数
    var newCount = this.data.newCount
    var convertedCount = this.data.convertedCount
    if (oldItem.status === 'new') newCount--
    if (oldItem.status === 'converted') convertedCount--
    if (newStatus === 'new') newCount++
    if (newStatus === 'converted') convertedCount++

    // 保存旧值用于回滚
    var oldNewCount = this.data.newCount
    var oldConvertedCount = this.data.convertedCount

    // 乐观更新：只改这一条
    var updateData = {}
    updateData['list[' + idx + '].status'] = newStatus
    updateData['list[' + idx + '].statusText'] = st.text
    updateData['list[' + idx + '].statusCls'] = st.cls
    updateData['newCount'] = newCount
    updateData['convertedCount'] = convertedCount
    this.setData(updateData)

    // 后台调API，失败则回滚
    var self = this
    api.updateLeadStatus(leadId, newStatus).catch(function() {
      var rollback = {}
      rollback['list[' + idx + '].status'] = oldItem.status
      rollback['list[' + idx + '].statusText'] = oldItem.statusText
      rollback['list[' + idx + '].statusCls'] = oldItem.statusCls
      rollback['newCount'] = oldNewCount
      rollback['convertedCount'] = oldConvertedCount
      self.setData(rollback)
      wx.showToast({ title: '更新失败', icon: 'none' })
    })
  },
})
