<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showFailToast, showSuccessToast } from 'vant'
import { api, errText } from '../api/client'

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const displayName = ref('')
const router = useRouter()
const route = useRoute()

async function submit() {
  try {
    if (mode.value === 'register') {
      await api.post('/auth/register', {
        username: username.value,
        password: password.value,
        display_name: displayName.value || username.value,
      })
      showSuccessToast('注册成功')
    }
    const { data } = await api.post('/auth/login', {
      username: username.value,
      password: password.value,
    })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', username.value)
    router.push((route.query.redirect as string) || '/')
  } catch (e) {
    showFailToast(errText(e))
  }
}
</script>

<template>
  <div class="page">
    <h2 class="title">网络信息协会招新</h2>
    <van-form @submit="submit">
      <van-cell-group inset>
        <van-field
          v-model="username"
          label="学号"
          placeholder="注册后请用学号登录"
          :rules="[{ required: true, message: '请输入学号' }]"
        />
        <van-field
          v-model="password"
          type="password"
          label="密码"
          :rules="[{ required: true, message: '请输入密码' }]"
        />
        <van-field v-if="mode === 'register'" v-model="displayName" label="姓名" placeholder="选填" />
      </van-cell-group>
      <div class="btn">
        <van-button round block type="primary" native-type="submit">
          {{ mode === 'login' ? '登录' : '注册并登录' }}
        </van-button>
        <van-button
          round
          block
          plain
          type="primary"
          class="gap"
          @click="mode = mode === 'login' ? 'register' : 'login'"
        >
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </van-button>
      </div>
    </van-form>
  </div>
</template>

<style scoped>
.page {
  padding: 48px 0;
}
.title {
  text-align: center;
  margin: 24px 0;
}
.btn {
  margin: 24px 32px 0;
}
.gap {
  margin-top: 12px;
}
</style>
