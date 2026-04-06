<template>
  <div class="bilibili-login">
    <div class="login-card">
      <h2>B站账号登录</h2>
      <p class="description">扫码登录以获取B站动态和视频访问权限</p>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error">
        <p>{{ error }}</p>
        <button @click="generateQrcode" class="btn btn-primary">重试</button>
      </div>

      <div v-else-if="qrcodeUrl" class="qrcode-container">
        <img :src="qrcodeUrl" alt="B站登录二维码" class="qrcode" />
        <p class="hint">请使用B站APP扫码登录</p>
        
        <button @click="generateQrcode" class="btn btn-secondary">刷新二维码</button>

        <div v-if="status === 'scanned'" class="scanned">
          <p>已扫描，请在手机上确认登录</p>
        </div>

        <div v-if="status === 'confirmed'" class="success">
          <p>登录成功！</p>
          <p class="sub">正在获取权限...</p>
        </div>
      </div>

      <div v-if="hasCredential" class="has-credential">
        <p>您已绑定B站账号</p>
        <button @click="unbindCredential" class="btn btn-danger">解除绑定</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router' 
import { bilibiliApi, type QrCodeResponse, type QrCodeStatusResponse } from '@/api/bilibili'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const qrcodeUrl = ref('')
const sessionId = ref('')
const status = ref('')
const hasCredential = ref(false)
const polling = ref(false)

async function generateQrcode() {
  loading.value = true
  error.value = ''

  try {
    const res = await bilibiliApi.generateQrcode()
    const data: QrCodeResponse = res.data
    sessionId.value = data.session_id
    qrcodeUrl.value = data.qrcode_url
    status.value = 'new'
    startPolling()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '生成二维码失败'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  polling.value = true
  pollStatus()
}

function pollStatus() {
  if (!sessionId.value || status.value === 'confirmed' || status.value === 'timeout') {
    polling.value = false
    return
  }

  setTimeout(async () => {
    try {
      const res = await bilibiliApi.checkQrcodeStatus(sessionId.value)
      const data: QrCodeStatusResponse = res.data
      status.value = data.status

      if (data.status === 'confirmed') {
        polling.value = false
        hasCredential.value = true
      } else if (data.status === 'timeout') {
        error.value = '二维码已过期，请重新生成'
        polling.value = false
      } else if (data.status === 'error') {
        error.value = data.message || '登录失败'
        polling.value = false
      } else {
        pollStatus()
      }
    } catch {
      pollStatus()
    }
  }, 2000)
}

async function unbindCredential() {
  // TODO: 实现解除绑定
  hasCredential.value = false
}

onMounted(async () => {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  
  if (!authStore.canAccessBilibili) {
    router.push('/')
    return
  }

  // 检查是否已有凭证
  // hasCredential.value = await checkCredential()
  await generateQrcode()
})

onUnmounted(() => {
  polling.value = false
})
</script>

<style scoped>
.bilibili-login {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.login-card {
  background: transparent;
  padding: 40px;
  max-width: 400px;
  width: 100%;
  text-align: center;
}

h2 {
  margin: 0 0 8px;
  color: #fff;
}

.description {
  color: #71717a;
  margin-bottom: 24px;
}

.loading {
  padding: 40px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #3f3f46;
  border-top: 3px solid #ec4899;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  color: #f87171;
}

.qrcode-container {
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.qrcode {
  width: 200px;
  height: 200px;
  border: 1px solid #3f3f46;
  border-radius: 8px;
  display: block;
}

.hint {
  color: #71717a;
  margin-top: 16px;
}

.scanned {
  color: #ec4899;
  margin-top: 16px;
}

.success {
  color: #4ade80;
  margin-top: 16px;
}

.sub {
  font-size: 12px;
  opacity: 0.7;
  color: #71717a;
}

.has-credential {
  padding: 20px;
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid #4ade80;
  border-radius: 8px;
  color: #4ade80;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background: #ec4899;
  color: white;
}

.btn-primary:hover {
  background: #ec4899;
  opacity: 0.9;
}

.btn-danger {
  background: #f43f5e;
  color: white;
}

.btn-secondary {
  background: #3f3f46;
  color: white;
  margin-top: 16px;
}

.btn-secondary:hover {
  background: #52525b;
}
</style>
