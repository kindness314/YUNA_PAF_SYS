<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const logged = computed(() => !!localStorage.getItem('token'))
const username = computed(() => localStorage.getItem('username') ?? '')

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  router.go(0)
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="网络信息协会招新" />
    <van-cell-group inset class="card">
      <van-cell title="当前用户" :value="logged ? username : '未登录'" />
    </van-cell-group>
    <van-grid :column-num="2" clickable class="card">
      <van-grid-item icon="edit" text="我要报名" to="/apply" />
      <van-grid-item icon="notes-o" text="笔试答卷" to="/exam" />
    </van-grid>
    <div class="actions">
      <van-button v-if="!logged" type="primary" block round @click="router.push('/login')">
        学号登录
      </van-button>
      <van-button v-else plain type="default" block round @click="logout">退出登录</van-button>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
}
.card {
  margin-top: 16px;
}
.actions {
  margin: 32px 24px 0;
}
</style>
