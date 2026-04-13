import { defineStore } from 'https://unpkg.com/pinia@2.1.7/dist/pinia.esm-browser.js'

const API_BASE = 'http://localhost:8000/api/v1'

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        accessToken: localStorage.getItem('accessToken') || null,
        refreshToken: localStorage.getItem('refreshToken') || null
    }),

    getters: {
        isAuthenticated: (state) => !!state.accessToken,
        isAdmin: (state) => state.user?.role === 'admin'
    },

    actions: {
        init() {
            if (this.accessToken) {
                this.fetchUser()
            }
        },

        async login(username, password) {
            try {
                const response = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                })

                if (!response.ok) {
                    throw new Error('登录失败')
                }

                const data = await response.json()
                this.accessToken = data.access_token
                this.refreshToken = data.refresh_token

                localStorage.setItem('accessToken', this.accessToken)
                localStorage.setItem('refreshToken', this.refreshToken)

                await this.fetchUser()
                return true
            } catch (error) {
                console.error('Login error:', error)
                throw error
            }
        },

        async register(email, username, password, displayName) {
            try {
                const response = await fetch(`${API_BASE}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email,
                        username,
                        password,
                        display_name: displayName
                    })
                })

                if (!response.ok) {
                    const error = await response.json()
                    throw new Error(error.detail || '注册失败')
                }

                return true
            } catch (error) {
                console.error('Register error:', error)
                throw error
            }
        },

        async fetchUser() {
            if (!this.accessToken) return

            try {
                const response = await fetch(`${API_BASE}/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${this.accessToken}`
                    }
                })

                if (response.ok) {
                    this.user = await response.json()
                } else if (response.status === 401) {
                    await this.refreshAccessToken()
                }
            } catch (error) {
                console.error('Fetch user error:', error)
            }
        },

        async refreshAccessToken() {
            if (!this.refreshToken) {
                this.logout()
                return
            }

            try {
                const response = await fetch(`${API_BASE}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: this.refreshToken })
                })

                if (response.ok) {
                    const data = await response.json()
                    this.accessToken = data.access_token
                    this.refreshToken = data.refresh_token

                    localStorage.setItem('accessToken', this.accessToken)
                    localStorage.setItem('refreshToken', this.refreshToken)

                    await this.fetchUser()
                } else {
                    this.logout()
                }
            } catch (error) {
                console.error('Refresh token error:', error)
                this.logout()
            }
        },

        logout() {
            this.user = null
            this.accessToken = null
            this.refreshToken = null
            localStorage.removeItem('accessToken')
            localStorage.removeItem('refreshToken')
        }
    }
})