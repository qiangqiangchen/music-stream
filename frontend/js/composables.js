/* 所有 composable 函数，依赖全局 Vue、API_BASE、createApiFetch、Utils */

/* ──────────────────────────────────────────────
   useAuth
─────────────────────────────────────────────── */
function useAuth() {
    var _Vue = Vue;
    var ref = _Vue.ref;

    var isAuthenticated = ref(false);
    var user = ref(null);
    var loading = ref(false);
    var error = ref(null);
    var success = ref(null);
    var showRegister = ref(false);
    var accessToken = ref(localStorage.getItem('accessToken') || '');
    var refreshToken = ref(localStorage.getItem('refreshToken') || '');

    var apiFetch = createApiFetch({
        getToken: function () {
            return accessToken.value;
        },
        getRefreshToken: function () {
            return refreshToken.value;
        },
        onLogout: function () {
            logout();
        },
        onTokenRefreshed: function (at, rt) {
            accessToken.value = at;
            refreshToken.value = rt;
            localStorage.setItem('accessToken', at);
            localStorage.setItem('refreshToken', rt);
        }
    });

    function logout() {
        isAuthenticated.value = false;
        user.value = null;
        accessToken.value = '';
        refreshToken.value = '';
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        showRegister.value = false;
    }

    async function fetchUser() {
        try {
            var r = await apiFetch('/auth/me');
            if (r.ok) {
                user.value = await r.json();
                isAuthenticated.value = true;
                return true;
            }
            logout();
            return false;
        } catch (_) {
            logout();
            return false;
        }
    }

    async function handleLogin(form) {
        loading.value = true;
        error.value = null;
        try {
            var r = await fetch(API_BASE + '/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(form)
            });
            if (r.ok) {
                var d = await r.json();
                accessToken.value = d.access_token;
                refreshToken.value = d.refresh_token;
                localStorage.setItem('accessToken', d.access_token);
                localStorage.setItem('refreshToken', d.refresh_token);
                return await fetchUser();
            }
            var e = await r.json();
            error.value = e.detail || '登录失败';
            return false;
        } catch (_) {
            error.value = '网络错误';
            return false;
        } finally {
            loading.value = false;
        }
    }

    async function handleRegister(form) {
        error.value = null;
        success.value = null;
        if (form.password !== form.confirm_password) {
            error.value = '两次密码不一致';
            return false;
        }
        loading.value = true;
        try {
            var r = await fetch(API_BASE + '/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(form)
            });
            if (r.ok) {
                success.value = '注册成功！';
                return true;
            }
            var e = await r.json();
            error.value = e.detail || '注册失败';
            return false;
        } catch (_) {
            error.value = '网络错误';
            return false;
        } finally {
            loading.value = false;
        }
    }

    async function init() {
        if (accessToken.value) await fetchUser();
    }

    return {
        isAuthenticated, user, loading, error, success,
        showRegister, apiFetch,
        init, logout, handleLogin, handleRegister
    };
}

/* ──────────────────────────────────────────────
   usePlayer
─────────────────────────────────────────────── */
function usePlayer(apiFetch) {
    var ref = Vue.ref, computed = Vue.computed;

    var audio = ref(null);
    var currentTrack = ref(null);
    var isPlaying = ref(false);
    var currentTime = ref(0);
    var duration = ref(0);
    var volume = ref(parseFloat(localStorage.getItem('music_volume') || '0.8'));
    var _prevVol = ref(0.8);
    var queue = ref([]);
    var queueIndex = ref(-1);
    var currentBlobUrl = ref(null);
    var isTranscoding = ref(false);
    var playMode = ref('sequential');
    var onTrackReady = ref(null);
    var onTrackEnded = ref(null);

    var sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8);
    var playLock = false;
    var saveTimer = null;

    var progress = computed({
        get: function () {
            return duration.value ? (currentTime.value / duration.value) * 100 : 0;
        },
        set: function (v) {
            if (audio.value) audio.value.currentTime = (v / 100) * duration.value;
        }
    });

    var playModeIcon = computed(function () {
        return {sequential: 'bi-repeat', random: 'bi-shuffle', single: 'bi-repeat-1'}[playMode.value] || 'bi-repeat';
    });

    var playModeText = computed(function () {
        return {sequential: '顺序播放', random: '随机播放', single: '单曲循环'}[playMode.value] || '顺序播放';
    });

    async function saveProgress() {
        if (!currentTrack.value || !audio.value) return;
        var pos = Math.floor(audio.value.currentTime * 1000);
        if (pos < 5000) return;
        try {
            await apiFetch('/progress/' + currentTrack.value.id, {method: 'POST', body: {position_ms: pos}});
        } catch (_) {
        }
    }

    function stopSaving() {
        if (saveTimer) {
            clearInterval(saveTimer);
            saveTimer = null;
        }
    }

    function startSaving() {
        stopSaving();
        saveTimer = setInterval(function () {
            if (isPlaying.value) saveProgress();
        }, 10000);
    }

    async function sendEvent(type, trackId, posMs) {
        var tid = trackId || (currentTrack.value && currentTrack.value.id);
        if (!tid) return;
        var pos = (posMs != null) ? posMs : (audio.value ? Math.floor(audio.value.currentTime * 1000) : 0);
        try {
            await apiFetch('/analytics/events', {
                method: 'POST',
                body: {type: type, track_id: tid, pos_ms: pos, session_id: sessionId}
            });
        } catch (_) {
        }
    }

    async function playTrack(track) {
        if (playLock) return;
        playLock = true;
        currentTrack.value = track;
        isTranscoding.value = (track.format === 'flac');
        stopSaving();

        try {
            var oldAudio = audio.value;
            var oldBlobUrl = currentBlobUrl.value;

            var suffix = (track.format === 'flac') ? '?transcode=true' : '';
            var r = await apiFetch('/media/stream/' + track.id + suffix);
            if (!r.ok) throw new Error('Stream failed: ' + r.status);

            var blob = await r.blob();
            var newBlobUrl = URL.createObjectURL(blob);
            var newAudio = new Audio();
            newAudio.volume = volume.value;

            newAudio.addEventListener('loadedmetadata', function () {
                duration.value = newAudio.duration;
            });
            newAudio.addEventListener('timeupdate', function () {
                currentTime.value = newAudio.currentTime;
            });
            newAudio.addEventListener('play', function () {
                isPlaying.value = true;
                isTranscoding.value = false;
                sendEvent('play_start', track.id);
                startSaving();
                if (typeof onTrackReady.value === 'function') onTrackReady.value();
            });
            newAudio.addEventListener('pause', function () {
                sendEvent('pause');
                saveProgress();
            });
            newAudio.addEventListener('ended', function () {
                isPlaying.value = false;
                stopSaving();
                sendEvent('play_end');
                if (typeof onTrackEnded.value === 'function') onTrackEnded.value();
            });
            newAudio.addEventListener('error', function () {
                isTranscoding.value = false;
                stopSaving();
            });

            newAudio.src = newBlobUrl;

            await new Promise(function (resolve, reject) {
                function onOk() {
                    newAudio.removeEventListener('canplay', onOk);
                    newAudio.removeEventListener('error', onErr);
                    resolve();
                }

                function onErr() {
                    newAudio.removeEventListener('canplay', onOk);
                    newAudio.removeEventListener('error', onErr);
                    reject(new Error('Audio load failed'));
                }

                newAudio.addEventListener('canplay', onOk);
                newAudio.addEventListener('error', onErr);
                setTimeout(function () {
                    newAudio.removeEventListener('canplay', onOk);
                    newAudio.removeEventListener('error', onErr);
                    reject(new Error('Timeout waiting for audio'));
                }, 15000);
            });

            audio.value = newAudio;
            window.currentAudio = newAudio;
            currentBlobUrl.value = newBlobUrl;

            await newAudio.play();
            isPlaying.value = true;

            setTimeout(function () {
                try {
                    if (oldAudio) oldAudio.pause();
                } catch (_) {
                }
            }, 100);
            setTimeout(function () {
                if (oldBlobUrl) URL.revokeObjectURL(oldBlobUrl);
            }, 300);

        } catch (e) {
            isTranscoding.value = false;
            stopSaving();
            console.error('playTrack error:', e);
        } finally {
            playLock = false;
        }
    }

    function playTrackFromList(track, list) {
        if (list && list.length) {
            queue.value = list.slice();
            queueIndex.value = list.findIndex(function (t) {
                return t.id === track.id;
            });
        } else {
            queue.value = [track];
            queueIndex.value = 0;
        }
        return playTrack(track);
    }

    function togglePlay() {
        var a = audio.value;
        if (!a) return;
        if (a.paused) {
            a.play().then(function () {
                isPlaying.value = true;
            }).catch(console.error);
        } else {
            a.pause();
            isPlaying.value = false;
        }
    }

    function nextTrack() {
        if (!queue.value.length) return;
        if (playMode.value === 'single') {
            playTrack(currentTrack.value);
            return;
        }
        var idx = playMode.value === 'random'
            ? Math.floor(Math.random() * queue.value.length)
            : (queueIndex.value + 1) % queue.value.length;
        queueIndex.value = idx;
        setTimeout(function () {
            playTrack(queue.value[idx]);
        }, 10);
    }

    function previousTrack() {
        if (!queue.value.length) return;
        var idx = playMode.value === 'random'
            ? Math.floor(Math.random() * queue.value.length)
            : (queueIndex.value > 0 ? queueIndex.value - 1 : queue.value.length - 1);
        queueIndex.value = idx;
        setTimeout(function () {
            playTrack(queue.value[idx]);
        }, 10);
    }

    function seek(v) {
        if (!audio.value || !duration.value) return;
        audio.value.currentTime = (parseFloat(v) / 100) * duration.value;
        sendEvent('seek');
    }

    function setVolume(v) {
        if (v !== undefined) volume.value = v;
        if (audio.value) audio.value.volume = volume.value;
        localStorage.setItem('music_volume', String(volume.value));
    }

    function toggleMute() {
        if (volume.value > 0) {
            _prevVol.value = volume.value;
            setVolume(0);
        } else setVolume(_prevVol.value || 0.8);
    }

    function togglePlayMode() {
        var modes = ['sequential', 'random', 'single'];
        playMode.value = modes[(modes.indexOf(playMode.value) + 1) % modes.length];
    }

    async function downloadTrack(track) {
        try {
            var r = await apiFetch('/media/download/' + track.id);
            if (!r.ok) throw new Error('fail');
            var blob = await r.blob();
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = (track.artist || 'Unknown') + ' - ' + track.title + '.' + (track.format || 'mp3');
            a.click();
            URL.revokeObjectURL(url);
            sendEvent('download', track.id);
        } catch (_) {
            alert('下载失败');
        }
    }

    function destroy() {
        if (audio.value) {
            saveProgress();
            audio.value.pause();
            audio.value.src = '';
        }
        if (currentBlobUrl.value) URL.revokeObjectURL(currentBlobUrl.value);
        stopSaving();
    }

    return {
        audio, currentTrack, isPlaying, currentTime, duration,
        volume, progress, queue, queueIndex,
        isTranscoding, playMode, playModeIcon, playModeText,
        onTrackReady, onTrackEnded,
        playTrack, playTrackFromList, togglePlay,
        nextTrack, previousTrack, seek,
        setVolume, toggleMute, togglePlayMode,
        downloadTrack, sendEvent, destroy
    };
}

/* ──────────────────────────────────────────────
   useLyrics
─────────────────────────────────────────────── */
function useLyrics(apiFetch, currentTrack, currentTime) {
    var ref = Vue.ref, watch = Vue.watch;

    var LYRIC_LINE_HEIGHT = 40; // px，与 CSS --lyric-line-height 保持一致
    var ACTIVE_ROW = 2;  // 第三行（0-indexed = 2）作为激活行

    var showLyrics = ref(false);
    var lyrics = ref(null);
    var lyricOffset = ref(0);
    // trackOffset：歌词轨道的 Y 偏移（负值向上）
    var trackOffset = ref(0);
    // 用户手动滚动产生的额外偏移（相对于自动位置的增量）
    var userDelta = ref(0);

    var userScrolling = false;
    var resumeTimer = null;

    // ── 计算当前激活行索引 ──────────────────────────────
    function getCurrentIdx() {
        if (!lyrics.value || !lyrics.value.lines) return -1;
        var ct = currentTime.value * 1000;
        var lines = lyrics.value.lines;
        var result = -1;
        for (var i = 0; i < lines.length; i++) {
            if (lines[i].time_ms == null) continue;
            if (ct >= lines[i].time_ms) result = i;
            else break;
        }
        return result;
    }

    // ── 计算自动跟随时的轨道偏移 ──────────────────────
    function calcAutoOffset(idx) {
        // idx < ACTIVE_ROW：从第0行开始，轨道不动
        // idx >= ACTIVE_ROW：把第 idx 行滚到第 ACTIVE_ROW 行位置
        var scrollRows = Math.max(0, idx - ACTIVE_ROW);
        return -scrollRows * LYRIC_LINE_HEIGHT;
    }

    // ── 应用自动偏移（不含用户增量）─────────────────────
    function applyAutoOffset(smooth) {
        var idx = getCurrentIdx();
        var auto = calcAutoOffset(idx);
        trackOffset.value = auto + (userScrolling ? userDelta.value : 0);
    }

    // ── 获取某行的 class ──────────────────────────────
    function getLineClass(lineIdx) {
        var cur = getCurrentIdx();
        var diff = lineIdx - cur;
        if (diff === 0) return 'lyrics-line active';
        if (diff === -1) return 'lyrics-line prev-1';
        if (diff === -2) return 'lyrics-line prev-2';
        if (diff === 1) return 'lyrics-line next-1';
        if (diff === 2) return 'lyrics-line next-2';
        return 'lyrics-line';
    }

    // ── 用户滚动（鼠标滚轮 / 触摸）─────────────────────
    function onWheel(e) {
        e.preventDefault();
        _startUserScroll();
        userDelta.value -= e.deltaY * 0.8;
        _clampUserDelta();
        trackOffset.value = calcAutoOffset(getCurrentIdx()) + userDelta.value;
    }

    // 触摸支持
    var touchStartY = 0;

    function onTouchStart(e) {
        touchStartY = e.touches[0].clientY;
    }

    function onTouchMove(e) {
        e.preventDefault();
        _startUserScroll();
        var dy = e.touches[0].clientY - touchStartY;
        touchStartY = e.touches[0].clientY;
        userDelta.value += dy;
        _clampUserDelta();
        trackOffset.value = calcAutoOffset(getCurrentIdx()) + userDelta.value;
    }

    function _startUserScroll() {
        userScrolling = true;
        clearTimeout(resumeTimer);
        resumeTimer = setTimeout(function () {
            userScrolling = false;
            userDelta.value = 0;
            // 平滑回到当前位置
            trackOffset.value = calcAutoOffset(getCurrentIdx());
        }, 3000);
    }


    // 限制用户可以滚动的范围：不能超出歌词头尾
    function _clampUserDelta() {
        if (!lyrics.value || !lyrics.value.lines) return;
        var total = lyrics.value.lines.length;
        var autoOff = calcAutoOffset(getCurrentIdx());
        // 向上最多滚到末尾（让最后一行在第ACTIVE_ROW行）
        var minDelta = -(total - 1 - ACTIVE_ROW) * LYRIC_LINE_HEIGHT - autoOff;
        // 向下最多滚回第0行
        var maxDelta = -autoOff; // 让第0行回到第0行位置
        userDelta.value = Math.max(minDelta, Math.min(maxDelta, userDelta.value));
    }

    // ── 对外接口 ──────────────────────────────────────

    async function loadLyrics() {
        if (!currentTrack.value) return;
        try {
            var url = '/lyrics/' + currentTrack.value.id;
            if (lyricOffset.value) url += '?offset=' + lyricOffset.value;
            var r = await apiFetch(url);
            lyrics.value = r.ok ? await r.json() : null;
        } catch (_) {
            lyrics.value = null;
        }
        // 重置偏移
        userScrolling = false;
        userDelta.value = 0;
        trackOffset.value = calcAutoOffset(getCurrentIdx());
    }

    function toggleLyrics() {
        showLyrics.value = !showLyrics.value;
        if (showLyrics.value && currentTrack.value) loadLyrics();
    }

    function adjustOffset(delta) {
        lyricOffset.value += delta;
        loadLyrics();
    }

    function isCurrentLine(line) {
        if (line.time_ms == null) return false;
        var ct = currentTime.value * 1000;
        var lines = (lyrics.value && lyrics.value.lines) ? lyrics.value.lines : [];
        var idx = lines.indexOf(line);
        if (idx === -1) return false;
        var next = lines[idx + 1];
        if (next && next.time_ms != null) return ct >= line.time_ms && ct < next.time_ms;
        return ct >= line.time_ms;
    }

    function reset() {
        userScrolling = false;
        userDelta.value = 0;
        clearTimeout(resumeTimer);
    }
    function resetScroll() {
        userScrolling = false;
        userDelta.value = 0;
        clearTimeout(resumeTimer);
        trackOffset.value = calcAutoOffset(getCurrentIdx());
    }

    // 监听时间变化 → 更新自动偏移
    var lastAutoIdx = -1;
    watch(currentTime, function () {
        if (!showLyrics.value || userScrolling) return;
        var idx = getCurrentIdx();
        if (idx !== lastAutoIdx) {
            lastAutoIdx = idx;
            trackOffset.value = calcAutoOffset(idx);
        }
    });

    // 歌曲切换时重置
    watch(currentTrack, function () {
        userScrolling = false;
        userDelta.value = 0;
        lastAutoIdx = -1;
        trackOffset.value = 0;
    });

    return {
        showLyrics, lyrics, lyricOffset,
        trackOffset,
        loadLyrics, toggleLyrics, adjustOffset,
        isCurrentLine, getLineClass,
        onWheel, onTouchStart, onTouchMove,
        reset,
        resetScroll,
        LYRIC_LINE_HEIGHT
    };
}

/* ──────────────────────────────────────────────
   useSpectrum
─────────────────────────────────────────────── */
function useSpectrum(isPlaying) {
    var ref = Vue.ref;
    var spectrumCanvas = ref(null);

    var audioCtx = null;
    var analyser = null;
    var srcNode = null;
    var animId = null;
    var initialized = false;

    function clearCanvas() {
        var c = spectrumCanvas.value;
        if (!c) return;
        c.getContext('2d').clearRect(0, 0, c.width, c.height);
    }

    function draw() {
        var c = spectrumCanvas.value;
        if (!c || !analyser) return;
        var ctx = c.getContext('2d');
        var W = c.width = window.innerWidth, H = 90;
        c.height = H;

        var len = analyser.frequencyBinCount;
        var data = new Uint8Array(len);
        analyser.getByteFrequencyData(data);

        ctx.clearRect(0, 0, W, H);
        var bw = (W / len) * 2.5, x = 0;
        for (var i = 0; i < len; i++) {
            var bh = Math.min((data[i] / 255) * (H - 8), H - 8);
            var hue = 120 + (i / len) * 40;
            var op = 0.25 + (bh / (H - 8)) * 0.55;
            ctx.fillStyle = 'hsla(' + hue + ',80%,55%,' + op + ')';
            ctx.fillRect(x, H - bh, bw, bh);
            x += bw + 1;
        }
        animId = requestAnimationFrame(draw);
    }

    function init(audioElement) {
        if (initialized) {
            if (!animId) draw();
            return;
        }
        if (!audioElement || !audioElement.src || audioElement.src === window.location.href) return;
        try {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            srcNode = audioCtx.createMediaElementSource(audioElement);
            srcNode.connect(analyser);
            analyser.connect(audioCtx.destination);
            initialized = true;
            draw();
        } catch (e) {
            console.warn('Spectrum init failed:', e.message);
            initialized = true;
        }
    }

    function stop() {
        if (animId) {
            cancelAnimationFrame(animId);
            animId = null;
        }
        if (srcNode) {
            try {
                srcNode.disconnect();
            } catch (_) {
            }
            srcNode = null;
        }
        analyser = null;
        clearCanvas();
    }

    function reset() {
        stop();
        if (audioCtx) {
            try {
                audioCtx.close();
            } catch (_) {
            }
            audioCtx = null;
        }
        initialized = false;
    }

    function destroy() {
        reset();
    }

    function handleResize() {
        var c = spectrumCanvas.value;
        if (c) c.width = window.innerWidth;
    }

    return {spectrumCanvas, init, stop, reset, destroy, handleResize};
}

/* ──────────────────────────────────────────────
   useFavorites
─────────────────────────────────────────────── */
function useFavorites(apiFetch) {
    var ref = Vue.ref;
    var favorites = ref([]);
    var favoritedIds = ref(new Set());

    async function loadFavorites() {
        try {
            var r = await apiFetch('/favorites');
            if (r.ok) {
                favorites.value = await r.json();
                favoritedIds.value = new Set(favorites.value.map(function (t) {
                    return t.id;
                }));
            }
        } catch (_) {
        }
    }

    function isFavorited(id) {
        return favoritedIds.value.has(id);
    }

    async function toggleFavorite(track) {
        var fav = isFavorited(track.id);
        try {
            var r = await apiFetch('/favorites/' + track.id, {method: fav ? 'DELETE' : 'POST'});
            if (r.ok) {
                if (fav) {
                    favoritedIds.value.delete(track.id);
                    favorites.value = favorites.value.filter(function (t) {
                        return t.id !== track.id;
                    });
                } else {
                    favoritedIds.value.add(track.id);
                    favorites.value.unshift(Object.assign({}, track, {favorited_at: new Date().toISOString()}));
                }
                favoritedIds.value = new Set(favoritedIds.value); // 触发响应
            }
        } catch (_) {
        }
    }

    return {favorites, favoritedIds, loadFavorites, isFavorited, toggleFavorite};
}

/* ──────────────────────────────────────────────
   usePlaylists
─────────────────────────────────────────────── */
function usePlaylists(apiFetch) {
    var ref = Vue.ref, reactive = Vue.reactive;

    var playlists = ref([]);
    var currentPlaylist = ref(null);
    var playlistTracks = ref([]);
    var showCreatePlaylist = ref(false);
    var pendingTrack = ref(null);
    var newPlaylist = reactive({name: '', description: ''});

    async function loadPlaylists() {
        try {
            var r = await apiFetch('/playlists');
            if (r.ok) playlists.value = await r.json();
        } catch (_) {
        }
    }

    async function createPlaylist() {
        if (!newPlaylist.name.trim()) {
            alert('请输入名称');
            return;
        }
        try {
            var r = await apiFetch('/playlists', {
                method: 'POST',
                body: {name: newPlaylist.name.trim(), description: newPlaylist.description}
            });
            if (r.ok) {
                showCreatePlaylist.value = false;
                newPlaylist.name = newPlaylist.description = '';
                await loadPlaylists();
            }
        } catch (_) {
        }
    }

    async function viewPlaylist(pl) {
        try {
            var r = await apiFetch('/playlists/' + pl.id);
            if (r.ok) {
                currentPlaylist.value = await r.json();
                playlistTracks.value = currentPlaylist.value.tracks || [];
            }
        } catch (_) {
        }
    }

    async function deletePlaylist(pl) {
        if (!confirm('确定删除 "' + pl.name + '"？')) return;
        try {
            var r = await apiFetch('/playlists/' + pl.id, {method: 'DELETE'});
            if (r.ok) {
                if (currentPlaylist.value && currentPlaylist.value.id === pl.id) currentPlaylist.value = null;
                await loadPlaylists();
            }
        } catch (_) {
        }
    }

    async function addToPlaylist(playlistId) {
        if (!pendingTrack.value) return;
        try {
            var r = await apiFetch('/playlists/' + playlistId + '/tracks', {
                method: 'POST',
                body: {track_id: pendingTrack.value.id}
            });
            if (r.ok) {
                var pl = playlists.value.find(function (p) {
                    return p.id === playlistId;
                });
                alert('已添加到 "' + (pl ? pl.name : '') + '"');
                pendingTrack.value = null;
                await loadPlaylists();
            }
        } catch (_) {
            alert('添加失败');
        }
    }

    async function quickCreatePlaylist() {
        var name = prompt('请输入新播放列表名称：');
        if (!name || !name.trim()) return;
        try {
            var r = await apiFetch('/playlists', {method: 'POST', body: {name: name.trim()}});
            if (r.ok) {
                await loadPlaylists();
                alert('"' + name + '" 已创建');
            }
        } catch (_) {
            alert('创建失败');
        }
    }

    async function removeFromPlaylist(track) {
        if (!currentPlaylist.value) return;
        try {
            var r = await apiFetch('/playlists/' + currentPlaylist.value.id + '/tracks/' + track.id, {method: 'DELETE'});
            if (r.ok) {
                playlistTracks.value = playlistTracks.value.filter(function (t) {
                    return t.id !== track.id;
                });
                if (currentPlaylist.value) currentPlaylist.value.track_count = playlistTracks.value.length;
                await loadPlaylists();
            }
        } catch (_) {
        }
    }

    return {
        playlists, currentPlaylist, playlistTracks,
        showCreatePlaylist, pendingTrack, newPlaylist,
        loadPlaylists, createPlaylist, viewPlaylist,
        deletePlaylist, addToPlaylist, quickCreatePlaylist, removeFromPlaylist
    };
}

/* ──────────────────────────────────────────────
   useRecentPlays
─────────────────────────────────────────────── */
function useRecentPlays(apiFetch) {
    var ref = Vue.ref;
    var recentPlays = ref([]);

    async function loadRecentPlays() {
        try {
            var r = await apiFetch('/recent?limit=50');
            if (r.ok) recentPlays.value = await r.json();
        } catch (_) {
        }
    }

    async function clearRecentPlays() {
        if (!confirm('确定清空所有记录？')) return;
        try {
            var r = await apiFetch('/recent/clear', {method: 'DELETE'});
            if (r.ok) {
                recentPlays.value = [];
                alert('已清空');
            }
        } catch (_) {
        }
    }

    async function removeFromRecent(track) {
        try {
            var r = await apiFetch('/recent/' + track.id, {method: 'DELETE'});
            if (r.ok) recentPlays.value = recentPlays.value.filter(function (t) {
                return t.id !== track.id;
            });
        } catch (_) {
        }
    }

    return {recentPlays, loadRecentPlays, clearRecentPlays, removeFromRecent};
}