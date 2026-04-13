// 由于使用 CDN，使用全局 VueRouter
const { createRouter, createWebHashHistory } = VueRouter

// 定义路由
const routes = [
    {
        path: '/',
        redirect: '/library'
    },
    {
        path: '/login',
        component: () => import('./views/Login.js'),
        meta: { requiresGuest: true }
    },
    {
        path: '/register',
        component: () => import('./views/Register.js'),
        meta: { requiresGuest: true }
    },
    {
        path: '/library',
        component: () => import('./views/Library.js'),
        meta: { requiresAuth: true }
    }
]

const router = createRouter({
    history: createWebHashHistory(),
    routes
})

export default router