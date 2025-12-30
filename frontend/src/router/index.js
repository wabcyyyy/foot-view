import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Result from '../views/Result.vue'
import Login from '../views/Login.vue'
import MetricDetail from '../views/MetricDetail.vue'
import axios from 'axios'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true }
  },
  {
    path: '/result/:filename',
    name: 'Result',
    component: Result,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/metric/:metricName',
    name: 'MetricDetail',
    component: MetricDetail,
    props: true,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    try {
      const response = await axios.get('/api/user/current');
      if (response.data.is_authenticated) {
        next();
      } else {
        next({ name: 'Login' });
      }
    } catch (error) {
      next({ name: 'Login' });
    }
  } else {
    next();
  }
});

export default router
