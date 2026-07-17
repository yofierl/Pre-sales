import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/projects',
      name: 'ProjectList',
      component: () => import('@/views/ProjectListView.vue'),
    },
    {
      path: '/projects/:id',
      name: 'ProjectWorkspace',
      component: () => import('@/views/ProjectWorkspaceView.vue'),
    },
  ],
})

export default router
