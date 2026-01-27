<script setup>
import { ref, onMounted, nextTick } from 'vue'
import axios from 'axios'
import { Send, Bot, User, Sparkles } from 'lucide-vue-next'

const messages = ref([
    { role: 'assistant', text: '你好！我是 AI 助手。我可以幫你查詢食記或解答問題。' }
])
const input = ref('')
const loading = ref(false)
const chatContainer = ref(null)

const scrollToBottom = async () => {
    await nextTick()
    if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
}

const sendMessage = async () => {
    if (!input.value.trim() || loading.value) return
    
    const text = input.value
    input.value = ''
    messages.value.push({ role: 'user', text })
    scrollToBottom()
    
    loading.value = true
    
    try {
        // Here we should call the Langflow API.
        setTimeout(() => {
            messages.value.push({ role: 'assistant', text: '目前 Langflow Agent 尚未連接。請確認後端 MCP Server 已啟動且 Langflow 已配置 Agent Flow。' })
            loading.value = false
            scrollToBottom()
        }, 1000)
        
    } catch (e) {
        messages.value.push({ role: 'assistant', text: '發生錯誤: ' + e.message })
        loading.value = false
        scrollToBottom()
    }
}
</script>

<template>
  <div class="page-container flex-col h-screen">
    <div class="page-header shrink-0">
       <h1 class="page-title flex items-center gap-2"><Sparkles class="text-accent-primary" /> AI Agent</h1>
    </div>
    
    <div class="glass-panel flex-1 flex flex-col overflow-hidden chat-box">
        <div class="messages-area flex-1 overflow-y-auto p-4" ref="chatContainer">
            <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
                <div class="avatar">
                    <Bot v-if="msg.role === 'assistant'" size="20" />
                    <User v-else size="20" />
                </div>
                <div class="bubble">
                    {{ msg.text }}
                </div>
            </div>
            <div v-if="loading" class="message-wrapper assistant">
                <div class="avatar"><Bot size="20" /></div>
                <div class="bubble loading-bubble">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
            </div>
        </div>
        
        <div class="input-area p-4 border-t border-glass-border">
            <div class="input-wrapper">
                <input v-model="input" @keyup.enter="sendMessage" placeholder="Ask something..." class="chat-input" />
                <button @click="sendMessage" class="send-btn" :disabled="loading || !input.trim()">
                    <Send size="18" />
                </button>
            </div>
        </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}
.chat-box {
    margin-bottom: 2rem;
}
.messages-area {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.message-wrapper {
    display: flex;
    gap: 12px;
    max-width: 80%;
}
.message-wrapper.user {
    align-self: flex-end;
    flex-direction: row-reverse;
}
.avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--bg-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--glass-border);
}
.bubble {
    padding: 12px 16px;
    border-radius: 16px;
    background: var(--bg-secondary);
    line-height: 1.5;
    border: 1px solid var(--glass-border);
}
.user .bubble {
    background: var(--accent-primary);
    color: white;
    border: none;
}
.loading-bubble {
    display: flex;
    gap: 4px;
    padding: 16px;
}
.dot {
    width: 6px;
    height: 6px;
    background: var(--text-secondary);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
    background: var(--bg-sidebar);
    border-bottom-left-radius: 16px;
    border-bottom-right-radius: 16px;
}
.input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}
.chat-input {
    width: 100%;
    background: var(--bg-primary);
    border: 1px solid var(--glass-border);
    padding: 14px;
    padding-right: 50px;
    border-radius: 12px;
    color: var(--text-primary);
    font-size: 1rem;
}
.chat-input:focus {
    outline: 2px solid var(--accent-primary);
    border-color: transparent;
}
.send-btn {
    position: absolute;
    right: 8px;
    background: var(--accent-primary);
    border: none;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: opacity 0.2s;
}
.send-btn:hover {
    opacity: 0.9;
}
.send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
.text-accent-primary {
    color: var(--accent-primary);
}
</style>
