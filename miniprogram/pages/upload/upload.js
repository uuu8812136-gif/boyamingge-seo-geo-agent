// 素材上传页
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    list: [],
    loading: true,
    uploading: false,
    uploadProgress: 0,
    isEmpty: false,
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadList()
  },

  onPullDownRefresh() {
    api.clearCache('GET:/dealer/materials')
    this.loadList().finally(function() {
      wx.stopPullDownRefresh()
    })
  },

  loadList() {
    this.setData({ loading: true })
    return api.getMaterials().then(function(res) {
      var list = (res && res.items) || []
      this.setData({ list: list, isEmpty: list.length === 0, loading: false })
    }.bind(this)).catch(function() {
      this.setData({ loading: false, isEmpty: true, list: [] })
    }.bind(this))
  },

  // 选择图片
  chooseImage(e) {
    if (this.data.uploading) return
    var source = e.currentTarget.dataset.source
    var sourceType = source === 'camera' ? ['camera'] : ['album']
    var self = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: sourceType,
      sizeType: ['compressed'],
      success: function(res) {
        self.uploadFile(res.tempFiles[0].tempFilePath)
      },
    })
  },

  // 上传素材文件（进度节流：每10%更新一次）
  uploadFile(filePath) {
    this.setData({ uploading: true, uploadProgress: 0 })
    var lastReported = 0
    var self = this
    api.uploadMaterial(filePath, function(progress) {
      var p = Math.round(progress)
      // 每10%更新一次UI，减少setData频率
      if (p - lastReported >= 10 || p >= 100) {
        lastReported = p
        self.setData({ uploadProgress: p })
      }
    }).then(function() {
      self.setData({ uploading: false, uploadProgress: 0 })
      wx.showToast({ title: '上传成功', icon: 'success' })
      self.loadList()
    }).catch(function() {
      wx.showToast({ title: '上传失败', icon: 'none' })
      self.setData({ uploading: false, uploadProgress: 0 })
    })
  },

  // 预览素材大图
  onPreview(e) {
    var url = e.currentTarget.dataset.url
    var urls = this.data.list
      .map(function(item) { return item.oss_url || item.url || item.thumbnail || '' })
      .filter(function(u) { return u })
    if (url && urls.length) {
      wx.previewImage({ current: url, urls: urls })
    }
  },
})
