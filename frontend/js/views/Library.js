import { usePlayerStore } from '../stores/player.js'
import { useAuthStore } from '../stores/auth.js'

const API_BASE = 'http://localhost:8000/api/v1'

export default {
    template: `
        <div class="container-fluid mt-3">
            <div class="row">
                <div class="col-12">
                    <h2><i class="bi bi-music-note-list"></i> 音乐库</h2>
                    
                    <!-- 搜索栏 -->
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <input 
                                type="text" 
                                class="form-control" 
                                placeholder="搜索歌曲、艺术家或专辑..." 
                                v-model="searchQuery"
                                @input="search"
                            >
                        </div>
                    </div>
                    
                    <!-- 歌曲列表 -->
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th style="width: 50px">#</th>
                                    <th>标题</th>
                                    <th>艺术家</th>
                                    <th>专辑</th>
                                    <th style="width: 100px">时长</th>
                                    <th style="width: 100px">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(track, index) in tracks" :key="track.id" 
                                    @dblclick="playTrack(track, index)">
                                    <td>{{ (page - 1) * pageSize + index + 1 }}</td>
                                    <td>
                                        <div class="d-flex align-items-center">
                                            <img 
                                                :src="getCoverUrl(track.id)" 
                                                class="me-2"
                                                style="width: 40px; height: 40px; object-fit: cover;"
                                                @error="handleImageError"
                                            >
                                            {{ track.title }}
                                        </div>
                                    </td>
                                    <td>{{ track.artist || '未知艺术家' }}</td>
                                    <td>{{ track.album || '未知专辑' }}</td>
                                    <td>{{ formatDuration(track.duration) }}</td>
                                    <td>
                                        <button class="btn btn-sm btn-primary" @click="playTrack(track, index)">
                                            <i class="bi bi-play-fill"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 分页 -->
                    <nav v-if="totalPages > 1">
                        <ul class="pagination">
                            <li class="page-item" :class="{ disabled: page === 1 }">
                                <a class="page-link" href="#" @click.prevent="changePage(page - 1)">上一页</a>
                            </li>
                            <li class="page-item disabled">
                                <span class="page-link">{{ page }} / {{ totalPages }}</span>
                            </li>
                            <li class="page-item" :class="{ disabled: page === totalPages }">
                                <a class="page-link" href="#" @click.prevent="changePage(page + 1)">下一页</a>
                            </li>
                        </ul>
                    </nav>
                    
                    <!-- 加载状态 -->
                    <div v-if="loading" class="text-center">
                        <div class="spinner-border" role="status">
                            <span class="visually-hidden">加载中...</span>
                        </div>
                    </div>
                    
                    <!-- 空状态 -->
                    <div v-if="!loading && tracks.length === 0" class="text-center text-muted">
                        <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                        <p>暂无音乐文件，请先添加音乐到 media 目录并扫描</p>
                    </div>
                </div>
            </div>
        </div>
    `,

    data() {
        return {
            tracks: [],
            loading: false,
            page: 1,
            pageSize: 50,
            total: 0,
            totalPages: 0,
            searchQuery: '',
            searchTimeout: null
        }
    },

    mounted() {
        this.loadTracks()
    },

    methods: {
        async loadTracks() {
            this.loading = true

            try {
                const authStore = useAuthStore()
                const params = new URLSearchParams({
                    page: this.page,
                    page_size: this.pageSize,
                    sort_by: 'title',
                    sort_order: 'asc'
                })

                if (this.searchQuery) {
                    params.append('search', this.searchQuery)
                }

                const response = await fetch(`${API_BASE}/tracks?${params}`, {
                    headers: {
                        'Authorization': `Bearer ${authStore.accessToken}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    this.tracks = data.items
                    this.total = data.total
                    this.totalPages = data.total_pages
                }
            } catch (error) {
                console.error('Load tracks error:', error)
            } finally {
                this.loading = false
            }
        },

        search() {
            clearTimeout(this.searchTimeout)
            this.searchTimeout = setTimeout(() => {
                this.page = 1
                this.loadTracks()
            }, 300)
        },

        changePage(page) {
            if (page >= 1 && page <= this.totalPages) {
                this.page = page
                this.loadTracks()
            }
        },

        playTrack(track, index) {
            const playerStore = usePlayerStore()

            // 创建播放队列
            const queue = this.tracks.slice(index).concat(this.tracks.slice(0, index))
            playerStore.setQueue(queue, 0)
        },

        getCoverUrl(trackId) {
            return `${API_BASE}/media/cover/${trackId}?size=sm`
        },

        handleImageError(e) {
            e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"%3E%3Crect width="40" height="40" fill="%23e9ecef"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%236c757d" font-size="12"%3E♪%3C/text%3E%3C/svg%3E'
        },

        formatDuration(seconds) {
            if (!seconds) return '--:--'
            const mins = Math.floor(seconds / 60)
            const secs = Math.floor(seconds % 60)
            return `${mins}:${secs.toString().padStart(2, '0')}`
        }
    }
}