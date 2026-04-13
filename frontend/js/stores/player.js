import { defineStore } from 'https://unpkg.com/pinia@2.1.7/dist/pinia.esm-browser.js'
import { useAuthStore } from './auth.js'

const API_BASE = 'http://localhost:8000/api/v1'

export const usePlayerStore = defineStore('player', {
    state: () => ({
        audio: null,
        currentTrack: null,
        isPlaying: false,
        currentTime: 0,
        duration: 0,
        volume: 0.8,
        playMode: 'sequential', // sequential, random, single
        queue: [],
        queueIndex: -1,
        lyrics: null,
        sessionId: this.generateSessionId()
    }),

    getters: {
        coverUrl: (state) => {
            if (!state.currentTrack) return null
            return `${API_BASE}/media/cover/${state.currentTrack.id}?size=lg`
        },

        streamUrl: (state) => {
            if (!state.currentTrack) return null
            return `${API_BASE}/media/stream/${state.currentTrack.id}`
        },

        progress: (state) => {
            if (!state.duration) return 0
            return (state.currentTime / state.duration) * 100
        }
    },

    actions: {
        generateSessionId() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
        },

        initAudio() {
            if (this.audio) return

            this.audio = new Audio()
            this.audio.volume = this.volume

            this.audio.addEventListener('timeupdate', () => {
                this.currentTime = this.audio.currentTime
            })

            this.audio.addEventListener('loadedmetadata', () => {
                this.duration = this.audio.duration
            })

            this.audio.addEventListener('play', () => {
                this.isPlaying = true
                this.trackEvent('play_start')
            })

            this.audio.addEventListener('pause', () => {
                this.isPlaying = false
                this.trackEvent('pause')
            })

            this.audio.addEventListener('ended', () => {
                this.isPlaying = false
                this.trackEvent('play_end')
                this.next()
            })

            // Heartbeat every 10 seconds
            setInterval(() => {
                if (this.isPlaying) {
                    this.trackEvent('heartbeat')
                }
            }, 10000)
        },

        async playTrack(track) {
            this.initAudio()

            if (this.currentTrack?.id !== track.id) {
                this.currentTrack = track
                this.audio.src = this.streamUrl

                // Load lyrics
                await this.loadLyrics()
            }

            await this.audio.play()

            // Update Media Session API
            if ('mediaSession' in navigator) {
                navigator.mediaSession.metadata = new MediaMetadata({
                    title: track.title,
                    artist: track.artist || 'Unknown Artist',
                    album: track.album || '',
                    artwork: [
                        { src: this.coverUrl, sizes: '512x512', type: 'image/jpeg' }
                    ]
                })

                navigator.mediaSession.setActionHandler('play', () => this.play())
                navigator.mediaSession.setActionHandler('pause', () => this.pause())
                navigator.mediaSession.setActionHandler('previoustrack', () => this.previous())
                navigator.mediaSession.setActionHandler('nexttrack', () => this.next())
            }
        },

        async loadLyrics() {
            if (!this.currentTrack) return

            try {
                const authStore = useAuthStore()
                const response = await fetch(`${API_BASE}/lyrics/${this.currentTrack.id}`, {
                    headers: {
                        'Authorization': `Bearer ${authStore.accessToken}`
                    }
                })

                if (response.ok) {
                    this.lyrics = await response.json()
                } else {
                    this.lyrics = null
                }
            } catch (error) {
                console.error('Load lyrics error:', error)
                this.lyrics = null
            }
        },

        play() {
            if (this.audio) {
                this.audio.play()
            }
        },

        pause() {
            if (this.audio) {
                this.audio.pause()
            }
        },

        stop() {
            if (this.audio) {
                this.audio.pause()
                this.audio.currentTime = 0
            }
        },

        togglePlay() {
            if (this.isPlaying) {
                this.pause()
            } else {
                this.play()
            }
        },

        seek(percent) {
            if (this.audio && this.duration) {
                this.audio.currentTime = (percent / 100) * this.duration
                this.trackEvent('seek')
            }
        },

        setVolume(value) {
            this.volume = value
            if (this.audio) {
                this.audio.volume = value
            }
        },

        setQueue(tracks, startIndex = 0) {
            this.queue = tracks
            this.queueIndex = startIndex
            if (tracks.length > startIndex) {
                this.playTrack(tracks[startIndex])
            }
        },

        next() {
            if (this.queue.length === 0) return

            let nextIndex = this.queueIndex

            switch (this.playMode) {
                case 'sequential':
                    nextIndex = (this.queueIndex + 1) % this.queue.length
                    break
                case 'random':
                    nextIndex = Math.floor(Math.random() * this.queue.length)
                    break
                case 'single':
                    // Repeat current track
                    this.playTrack(this.queue[this.queueIndex])
                    return
            }

            if (nextIndex !== this.queueIndex || this.playMode !== 'single') {
                this.queueIndex = nextIndex
                this.playTrack(this.queue[nextIndex])
            }
        },

        previous() {
            if (this.queue.length === 0) return

            let prevIndex = this.queueIndex

            switch (this.playMode) {
                case 'sequential':
                    prevIndex = this.queueIndex > 0 ? this.queueIndex - 1 : this.queue.length - 1
                    break
                case 'random':
                    prevIndex = Math.floor(Math.random() * this.queue.length)
                    break
                case 'single':
                    this.playTrack(this.queue[this.queueIndex])
                    return
            }

            this.queueIndex = prevIndex
            this.playTrack(this.queue[prevIndex])
        },

        setPlayMode(mode) {
            this.playMode = mode
        },

        async trackEvent(type) {
            if (!this.currentTrack) return

            const authStore = useAuthStore()
            if (!authStore.accessToken) return

            try {
                await fetch(`${API_BASE}/analytics/events`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authStore.accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        type,
                        track_id: this.currentTrack.id,
                        pos_ms: Math.floor(this.currentTime * 1000),
                        session_id: this.sessionId
                    })
                })
            } catch (error) {
                console.error('Track event error:', error)
            }
        }
    }
})