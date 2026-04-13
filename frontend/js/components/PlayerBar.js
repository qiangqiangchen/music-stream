import { usePlayerStore } from '../stores/player.js'

export default {
    template: `
        <div class="player-bar fixed-bottom bg-dark text-white p-3">
            <div class="container-fluid">
                <div class="row align-items-center">
                    <!-- 歌曲信息 -->
                    <div class="col-md-3">
                        <div class="d-flex align-items-center">
                            <img 
                                :src="playerStore.coverUrl" 
                                class="me-2"
                                style="width: 50px; height: 50px; object-fit: cover;"
                            >
                            <div>
                                <div class="fw-bold">{{ playerStore.currentTrack?.title }}</div>
                                <div class="small text-muted">{{ playerStore.currentTrack?.artist }}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 播放控制 -->
                    <div class="col-md-6">
                        <div class="d-flex flex-column align-items-center">
                            <div class="btn-group mb-2">
                                <button class="btn btn-outline-light btn-sm" @click="playerStore.previous">
                                    <i class="bi bi-skip-start-fill"></i>
                                </button>
                                <button class="btn btn-outline-light btn-sm" @click="playerStore.togglePlay">
                                    <i :class="playerStore.isPlaying ? 'bi-pause-fill' : 'bi-play-fill'"></i>
                                </button>
                                <button class="btn btn-outline-light btn-sm" @click="playerStore.stop">
                                    <i class="bi bi-stop-fill"></i>
                                </button>
                                <button class="btn btn-outline-light btn-sm" @click="playerStore.next">
                                    <i class="bi bi-skip-end-fill"></i>
                                </button>
                            </div>
                            
                            <!-- 进度条 -->
                            <div class="d-flex align-items-center w-100">
                                <span class="small me-2">{{ formatTime(playerStore.currentTime) }}</span>
                                <input 
                                    type="range" 
                                    class="form-range" 
                                    :value="playerStore.progress"
                                    @input="playerStore.seek($event.target.value)"
                                    style="flex: 1;"
                                >
                                <span class="small ms-2">{{ formatTime(playerStore.duration) }}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 音量控制 -->
                    <div class="col-md-3">
                        <div class="d-flex align-items-center justify-content-end">
                            <i class="bi bi-volume-down me-2"></i>
                            <input 
                                type="range" 
                                class="form-range" 
                                :value="playerStore.volume * 100"
                                @input="playerStore.setVolume($event.target.value / 100)"
                                style="width: 100px;"
                            >
                            <i class="bi bi-volume-up ms-2"></i>
                            
                            <!-- 播放模式 -->
                            <div class="btn-group ms-3">
                                <button 
                                    class="btn btn-sm" 
                                    :class="playerStore.playMode === 'sequential' ? 'btn-primary' : 'btn-outline-light'"
                                    @click="playerStore.setPlayMode('sequential')"
                                >
                                    <i class="bi bi-arrow-repeat"></i>
                                </button>
                                <button 
                                    class="btn btn-sm"
                                    :class="playerStore.playMode === 'random' ? 'btn-primary' : 'btn-outline-light'"
                                    @click="playerStore.setPlayMode('random')"
                                >
                                    <i class="bi bi-shuffle"></i>
                                </button>
                                <button 
                                    class="btn btn-sm"
                                    :class="playerStore.playMode === 'single' ? 'btn-primary' : 'btn-outline-light'"
                                    @click="playerStore.setPlayMode('single')"
                                >
                                    <i class="bi bi-arrow-repeat-1"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    setup() {
        const playerStore = usePlayerStore()
        return { playerStore }
    },

    methods: {
        formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '0:00'
            const mins = Math.floor(seconds / 60)
            const secs = Math.floor(seconds % 60)
            return `${mins}:${secs.toString().padStart(2, '0')}`
        }
    }
}