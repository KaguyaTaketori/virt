import { ref } from 'vue'
import { channelApi } from '@/api'


interface ContentNode {
  type: 'text' | 'emoji' | 'at'
  text: string
  url?: string  // 表情包 URL
  rid?: string  // AT 用户的 UID
}

interface Dynamic {
  dynamic_id: string
  url: string
  uid: string
  uname: string
  face: string
  type: number
  timestamp: number
  content_nodes: ContentNode[]
  images: string[]
  repost_content: string | null
  stat: {
    forward: number
    comment: number
    like: number
  }
  topic: string
  is_top: boolean
}

interface BilibiliVideo {
  aid: number;           // 稿件id
  bvid: string;          // 视频bvid
  title: string;         // 标题
  pic: string;           // 封面图
  duration: string;      // 时长 (如 "03:56")
  play: number;          // 播放量
  pubdate: number;       // 发布时间戳
  reply: number;         // 评论数
  like: number;          // 点赞数
  coin?: number;
  favorite?: number;
  share?: number;
}
export function useBilibiliData() {
  const dynamics        = ref<Dynamic[]>([])
  const videos          = ref<BilibiliVideo[]>([])
  const info            = ref<any>(null)
  const nextOffset      = ref('')
  const loading         = ref(false)
  const hasMore         = ref(true)

  async function fetch(channelId: number, offset = '', append = false) {
    if (loading.value) return
    loading.value = true
    try {
      const { data } = await channelApi.getBilibili(channelId, offset, 12)
      if (!append) {
        info.value    = data.info
        dynamics.value = data.dynamics
        videos.value  = data.videos
      } else {
        dynamics.value = [...dynamics.value, ...data.dynamics]
      }
      nextOffset.value = data.next_offset || ''
      hasMore.value    = !!data.next_offset
    } catch (e) {
      console.error('Failed to fetch Bilibili data:', e)
    } finally {
      loading.value = false
    }
  }

  function loadMore(channelId: number) {
    if (!hasMore.value || !nextOffset.value) return
    fetch(channelId, nextOffset.value, true)
  }

  function reset() {
    dynamics.value = []; videos.value = []
    info.value = null; nextOffset.value = ''
    hasMore.value = true
  }

  return { dynamics, videos, info, nextOffset, loading, hasMore, fetch, loadMore, reset }
}