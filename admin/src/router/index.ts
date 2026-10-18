import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      component: () => import('../layouts/AdminLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '概览' },
        },
        {
          path: 'applications',
          name: 'applications',
          component: () => import('../views/ApplicationsView.vue'),
          meta: { title: '报名管理' },
        },
        {
          path: 'form-builder',
          name: 'formBuilder',
          component: () => import('../views/FormBuilderView.vue'),
          meta: { title: '表单设计' },
        },
        {
          path: 'queue',
          name: 'queue',
          component: () => import('../views/QueueBoardView.vue'),
          meta: { title: '面试现场' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!localStorage.getItem('token')) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
