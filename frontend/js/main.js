(function () {
    'use strict';

    var createApp = Vue.createApp;
    var ref = Vue.ref;
    var reactive = Vue.reactive;
    var watch = Vue.watch;
    var onMounted = Vue.onMounted;
    var onUnmounted = Vue.onUnmounted;

    var App = {
        components: {
            NavBar: NavBar,
            LoginPage: LoginPage,
            RegisterPage: RegisterPage,
            TrackList: TrackList,
            AlbumGrid: AlbumGrid,
            ArtistGrid: ArtistGrid,
            PlaylistView: PlaylistView,
            FavoriteList: FavoriteList,
            RecentPlays: RecentPlays,
            AdminPanel: AdminPanel,
            PlayerBar: PlayerBar,
            CreatePlaylistModal: CreatePlaylistModal,
            ShortcutsModal: ShortcutsModal,
            ChatRoom: ChatRoom,
        },

        setup: function () {

            /* ── 认证 ── */
            var auth = useAuth();
            var player = usePlayer(auth.apiFetch);
            var lyricsM = useLyrics(auth.apiFetch, player.currentTrack, player.currentTime);
            var favM = useFavorites(auth.apiFetch);
            var plM = usePlaylists(auth.apiFetch);
            var recentM = useRecentPlays(auth.apiFetch);


            // 添加聊天模块
            var chat = useChat(auth);
            var showChat = ref(false);

            // 打开聊天室
            function handleOpenChat() {
                showChat.value = true;
                chat.openChatRoom();  // 标记聊天室打开，清空未读
            }

            // 关闭聊天室
            function handleCloseChat() {
                showChat.value = false;
                chat.closeChatRoom();
            }

            /* ══════════════════════════════════════
               频谱：完全在 setup 内管理，不依赖 useSpectrum
               ══════════════════════════════════════ */
            var canvasEl = ref(null);
            var audioCtx = null;
            var analyser = null;
            var srcNode = null;
            var animId = null;
            var specInited = false;
            var currentAudioElement = null;  // 记录当前连接的音频元素

            function specClearCanvas() {
                var c = canvasEl.value;
                if (!c) return;
                c.getContext('2d').clearRect(0, 0, c.width, c.height);
            }

            function specDraw() {
                var c = canvasEl.value;
                if (!c || !analyser) return;
                var ctx = c.getContext('2d');
                var W = window.innerWidth;
                var H = 90;
                if (c.width !== W) c.width = W;
                if (c.height !== H) c.height = H;

                var len = analyser.frequencyBinCount;
                var data = new Uint8Array(len);

                if (player.isPlaying.value) {
                    analyser.getByteFrequencyData(data);
                } else {
                    analyser.getByteFrequencyData(data);
                    for (var i = 0; i < len; i++) {
                        data[i] = data[i] * 0.5;
                    }
                }

                ctx.clearRect(0, 0, W, H);
                var bw = (W / len) * 3.0;
                var x = 0;
                for (var i = 0; i < len; i++) {
                    var bh = Math.min((data[i] / 255) * (H - 8), H - 8);
                    if (bh < 1) {
                        x += bw + 1;
                        continue;
                    }
                    var hue = 120 + (i / len) * 40;
                    var op = 0.7 + (bh / (H - 8)) * 0.3;
                    ctx.fillStyle = 'hsla(' + hue + ',80%,55%,' + op + ')';
                    ctx.fillRect(x, H - bh, bw, bh);
                    x += bw + 1;
                }
                animId = requestAnimationFrame(specDraw);
            }

            function specStop() {
                if (animId) {
                    cancelAnimationFrame(animId);
                    animId = null;
                }
                specClearCanvas();
            }

            function specReset() {
                specStop();
                if (srcNode) {
                    try {
                        srcNode.disconnect();
                    } catch (_) {
                    }
                    srcNode = null;
                }
                if (audioCtx) {
                    try {
                        audioCtx.close();
                    } catch (_) {
                    }
                    audioCtx = null;
                }
                analyser = null;
                specInited = false;
                currentAudioElement = null;
            }

            function specInit(audioElement) {
                if (!audioElement || !audioElement.src || audioElement.src === window.location.href) {
                    return;
                }

                // 如果是同一个音频元素且已初始化，只恢复绘制
                if (specInited && currentAudioElement === audioElement) {
                    if (!animId) specDraw();
                    return;
                }

                // 不同的音频元素，需要完全重置
                if (currentAudioElement !== audioElement) {
                    specReset();
                }

                try {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 256;
                    analyser.smoothingTimeConstant = 0.8;

                    srcNode = audioCtx.createMediaElementSource(audioElement);
                    srcNode.connect(analyser);
                    analyser.connect(audioCtx.destination);

                    specInited = true;
                    currentAudioElement = audioElement;
                    specDraw();
                    console.log('[Spectrum] 初始化成功');
                } catch (e) {
                    console.warn('[Spectrum] 初始化失败:', e.message);
                    // 如果失败，标记为已尝试但不可用
                    specInited = true;
                    currentAudioElement = audioElement;
                }
            }

            function specHandleResize() {
                var c = canvasEl.value;
                if (c) c.width = window.innerWidth;
            }

            function specDestroy() {
                specReset();
            }

            /* ══════════════════════════════════════
               播放器回调
               ══════════════════════════════════════ */
            player.onTrackReady.value = function () {
                var audioEl = player.audio.value;
                if (audioEl) {
                    // 延迟初始化，确保音频元素已准备好
                    setTimeout(function () {
                        specInit(audioEl);
                    }, 150);
                }
                if (lyricsM.showLyrics.value) lyricsM.loadLyrics();
            };

            player.onTrackEnded.value = function () {
                specStop();
                player.nextTrack();
            };

            // 监听播放状态
            watch(player.isPlaying, function (playing) {
                if (playing && specInited && analyser && !animId) {
                    specDraw();
                }
            });

            // 监听 canvasEl 变化
            watch(canvasEl, function (newEl) {
                if (newEl && player.audio.value && !specInited) {
                    setTimeout(function () {
                        specInit(player.audio.value);
                    }, 100);
                }
            });

            /* ══════════════════════════════════════
               页面数据
               ══════════════════════════════════════ */
            var activeTab = ref('tracks');
            var showShortcuts = ref(false);
            var searchQuery = ref('');
            var tracks = ref([]);
            var albums = ref([]);
            var artists = ref([]);
            var stats = reactive({total_tracks: 0, total_users: 0, total_plays: 0, today_plays: 0});
            var topTracks = ref([]);
            var topPeriod = ref('7d');
            var activities = ref([]);
            var searchTimer = null;

            /* ── 数据加载 ── */
            async function loadTracks() {
                auth.loading.value = true;
                try {
                    var p = new URLSearchParams({
                        page: 1, page_size: 100, sort_by: 'title', sort_order: 'asc'
                    });
                    if (searchQuery.value) p.append('search', searchQuery.value);
                    var r = await auth.apiFetch('/tracks?' + p.toString());
                    if (r.ok) tracks.value = (await r.json()).items || [];
                } catch (_) {
                } finally {
                    auth.loading.value = false;
                }
            }

            async function loadAlbums() {
                try {
                    var r = await auth.apiFetch('/albums?page=1&page_size=50');
                    if (r.ok) albums.value = (await r.json()).items || [];
                } catch (_) {
                }
            }

            async function loadArtists() {
                try {
                    var r = await auth.apiFetch('/artists?page=1&page_size=50');
                    if (r.ok) artists.value = (await r.json()).items || [];
                } catch (_) {
                }
            }

            async function loadAdminStats() {
                try {
                    var rs = await Promise.all([
                        auth.apiFetch('/admin/stats/overview'),
                        auth.apiFetch('/admin/stats/top-tracks?period=' + topPeriod.value + '&limit=10'),
                        auth.apiFetch('/admin/stats/recent-activity?limit=20')
                    ]);
                    if (rs[0].ok) Object.assign(stats, await rs[0].json());
                    if (rs[1].ok) topTracks.value = (await rs[1].json()).tracks || [];
                    if (rs[2].ok) activities.value = (await rs[2].json()).activities || [];
                } catch (_) {
                }
            }

            async function loadTopTracks() {
                try {
                    var r = await auth.apiFetch(
                        '/admin/stats/top-tracks?period=' + topPeriod.value + '&limit=10'
                    );
                    if (r.ok) topTracks.value = (await r.json()).tracks || [];
                } catch (_) {
                }
            }

            function handleSearch() {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(function () {
                    if (activeTab.value === 'tracks') loadTracks();
                }, 300);
            }

            async function scanLibrary() {
                try {
                    var r = await auth.apiFetch('/library/scan', {method: 'POST'});
                    if (r.ok) {
                        alert('扫描完成');
                        await loadTracks();
                    }
                } catch (_) {
                    alert('扫描失败');
                }
            }

            async function clearCache() {
                if (!confirm('确定清空转码缓存？')) return;
                try {
                    await auth.apiFetch('/system/cache/clear', {method: 'POST'});
                    alert('已清空');
                } catch (_) {
                }
            }

            function viewAlbum(a) {
                activeTab.value = 'tracks';
                searchQuery.value = a.name;
                loadTracks();
            }

            function viewArtist(a) {
                activeTab.value = 'tracks';
                searchQuery.value = a.name;
                loadTracks();
            }

            function playAll() {
                if (!plM.playlistTracks.value.length) {
                    alert('播放列表为空');
                    return;
                }
                player.queue.value = plM.playlistTracks.value.slice();
                player.queueIndex.value = 0;
                player.playTrack(plM.playlistTracks.value[0]);
            }

            /* ── CSS 变量同步 ── */
            watch([player.progress, player.volume], function () {
                document.documentElement.style.setProperty(
                    '--progress', player.progress.value + '%'
                );
                document.documentElement.style.setProperty(
                    '--volume', (player.volume.value * 100) + '%'
                );
            }, {immediate: true});

            /* ── 键盘快捷键 ── */
            function handleKeydown(e) {
                // 如果焦点在输入框，不处理快捷键
                if (e.target.tagName === 'INPUT' ||
                    e.target.tagName === 'TEXTAREA' ||
                    e.target.isContentEditable) {
                    return;
                }

                // 对于所有快捷键，都阻止默认行为
                var preventDefaultKeys = [
                    'Space', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
                    'KeyN', 'KeyP', 'KeyM', 'KeyL', 'KeyR'
                ];

                if (preventDefaultKeys.indexOf(e.code) !== -1) {
                    e.preventDefault();
                }

                var a = player.audio.value;

                switch (e.code) {
                    case 'Space':
                        if (!player.currentTrack.value) return;
                        player.togglePlay();
                        break;
                    case 'ArrowLeft':
                        if (a) a.currentTime = Math.max(0, a.currentTime - 5);
                        player.sendEvent('seek');
                        break;
                    case 'ArrowRight':
                        if (a) a.currentTime = Math.min(player.duration.value, a.currentTime + 5);
                        player.sendEvent('seek');
                        break;
                    case 'ArrowUp':
                        player.setVolume(Math.min(1, player.volume.value + 0.05));
                        break;
                    case 'ArrowDown':
                        player.setVolume(Math.max(0, player.volume.value - 0.05));
                        break;
                    case 'KeyN':
                        if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                            player.nextTrack();
                        }
                        break;
                    case 'KeyP':
                        if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                            player.previousTrack();
                        }
                        break;
                    case 'KeyM':
                        if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                            player.toggleMute();
                        }
                        break;
                    case 'KeyL':
                        if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                            lyricsM.toggleLyrics();
                        }
                        break;
                    case 'KeyR':
                        if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                            player.togglePlayMode();
                        }
                        break;
                }
            }

            /* ── 登录/注册 ── */
            async function handleLogin(form) {
                var ok = await auth.handleLogin(form);
                if (ok) {
                    await loadTracks();
                    await favM.loadFavorites();
                    await plM.loadPlaylists();
                }
            }

            async function handleRegister(form) {
                var ok = await auth.handleRegister(form);
                if (ok) setTimeout(function () {
                    auth.showRegister.value = false;
                }, 2000);
            }

            // 重写登出函数
            var originalLogout = auth.logout;
            auth.logout = function () {
                chat.disconnect();
                originalLogout.call(auth);
            };

            /* ── 生命周期 ── */
            onMounted(async function () {
                await auth.init();
                if (auth.isAuthenticated.value) {
                    await loadTracks();
                    await favM.loadFavorites();
                    await plM.loadPlaylists();
                    // 延迟一点连接，确保 token 已保存
                    setTimeout(function () {
                        chat.connect();
                    }, 100);
                }
                window.addEventListener('keydown', handleKeydown);
                window.addEventListener('resize', specHandleResize);
            });

            onUnmounted(function () {
                player.destroy();
                specDestroy();
                lyricsM.reset();
                window.removeEventListener('keydown', handleKeydown);
                window.removeEventListener('resize', specHandleResize);
            });


            /* ── 暴露给模板 ── */
            return {
                /* auth */
                isAuthenticated: auth.isAuthenticated,
                user: auth.user,
                loading: auth.loading,
                error: auth.error,
                success: auth.success,
                showRegister: auth.showRegister,
                handleLogin, handleRegister,
                logout: auth.logout,
                /* ui */
                activeTab, showShortcuts, searchQuery,
                /* data */
                tracks, albums, artists, stats, topTracks, topPeriod, activities,
                /* player */
                currentTrack: player.currentTrack,
                isPlaying: player.isPlaying,
                currentTime: player.currentTime,
                duration: player.duration,
                volume: player.volume,
                progress: player.progress,
                playModeIcon: player.playModeIcon,
                playModeText: player.playModeText,
                togglePlay: player.togglePlay,
                nextTrack: player.nextTrack,
                previousTrack: player.previousTrack,
                togglePlayMode: player.togglePlayMode,
                toggleMute: player.toggleMute,
                setVolume: player.setVolume,
                seek: player.seek,
                downloadTrack: player.downloadTrack,
                playTrack: player.playTrack,
                playTrackFromList: player.playTrackFromList,
                /* canvas — 用 ref 对象暴露，模板用函数式写法赋值 */
                canvasEl,
                /* lyrics */
                showLyrics: lyricsM.showLyrics,
                lyrics: lyricsM.lyrics,
                lyricOffset: lyricsM.lyricOffset,
                toggleLyrics: lyricsM.toggleLyrics,
                adjustLyricOffset: lyricsM.adjustOffset,
                isCurrentLyricLine: lyricsM.isCurrentLine,
                onLyricsScroll: lyricsM.onLyricsScroll,
                /* favorites */
                favorites: favM.favorites,
                favoritedIds: favM.favoritedIds,
                loadFavorites: favM.loadFavorites,
                toggleFavorite: favM.toggleFavorite,
                /* playlists */
                playlists: plM.playlists,
                currentPlaylist: plM.currentPlaylist,
                playlistTracks: plM.playlistTracks,
                showCreatePlaylist: plM.showCreatePlaylist,
                pendingTrack: plM.pendingTrack,
                newPlaylist: plM.newPlaylist,
                loadPlaylists: plM.loadPlaylists,
                createPlaylist: plM.createPlaylist,
                viewPlaylist: plM.viewPlaylist,
                deletePlaylist: plM.deletePlaylist,
                addToPlaylist: plM.addToPlaylist,
                quickCreatePlaylist: plM.quickCreatePlaylist,
                removeFromPlaylist: plM.removeFromPlaylist,
                playAll,
                /* recent */
                recentPlays: recentM.recentPlays,
                loadRecentPlays: recentM.loadRecentPlays,
                clearRecentPlays: recentM.clearRecentPlays,
                removeFromRecent: recentM.removeFromRecent,
                /* loaders */
                loadTracks, loadAlbums, loadArtists,
                loadAdminStats, loadTopTracks,
                handleSearch, scanLibrary, clearCache,
                viewAlbum, viewArtist,

                trackOffset: lyricsM.trackOffset,
                getLineClass: lyricsM.getLineClass,
                lyricLineHeight: lyricsM.LYRIC_LINE_HEIGHT,
                onLyricWheel: lyricsM.onWheel,
                onLyricTouchStart: lyricsM.onTouchStart,
                onLyricTouchMove: lyricsM.onTouchMove,

                // 聊天
                showChat,
                chatIsConnected: chat.isConnected,
                chatMessages: chat.messages,
                chatOnlineUsers: chat.onlineUsers,
                chatOnlineCount: chat.onlineCount,
                chatUnreadCount: chat.unreadCount,
                chatInputMessage: chat.inputMessage,
                chatFormatTime: chat.formatChatTime,
                chatGetMessageClass: chat.getMessageClass,
                handleOpenChat,
                handleCloseChat,
                chatSend: chat.sendMessage,
                chatCurrentUserId: function () {
                    return auth.user.value?.id;
                },
            };
        },

        template: [
            '<div>',

            /* 导航栏 */
            '  <NavBar v-if="isAuthenticated" :user="user" @logout="logout" />',

            /* 认证页 */
            '  <LoginPage v-if="!isAuthenticated && !showRegister"',
            '             :loading="loading" :error="error"',
            '             @login="handleLogin" @show-register="showRegister = true" />',
            '  <RegisterPage v-if="!isAuthenticated && showRegister"',
            '                :loading="loading" :error="error" :success="success"',
            '                @register="handleRegister" @back-login="showRegister = false" />',

            /* 主内容 */
            '  <div v-if="isAuthenticated" class="container-fluid mt-3">',

            /* 标签页 */
            '    <ul class="nav nav-tabs mb-3">',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'tracks\'}"',
            '           href="#" @click.prevent="activeTab=\'tracks\'">',
            '          <i class="bi bi-music-note-list"></i> 歌曲',
            '        </a>',
            '      </li>',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'albums\'}"',
            '           href="#" @click.prevent="activeTab=\'albums\';loadAlbums()">',
            '          <i class="bi bi-disc"></i> 专辑',
            '        </a>',
            '      </li>',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'artists\'}"',
            '           href="#" @click.prevent="activeTab=\'artists\';loadArtists()">',
            '          <i class="bi bi-person"></i> 艺术家',
            '        </a>',
            '      </li>',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'playlists\'}"',
            '           href="#" @click.prevent="activeTab=\'playlists\';loadPlaylists()">',
            '          <i class="bi bi-list-ul"></i> 播放列表',
            '        </a>',
            '      </li>',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'favorites\'}"',
            '           href="#" @click.prevent="activeTab=\'favorites\';loadFavorites()">',
            '          <i class="bi bi-heart"></i> 收藏',
            '        </a>',
            '      </li>',
            '      <li class="nav-item">',
            '        <a class="nav-link" :class="{active:activeTab===\'recent\'}"',
            '           href="#" @click.prevent="activeTab=\'recent\';loadRecentPlays()">',
            '          <i class="bi bi-clock-history"></i> 最近播放',
            '        </a>',
            '      </li>',
            '      <li class="nav-item" v-if="user && user.role===\'admin\'">',
            '        <a class="nav-link" :class="{active:activeTab===\'admin\'}"',
            '           href="#" @click.prevent="activeTab=\'admin\';loadAdminStats()">',
            '          <i class="bi bi-bar-chart"></i> 管理',
            '        </a>',
            '      </li>',
            '    </ul>',

            /* 搜索栏 */
            '    <div class="row mb-3">',
            '      <div class="col-md-6">',
            '        <input type="text" class="form-control" placeholder="搜索歌曲、艺术家..."',
            '               v-model="searchQuery" @input="handleSearch">',
            '      </div>',
            '      <div class="col-md-6 text-end mt-2 mt-md-0"',
            '           v-if="user && user.role===\'admin\'">',
            '        <button class="btn btn-success btn-sm" @click="scanLibrary">',
            '          <i class="bi bi-arrow-repeat"></i> 扫描媒体库',
            '        </button>',
            '      </div>',
            '    </div>',

            /* Tab 内容区 */
            '    <TrackList v-if="activeTab===\'tracks\'"',
            '               :tracks="tracks" :playlists="playlists"',
            '               :favoritedIds="favoritedIds" :loading="loading"',
            '               @play="t => playTrackFromList(t, tracks)"',
            '               @download="downloadTrack"',
            '               @toggle-favorite="toggleFavorite"',
            '               @open-playlist-dropdown="t => { pendingTrack = t; if (!playlists.length) loadPlaylists(); }"',
            '               @add-to-playlist="addToPlaylist"',
            '               @create-playlist="quickCreatePlaylist" />',

            '    <AlbumGrid v-if="activeTab===\'albums\'"',
            '               :albums="albums" @view-album="viewAlbum" />',

            '    <ArtistGrid v-if="activeTab===\'artists\'"',
            '                :artists="artists" @view-artist="viewArtist" />',

            '    <PlaylistView v-if="activeTab===\'playlists\'"',
            '                  :playlists="playlists"',
            '                  :currentPlaylist="currentPlaylist"',
            '                  :playlistTracks="playlistTracks"',
            '                  @view-playlist="viewPlaylist"',
            '                  @delete-playlist="deletePlaylist"',
            '                  @create-playlist="showCreatePlaylist = true"',
            '                  @play-track="playTrack"',
            '                  @remove-track="removeFromPlaylist"',
            '                  @play-all="playAll"',
            '                  @back="currentPlaylist = null" />',

            '    <FavoriteList v-if="activeTab===\'favorites\'"',
            '                  :favorites="favorites"',
            '                  @play="playTrack"',
            '                  @toggle-favorite="toggleFavorite" />',

            '    <RecentPlays v-if="activeTab===\'recent\'"',
            '                 :recentPlays="recentPlays"',
            '                 :favoritedIds="favoritedIds"',
            '                 @play="playTrack"',
            '                 @toggle-favorite="toggleFavorite"',
            '                 @remove="removeFromRecent"',
            '                 @clear="clearRecentPlays" />',

            '    <AdminPanel v-if="activeTab===\'admin\' && user && user.role===\'admin\'"',
            '                :stats="stats" :topTracks="topTracks"',
            '                :topPeriod="topPeriod" :activities="activities"',
            '                @scan="scanLibrary"',
            '                @clear-cache="clearCache"',
            '                @load-top-tracks="loadTopTracks"',
            '                @update:topPeriod="v => topPeriod = v" />',
            '  </div>',

            /* ★ 频谱画布
               使用函数式 ref，每次 canvas DOM 挂载/卸载都会触发
               赋值给 canvasEl.value 后，watch(canvasEl) 会检测到并初始化频谱 */
            '  <canvas v-if="currentTrack"',
            '          class="spectrum-canvas"',
            '          :ref="el => { canvasEl = el; }"',
            '  ></canvas>',

            /* 播放器栏 */
            '  <PlayerBar v-if="isAuthenticated && currentTrack"',
            '             :currentTrack="currentTrack"',
            '             :isPlaying="isPlaying"',
            '             :currentTime="currentTime"',
            '             :duration="duration"',
            '             :progress="progress"',
            '             :volume="volume"',
            '             :playModeIcon="playModeIcon"',
            '             :playModeText="playModeText"',
            '             :showLyrics="showLyrics"',
            '             :lyrics="lyrics"',
            '             :lyricOffset="lyricOffset"',
            '             :trackOffset="trackOffset"',
            '             :getLineClass="getLineClass"',
            '             :lyricLineHeight="lyricLineHeight"',
            '             @toggle-play-mode="togglePlayMode"',
            '             @prev="previousTrack"',
            '             @toggle-play="togglePlay"',
            '             @next="nextTrack"',
            '             @toggle-lyrics="toggleLyrics"',
            '             @seek="seek"',
            '             @toggle-mute="toggleMute"',
            '             @set-volume="setVolume"',
            '             @show-shortcuts="showShortcuts = true"',
            '             @adjust-lyric-offset="adjustLyricOffset"',
            '             @lyric-wheel="onLyricWheel"',
            '             @lyric-touch-start="onLyricTouchStart"',
            '             @lyric-touch-move="onLyricTouchMove" />',

            /* 模态框 */
            '  <CreatePlaylistModal v-if="showCreatePlaylist"',
            '                       :name="newPlaylist.name"',
            '                       :description="newPlaylist.description"',
            '                       @update:name="v => newPlaylist.name = v"',
            '                       @update:description="v => newPlaylist.description = v"',
            '                       @confirm="createPlaylist"',
            '                       @cancel="showCreatePlaylist = false" />',

            '  <ShortcutsModal v-if="showShortcuts" @close="showShortcuts = false" />',
            '  <ChatRoom',
            '    :isOpen="showChat"',
            '    :isConnected="chatIsConnected"',
            '    :messages="chatMessages"',
            '    :onlineUsers="chatOnlineUsers"',
            '    :onlineCount="chatOnlineCount"',
            '    :unreadCount="chatUnreadCount"',
            '    :inputMessage="chatInputMessage"',
            '    :currentUserId="chatCurrentUserId()"',
            '    :formatChatTime="chatFormatTime"',
            '    :getMessageClass="chatGetMessageClass"',
            '    @open="handleOpenChat"',
            '    @close="handleCloseChat"',
            '    @send="chatSend"',
            '    @update:inputMessage="v => chatInputMessage = v"',
            '  />',
            '</div>'
        ].join('\n')
    };

    createApp(App).mount('#app');
})();