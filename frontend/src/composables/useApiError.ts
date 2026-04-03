import { useMessage } from 'naive-ui'
import type { AxiosError } from 'axios'

export function useApiError() {
  const message = useMessage()

  function handleError(err: unknown, fallback = '操作失败，请重试') {
    const axiosErr = err as AxiosError<{ detail?: string }>
    const detail = axiosErr.response?.data?.detail
    message.error(detail || fallback)
  }

  return { handleError }
}