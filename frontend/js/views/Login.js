import { useAuthStore } from '../stores/auth.js'

export default {
    template: `
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6 col-lg-4">
                    <div class="card shadow">
                        <div class="card-body">
                            <h3 class="card-title text-center mb-4">
                                <i class="bi bi-vinyl-fill"></i> Music Stream
                            </h3>
                            <h5 class="card-subtitle text-center text-muted mb-4">用户登录</h5>
                            
                            <div v-if="error" class="alert alert-danger">{{ error }}</div>
                            
                            <form @submit.prevent="handleLogin">
                                <div class="mb-3">
                                    <label for="username" class="form-label">用户名</label>
                                    <input 
                                        type="text" 
                                        class="form-control" 
                                        id="username" 
                                        v-model="username"
                                        required
                                        autofocus
                                    >
                                </div>
                                
                                <div class="mb-3">
                                    <label for="password" class="form-label">密码</label>
                                    <input 
                                        type="password" 
                                        class="form-control" 
                                        id="password" 
                                        v-model="password"
                                        required
                                    >
                                </div>
                                
                                <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                                    <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                                    {{ loading ? '登录中...' : '登录' }}
                                </button>
                            </form>
                            
                            <div class="text-center mt-3">
                                <router-link to="/register">还没有账号？立即注册</router-link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    data() {
        return {
            username: '',
            password: '',
            loading: false,
            error: null
        }
    },

    methods: {
        async handleLogin() {
            this.loading = true
            this.error = null

            try {
                const authStore = useAuthStore()
                await authStore.login(this.username, this.password)
                this.$router.push('/library')
            } catch (error) {
                this.error = error.message || '登录失败，请检查用户名和密码'
            } finally {
                this.loading = false
            }
        }
    }
}