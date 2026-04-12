export function formatCount(num: number | undefined): string {
  if (!num) return '0'
  return num >= 10000 ? (num / 10000).toFixed(1) + '万' : num.toString()
}

export function formatPubDate(ts: number | undefined): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}

export function formatTimestamp(ts: number | undefined): string {
  if (!ts) return ''
  const date = new Date(ts * 1000)
  return date.toLocaleDateString('zh-CN') + ' ' + 
         date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export function getDynamicTypeLabel(type: number): string {
  const map: Record<number, string> = { 
    1: '转发', 2: '图文', 4: '文字', 8: '视频', 64: '专栏' 
  }
  return map[type] || '动态'
}