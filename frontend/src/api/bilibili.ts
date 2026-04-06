import axios from '@/api'

export interface QrCodeResponse {
  session_id: string
  qrcode_url: string
}

export interface QrCodeStatusResponse {
  status: 'new' | 'scanned' | 'confirmed' | 'timeout' | 'error' | 'not_found'
  message?: string
  credential?: {
    sessdata: string
    bili_jct: string
    buvid3: string
    dedeuserid?: string
  }
}

export const bilibiliApi = {
  generateQrcode: () =>
    axios.post<QrCodeResponse>('/api/bilibili/auth/qrcode'),

  checkQrcodeStatus: (sessionId: string) =>
    axios.get<QrCodeStatusResponse>(`/api/bilibili/auth/qrcode/${sessionId}`),
}
