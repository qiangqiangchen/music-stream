/* 聊天功能 composable */
function useChat(auth) {
    var ref = Vue.ref;
    var computed = Vue.computed;

    var ws = null;
    var reconnectTimer = null;
    var reconnectAttempts = 0;
    var maxReconnectAttempts = 5;

    var isConnected = ref(false);
    var isOpen = ref(false);
    var messages = ref([]);
    var onlineUsers = ref([]);
    var onlineCount = computed(function() {
        return onlineUsers.value.length;
    });
    var inputMessage = ref('');

    // 新增：未读消息计数
    var unreadCount = ref(0);
    var chatRoomActive = ref(false);  // 聊天室是否打开

    // 连接 WebSocket
    function connect() {
        if (!auth.isAuthenticated.value) {
            console.log('[Chat] Not authenticated, skipping connect');
            return;
        }

        var token = localStorage.getItem('accessToken');
        if (!token) {
            console.log('[Chat] No access token found');
            return;
        }

        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            console.log('[Chat] Already connected or connecting');
            return;
        }

        var wsUrl = 'ws://localhost:8000/api/v1/ws?token=' + encodeURIComponent(token);

        console.log('[Chat] Connecting to:', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('[Chat] WebSocket connected');
            isConnected.value = true;
            isOpen.value = true;
            reconnectAttempts = 0;
            clearReconnectTimer();
            startHeartbeat();
        };

        ws.onmessage = function(event) {
            try {
                var data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('[Chat] Failed to parse message:', e);
            }
        };

        ws.onclose = function(event) {
            console.log('[Chat] WebSocket closed:', event.code, event.reason);
            isConnected.value = false;
            isOpen.value = false;
            stopHeartbeat();

            if (reconnectAttempts < maxReconnectAttempts && auth.isAuthenticated.value) {
                reconnectAttempts++;
                var delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                console.log('[Chat] Reconnecting in', delay, 'ms (attempt', reconnectAttempts, ')');
                reconnectTimer = setTimeout(connect, delay);
            }
        };

        ws.onerror = function(error) {
            console.error('[Chat] WebSocket error:', error);
        };
    }

    // 心跳保持连接
    var heartbeatInterval = null;

    function startHeartbeat() {
        stopHeartbeat();
        heartbeatInterval = setInterval(function() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }

    function clearReconnectTimer() {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
    }

    // 处理收到的消息
    function handleMessage(data) {
        switch (data.type) {
            case 'history':
                messages.value = data.messages || [];
                break;
            case 'chat':
            case 'system':
                messages.value.push(data);
                if (messages.value.length > 200) {
                    messages.value = messages.value.slice(-200);
                }

                // 如果是聊天消息，且聊天室未打开，增加未读计数
                if (data.type === 'chat' && !chatRoomActive.value) {
                    // 不计数自己发送的消息
                    if (data.user_id !== auth.user.value?.id) {
                        unreadCount.value++;
                    }
                }
                break;
            case 'user_list':
                onlineUsers.value = data.users || [];
                break;
            case 'error':
                console.warn('[Chat] Server error:', data.message);
                break;
            case 'pong':
                break;
        }
    }

    // 发送消息
    function sendMessage() {
        var content = inputMessage.value.trim();
        if (!content || content.length > 500) {
            return;
        }

        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.warn('[Chat] WebSocket not connected');
            return;
        }

        ws.send(JSON.stringify({
            type: 'chat',
            content: content
        }));

        inputMessage.value = '';
    }

    // 断开连接
    function disconnect() {
        clearReconnectTimer();
        stopHeartbeat();
        reconnectAttempts = maxReconnectAttempts;

        if (ws) {
            ws.close();
            ws = null;
        }

        isConnected.value = false;
        isOpen.value = false;
        messages.value = [];
        onlineUsers.value = [];
        unreadCount.value = 0;
    }

    // 打开聊天室
    function openChatRoom() {
        chatRoomActive.value = true;
        unreadCount.value = 0;  // 清空未读计数
    }

    // 关闭聊天室
    function closeChatRoom() {
        chatRoomActive.value = false;
    }

    // 格式化时间
    function formatChatTime(isoString) {
        if (!isoString) return '';
        var date = new Date(isoString);
        var hours = date.getHours().toString().padStart(2, '0');
        var minutes = date.getMinutes().toString().padStart(2, '0');
        return hours + ':' + minutes;
    }

    // 获取消息样式
    function getMessageClass(msg, currentUserId) {
        if (msg.type === 'system') return 'chat-message-system';
        if (msg.user_id === currentUserId) return 'chat-message-self';
        return 'chat-message-other';
    }

    return {
        isConnected,
        isOpen,
        messages,
        onlineUsers,
        onlineCount,
        unreadCount,           // 新增
        inputMessage,
        chatRoomActive,        // 新增
        connect,
        disconnect,
        sendMessage,
        openChatRoom,          // 新增
        closeChatRoom,         // 新增
        formatChatTime,
        getMessageClass
    };
}