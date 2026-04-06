<template>
  <div class="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="w-16 h-16 rounded-xl bg-rose-600 flex items-center justify-center mx-auto mb-4">
          <span class="text-white text-2xl font-black">VL</span>
        </div>
        <h1 class="text-2xl font-bold text-white">登录</h1>
        <p class="text-zinc-400 mt-1">登录以访问更多功能</p>
      </div>

      <n-card>
        <n-form ref="formRef" :model="form" :rules="rules" @submit.prevent="isRegister ? handleRegister() : handleLogin()">
          <n-form-item path="username" label="用户名">
            <n-input v-model:value="form.username" placeholder="用户名" @keydown.enter="handleLogin" />
          </n-form-item>
          <n-form-item path="password" label="密码">
            <n-input v-model:value="form.password" type="password" placeholder="密码" show-password-on="click" @keydown.enter="handleLogin" />
          </n-form-item>
          <n-form-item v-if="isRegister" path="email" label="邮箱">
            <n-input v-model:value="form.email" placeholder="邮箱（可选）" @keydown.enter="handleRegister" />
          </n-form-item>
        </n-form>

        <div class="flex flex-col gap-3 mt-6">
          <n-button
            v-if="!isRegister"
            type="primary"
            block
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </n-button>
          <n-button
            v-if="!isRegister"
            block
            @click="isRegister = true"
          >
            注册
          </n-button>
          <n-button
            v-if="isRegister"
            type="primary"
            block
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </n-button>
          <n-button
            v-if="isRegister"
            block
            @click="isRegister = false"
          >
            返回登录
          </n-button>
        </div>

        <p v-if="loginError" class="text-red-500 text-sm mt-3 text-center">{{ loginError }}</p>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NCard, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

const isRegister = ref(false)
const loading = ref(false)
const loginError = ref('')

const form = reactive({
  username: '',
  password: '',
  email: '',
})

const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

async function handleLogin() {
  if (!form.username || !form.password) return
  loading.value = true
  loginError.value = ''

  const success = await authStore.login(form.username, form.password)
  
  if (success) {
    message.success('登录成功')
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } else {
    loginError.value = '用户名或密码错误'
  }
  loading.value = false
}

async function handleRegister() {
  if (!form.username || !form.password) return
  loading.value = true
  loginError.value = ''

  const success = await authStore.register(form.username, form.email, form.password)
  
  if (success) {
    message.success('注册成功')
    router.push('/')
  } else {
    loginError.value = '注册失败，用户名可能已存在'
  }
  loading.value = false
}
</script>