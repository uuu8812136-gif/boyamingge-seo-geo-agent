// 内容详情页：查看内容并确认/驳回
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    publication_id: '',
    detail: null,
    loading: true,
    submitting: false,
    eeatDimensions: [],
  },

  onLoad(options) {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.setData({ publication_id: options.publication_id || '' })
    this.loadDetail()
  },

  loadDetail() {
    this.setData({ loading: true })
    api.getPublicationDetail(this.data.publication_id).then(function(res) {
      // 解析 EEAT breakdown 为进度条数据
      var eeatDimensions = []
      if (res.eeat_breakdown) {
        var labels = {
          experience: '经验性',
          expertise: '专业性',
          authoritativeness: '权威性',
          trustworthiness: '可信度',
        }
        var keys = Object.keys(res.eeat_breakdown)
        for (var i = 0; i < keys.length; i++) {
          var key = keys[i]
          var score = res.eeat_breakdown[key]
          eeatDimensions.push({
            key: key,
            label: labels[key] || key,
            score: score,
            color: score >= 80 ? '#047857' : score >= 70 ? '#1a365d' : score >= 60 ? '#b8860b' : '#b91c1c',
          })
        }
      }
      this.setData({ detail: res, eeatDimensions: eeatDimensions, loading: false })
    }.bind(this)).catch(function(err) {
      var msg = (err && err.data && err.data.detail) || '加载失败'
      wx.showToast({ title: msg, icon: 'none' })
      this.setData({ loading: false })
    }.bind(this))
  },

  // 确认发布
  onConfirm() {
    this.submit('confirm', '确认要发布这条内容吗？')
  },

  // 驳回
  onReject() {
    this.submit('reject', '确认要驳回这条内容吗？')
  },

  submit(action, content) {
    if (this.data.submitting) return
    wx.showModal({
      title: '操作确认',
      content: content,
      success: function(res) {
        if (!res.confirm) return
        this.doSubmit(action)
      }.bind(this),
    })
  },

  doSubmit(action) {
    this.setData({ submitting: true })
    api.confirmPublication(this.data.publication_id, action).then(function(res) {
      wx.showToast({ title: res.message || '操作成功', icon: 'success' })
      setTimeout(function() {
        wx.navigateBack()
      }, 800)
    }).catch(function(err) {
      var msg = (err && err.data && err.data.detail) || '操作失败'
      wx.showToast({ title: msg, icon: 'none' })
    }).finally(function() {
      this.setData({ submitting: false })
    }.bind(this))
  },
})
