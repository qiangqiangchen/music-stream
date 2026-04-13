// 使用全局变量
const { createApp } = Vue
const { createPinia } = Pinia

// 由于使用 CDN，需要确保 VueRouter 可用
const router = VueRouter.createRouter({
    history: VueRouter.createWebHashHistory(),
    routes: [
        {
            path: '/',
            redirect: '/library'
        },
        {
            path: '/login',
            component: () => Promise.resolve(LoginComponent),
            meta: { requiresGuest: true }
        },
        {
            path: '/register',
            component: () => Promise.resolve(RegisterComponent),
            meta: { requiresGuest: true }
        },
        {
            path: '/library',
            component: () => Promise.resolve(LibraryComponent),
            meta: { requiresAuth: true }
        }
    ]
})

// 导入组件（稍后定义）
let LoginComponent, RegisterComponent, LibraryComponent

// 导入 Stores
import { useAuthStore } from './stores/auth.js'
import { usePlayerStore } from './stores/player.js'

// 导入 Components
import PlayerBar from './components/PlayerBar.js'

// 创建应用
const app = createApp({
    setup() {
        const authStore = useAuthStore()
        const playerStore = usePlayerStore()

        const logout = () => {
            authStore.logout()
            router.push('/login')
        }

        return {
            authStore,
            playerStore,
            logout
        }
    }
})

// 使用插件
const pinia = createPinia()
app.use(pinia)
app.use(router)

// 注册全局组件
app.component('PlayerBar', PlayerBar)

// 挂载应用
app.mount('#app')

// 初始化认证
const authStore = useAuthStore()
authStore.init()

// 导航守卫
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore()

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next('/login')
    } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
        next('/library')
    } else {
        next()
    }
})