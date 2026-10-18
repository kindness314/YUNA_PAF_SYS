<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// ?fullscreen=1 投屏模式：隐藏侧栏（PLAN.md 第 11 节"现场模式"）
const isFullscreen = computed(() => route.query.fullscreen === '1')

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside v-if="!isFullscreen" width="210px" class="aside">
      <div class="brand">YUNA PAF 招新</div>
      <el-menu router :default-active="route.path" class="menu">
        <el-menu-item index="/">
          <el-icon><DataLine /></el-icon>概览
        </el-menu-item>
        <el-menu-item index="/applications">
          <el-icon><List /></el-icon>报名管理
        </el-menu-item>
        <el-menu-item index="/form-builder">
          <el-icon><SetUp /></el-icon>表单设计
        </el-menu-item>
        <el-menu-item index="/queue">
          <el-icon><Bell /></el-icon>面试现场
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span v-if="isFullscreen">现场投屏模式</span>
        </div>
        <el-dropdown @command="onLogout">
          <span class="user">
            {{ auth.displayName || '未登录' }}（{{ auth.role }}）
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}
.brand {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}
.menu {
  border-right: none;
}
.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.user {
  cursor: pointer;
  color: #409eff;
}
.main {
  padding: 16px;
}
</style>
