import { Ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import { userChannelApi, type Channel } from '@/api'
import { useMultiviewStore } from '@/stores/multiview'
import { useMutation, useQueryClient } from '@tanstack/vue-query'

export function useChannelActions(channel: Ref<Channel | null | undefined>) {
  const message = useMessage()
  const router  = useRouter()
  const store   = useMultiviewStore()
  const queryClient = useQueryClient()
  
  const likeMutation = useMutation({
    // 1. 执行 API 请求
    mutationFn: async ({ id, isLiked }: { id: number; isLiked: boolean }) => {
      if (isLiked) return await userChannelApi.unlike(id)
      return await userChannelApi.like(id)
    },
    // 2. 乐观更新：在请求发出瞬间立刻修改本地缓存
    onMutate: async ({ isLiked }) => {
      // 撤销正在进行的请求，防止数据覆盖
      await queryClient.cancelQueries({ queryKey: ['channel', channel.value?.id] })

      // 保存旧值，用于出错回滚
      const previousChannel = queryClient.getQueryData(['channel', channel.value?.id])

      // 快速更新本地 UI
      if (channel.value) {
        queryClient.setQueryData(['channel', channel.value.id], (old: any) => ({
          ...old,
          is_liked: !isLiked
        }))
      }

      return { previousChannel }
    },
    // 3. 如果失败，回滚到旧值
    onError: (_err, _variables, context) => {
      if (context?.previousChannel) {
        queryClient.setQueryData(['channel', channel.value?.id], context.previousChannel)
      }
      message.error('操作失败')
    },
    // 4. 不管成功失败，都标记为失效，从服务器拉取最新状态（确保同步）
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['channel', channel.value?.id] })
    },
    onSuccess: (_data, variables) => {
      message.success(variables.isLiked ? '已取消收藏' : '已添加到收藏')
    }
  })

  const blockMutation = useMutation({
    mutationFn: async ({ id, isBlocked }: { id: number; isBlocked: boolean }) => {
      if (isBlocked) return await userChannelApi.unblock(id)
      return await userChannelApi.block(id)
    },

    onMutate: async ({ isBlocked }) => {
      await queryClient.cancelQueries({ queryKey: ['channel', channel.value?.id] })

      const previousChannel = queryClient.getQueryData(['channel', channel.value?.id])

      if (channel.value) {
        queryClient.setQueryData(['channel', channel.value.id], (old: any) => ({
          ...old,
          is_blocked: !isBlocked
        }))
      }

      return { previousChannel }
    },

    // 3. 错误处理：回滚
    onError: (_err, _variables, context) => {
      if (context?.previousChannel) {
        queryClient.setQueryData(['channel', channel.value?.id], context.previousChannel)
      }
      message.error('操作失败，请稍后重试')
    },

    // 4. 无论成功失败，都刷新服务器最新数据
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['channel', channel.value?.id] })
    },

    // 5. 成功提示
    onSuccess: (_data, variables) => {
      message.success(variables.isBlocked ? '已取消屏蔽' : '已屏蔽该频道')
    }
  })

  function toggleLike() {
    if (!channel.value) return
    likeMutation.mutate({ 
      id: channel.value.id, 
      isLiked: !!channel.value.is_liked 
    })
  }

 function toggleBlock() {
    if (!channel.value) {
      message.warning('频道信息未加载')
      return
    }

    blockMutation.mutate({
      id: channel.value.id,
      // 注意：这里使用 !! 确保转换为 boolean，且字段名需与 API 返回的一致（这里假设是 is_blocked）
      isBlocked: !!channel.value.is_blocked 
    })
  }

  function addToMultiview(videoId?: string) {
    if (!channel.value) return
    const id       = videoId ?? channel.value.channel_id
    const platform = channel.value.platform as 'youtube' | 'bilibili'
    store.addFromVideoId(platform, id)
    router.push({ name: 'MultiView' })
  }

  return { toggleLike, toggleBlock,isLikeLoading: likeMutation.isPending, addToMultiview }
}