var Utils = {
  formatDuration: function(s) {
    if (!s && s !== 0) return '--:--';
    var m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  },
  formatTime: function(s) {
    if (!s || isNaN(s)) return '0:00';
    var m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  },
  formatDate: function(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('zh-CN');
  },
  formatDateTime: function(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('zh-CN');
  },
  formatRelativeTime: function(iso) {
    if (!iso) return '';
    var diff = Date.now() - new Date(iso).getTime();
    var m = Math.floor(diff / 60000);
    var h = Math.floor(diff / 3600000);
    var d = Math.floor(diff / 86400000);
    if (m < 1)  return '刚刚';
    if (m < 60) return m + '分钟前';
    if (h < 24) return h + '小时前';
    if (d < 7)  return d + '天前';
    return Utils.formatDate(iso);
  },
  formatNumber: function(n) {
    if (!n) return '0';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
  },
  getCoverUrl: function(id) {
    return API_BASE + '/media/cover/' + id + '?size=sm';
  },
  handleImageError: function(e) {
    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40'%3E%3Crect width='40' height='40' fill='%23333'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.35em' fill='%23888' font-size='18'%3E%E2%99%AA%3C/text%3E%3C/svg%3E";
  },
  getActivityText: function(t) {
    var map = { play_start: '播放', play_end: '结束', pause: '暂停', seek: '跳转', download: '下载' };
    return map[t] || t;
  },
  getActivityBadge: function(t) {
    var map = { play_start: 'bg-success', play_end: 'bg-secondary', pause: 'bg-warning text-dark', seek: 'bg-info text-dark', download: 'bg-primary' };
    return map[t] || 'bg-secondary';
  }
};