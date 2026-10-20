import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/apply', name: 'apply', component: () => import('../views/ApplyView.vue') },
    { path: '/answer', name: 'answer', component: () => import('../views/AnswerView.vue') },
    { path: '/exam', name: 'exam', component: () => import('../views/ExamView.vue') },
  ],
})

router.beforeEach((to) => {
  if (to.name !== 'home' && to.name !== 'login' && !localStorage.getItem('token')) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
