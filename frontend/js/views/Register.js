import { useAuthStore } from '../stores/auth.js'

export default {
    template: `
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6 col-lg-4">
                    <div class="card shadow">
                        <div class="card-body">
                            <h3 class="card-title text-center mb-4">
                                <i class="bi bi-person-plus"></i> 用户注册
                            </h3>
                            
                            <div v-if="error" class="alert alert-danger">{{ error }}</div>
                            <div v-if="success" class="alert alert-success">{{ success }}</div>
                            
                            <form @submit.prevent="handleRegister">
                                <div class="mb-3">
                                    <label for="email" class="form-label">邮箱</label>
                                    <input 
                                        type="email" 
                                        class="form-control" 
                                        id="email" 
                                        v-model="email"
                                        required
                                    >
                                </div>
                                
                                <div class="mb-3">
                                    <label for="username" class="form-label">用户名</label>
                                    <input 
                                        type="text" 
                                        class="form-control" 
                                        id="username" 
                                        v-model="username"
                                        required
                                    >
                                </div>
                                
                                <div class="mb-3">
                                    <label for="displayName" class="form-label">显示名称</label>
                                    <input 
                                        type="text" 
                                        class="form-control" 
                                        id="displayName" 
                                        v-model="displayName"
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
                                        minlength="8"
                                    >
                                    <small class="text-muted">密码至少8个字符</small>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="confirmPassword" class="form-label">确认密码</label>
                                    <input 
                                        type="password" 
                                        class="form-control" 
                                        id="confirmPassword" 
                                        v-model="confirmPassword"
                                        required
                                    >
                                </div>
                                
                                <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                                    <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                                    {{ loading ? '注册中...' : '注册' }}
                                </button>
                            </form>
                            
                            <div class="text-center mt-3">
                                <router-link to="/login">已有账号？立即登录</router-link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    data() {
        return {
            email: '',
            username: '',
            displayName: '',
            password: '',
            confirmPassword: '',
            loading: false,
            error: null,
            success: null
        }
    },

    methods: {
        async handleRegister() {
            this.error = null
            this.success = null

            // 验证密码
            if (this.password !== this.confirmPassword) {
                this.error = '两次输入的密码不一致'
                return
            }

            if (this.password.length < 8) {
                this.error = '密码长度至少为8个字符'
                return
            }

            this.loading = true

            try {
                const authStore = useAuthStore()
                await authStore.register(
                    this.email,
                    this.username,
                    this.password,
                    this.displayName || this.username
                )

                this.success = '注册成功！3秒后跳转到登录页...'

                setTimeout(() => {
                    this.$router.push('/login')
                }, 3000)

            } catch (error) {
                this.error = error.message || '注册失败，请稍后重试'
            } finally {
                this.loading = false
            }
        }
    }
}