import { Ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import { userChannelApi, type Channel } from '@/api'
import { useMultiviewStore } from '@/stores/multiview'

export function useChannelActions(channel: Ref<Channel | null>) {
  const message = useMessage()
  const router  = useRouter()
  const store   = useMultiviewStore()

  async function toggleLike() {
    if (!channel.value) return
    const prev = channel.value.is_liked
    channel.value.is_liked = !prev
    try {
      if (!prev) await userChannelApi.like(channel.value.id)
      else       await userChannelApi.unlike(channel.value.id)
      message.success(prev ? '已取消收藏' : '已添加到收藏')
    } catch {
      channel.value.is_liked = prev
      message.error('操作失败')
    }
  }

  async function toggleBlock() {
    if (!channel.value) return
    const prev = channel.value.is_blocked
    channel.value.is_blocked = !prev
    try {
      if (!prev) await userChannelApi.block(channel.value.id)
      else       await userChannelApi.unblock(channel.value.id)
      message.success(prev ? '已取消屏蔽' : '已屏蔽频道')
    } catch {
      channel.value.is_blocked = prev
      message.error('操作失败')
    }
  }

  function addToMultiview(videoId?: string) {
    if (!channel.value) return
    const id       = videoId ?? channel.value.channel_id
    const platform = channel.value.platform as 'youtube' | 'bilibili'
    store.addFromVideoId(platform, id)
    router.push({ name: 'MultiView' })
  }

  return { toggleLike, toggleBlock, addToMultiview }
}