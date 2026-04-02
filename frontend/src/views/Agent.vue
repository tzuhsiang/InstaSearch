<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import { Send, Bot, User, Sparkles } from 'lucide-vue-next'

const messages = ref([
    { 
      role: 'assistant', 
      text: '你好！我是 Instagram 食記分析助理。我可以即時幫你查詢並分析最新的 IG 食記。你想查詢什麼呢？',
      html: marked('你好！我是 Instagram 食記分析助理。我可以即時幫你查詢並分析最新的 IG 食記。你想查詢什麼呢？'),
      isGenerating: false,
      reasoning: []
    }
])
const input = ref('')
const loading = ref(false)
const chatContainer = ref(null)
const defaultSuggestions = ref([])

onMounted(async () => {
    try {
        const res = await fetch('http://localhost:8000/api/chat/config')
        if (res.ok) {
            const data = await res.json()
            if (data.default_suggestions) {
                defaultSuggestions.value = data.default_suggestions
            }
        }
    } catch (e) {
        console.warn("無法取得預設推薦問題")
    }
})

const scrollToBottom = async () => {
    await nextTick()
    if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
}

const sendSuggestion = (text) => {
    input.value = text
    sendMessage()
}

const sendMessage = async () => {
    if (!input.value.trim() || loading.value) return
    
    const text = input.value
    input.value = ''
    
    // 把目前的訊息存到 history，但不用存 reasoning 等細節，只要 role 與 content
    const history = messages.value.map(m => ({ role: m.role, content: m.text }))
    
    messages.value.push({ role: 'user', text, html: marked(text) })
    
    const assistMsg = {
        role: 'assistant',
        text: '',
        html: '',
        isGenerating: true,
        reasoning: [],
        suggestions: [],
        error: false
    }
    messages.value.push(assistMsg)
    scrollToBottom()
    
    loading.value = true
    
    try {
        const response = await fetch('http://localhost:8000/api/chat/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, history })
        })

        if (!response.ok) throw new Error("Network error")

        const reader = response.body.getReader()
        const decoder = new TextDecoder("utf-8")
        
        while (true) {
            const { value, done } = await reader.read()
            if (done) break
            
            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6))
                        if (data.type === 'reasoning' || data.type === 'step') {
                            assistMsg.reasoning.push(data.content)
                        } else if (data.type === 'stream_text') {
                            assistMsg.text += data.content
                            assistMsg.html = marked(assistMsg.text)
                        } else if (data.type === 'suggestions') {
                            assistMsg.suggestions = data.data
                        } else if (data.type === 'error') {
                            assistMsg.error = true
                            assistMsg.text += `\n⚠️ 錯誤: ${data.content}`
                            assistMsg.html = marked(assistMsg.text)
                        }
                    } catch(e) { }
                }
            }
            scrollToBottom()
        }
    } catch (e) {
        assistMsg.error = true
        assistMsg.text = "連線發生錯誤。請確認後端正在運行。"
        assistMsg.html = marked(assistMsg.text)
    } finally {
        assistMsg.isGenerating = false
        loading.value = false
        scrollToBottom()
    }
}
</script>

<template>
  <div class="page-container flex-col h-screen">
    <div class="page-header shrink-0 flex justify-between items-center">
       <h1 class="page-title flex items-center gap-2"><Sparkles class="text-accent-primary" /> AI Agent</h1>
    </div>
    
    <div class="glass-panel flex-1 flex flex-col overflow-hidden chat-box">
        <div class="messages-area flex-1 overflow-y-auto p-4" ref="chatContainer">
            <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper py-2" :class="msg.role">
                <div class="avatar">
                    <Bot v-if="msg.role === 'assistant'" size="20" />
                    <User v-else size="20" />
                </div>
                
                <div class="message-content">
                    <!-- Reasoning Box -->
                    <details class="reasoning-box mb-2" v-if="msg.role === 'assistant' && msg.reasoning && msg.reasoning.length > 0" :open="msg.isGenerating">
                        <summary>展開思考與執行過程</summary>
                        <div class="reasoning-content mt-2 text-sm text-[var(--accent-primary)]">
                            <div v-for="(r, i) in msg.reasoning" :key="i" class="reasoning-item py-1">
                                {{ r }}
                            </div>
                        </div>
                    </details>
                    
                    <!-- Main text bubble -->
                    <div class="bubble markdown-body" v-if="msg.html" v-html="msg.html"></div>
                    <div class="bubble loading-bubble ml-2" v-else-if="msg.isGenerating && !msg.html">
                         <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                    </div>

                    <!-- Suggestions (if present on assistant message) -->
                    <div class="suggestions-container mt-3" v-if="msg.role === 'assistant' && !msg.isGenerating && (msg.suggestions?.length > 0 || (idx === 0 && defaultSuggestions.length > 0))">
                        <div class="text-xs text-[var(--text-secondary)] mb-2">您可以試著問我：</div>
                        <div class="flex flex-wrap gap-2">
                            <button 
                                v-for="sugg in (msg.suggestions?.length > 0 ? msg.suggestions : defaultSuggestions)" 
                                :key="sugg"
                                @click="sendSuggestion(sugg)" 
                                class="suggestion-btn text-xs px-3 py-1 border border-[var(--accent-primary)] text-[var(--accent-primary)] rounded-md hover:bg-[var(--accent-primary)] hover:text-white transition-colors">
                                {{ sugg }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="input-area p-4 border-t border-[var(--glass-border)]">
            <div class="input-wrapper relative flex items-center">
                <input v-model="input" @keyup.enter="sendMessage" placeholder="Ask something..." class="chat-input w-full bg-[var(--bg-primary)] border border-[var(--glass-border)] text-white px-4 py-3 rounded-xl pr-12 focus:outline-none focus:border-[var(--accent-primary)]" />
                <button @click="sendMessage" class="send-btn absolute right-2 bg-[var(--accent-primary)] text-white p-2 rounded-lg disabled:opacity-50 transition-opacity" :disabled="loading || !input.trim()">
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
    gap: 1.5rem;
}
.message-wrapper {
    display: flex;
    gap: 16px;
    max-width: 90%;
}
.message-wrapper.user {
    align-self: flex-end;
    flex-direction: row-reverse;
}
.message-content {
    display: flex;
    flex-direction: column;
    max-width: calc(100% - 52px);
    width: 100%;
}
.user .message-content {
    align-items: flex-end;
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
    flex-shrink: 0;
}
.bubble {
    padding: 12px 18px;
    border-radius: 16px;
    background: var(--bg-secondary);
    line-height: 1.6;
    border: 1px solid var(--glass-border);
    font-size: 0.95rem;
    overflow-wrap: break-word;
    word-break: break-word;
}

/* markdown overrides */
:deep(.markdown-body p) { margin-bottom: 0.5em; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
:deep(.markdown-body li) { margin-left: 1.5em; list-style-type: disc; }
:deep(.markdown-body h1, .markdown-body h2, .markdown-body h3) { font-weight: 600; margin-top: 1em; margin-bottom: 0.5em; }

.user .bubble {
    background: var(--accent-primary);
    color: white;
    border: none;
    border-bottom-right-radius: 4px;
}
.assistant .bubble {
    border-bottom-left-radius: 4px;
}
.loading-bubble {
    display: inline-flex;
    gap: 4px;
    padding: 16px;
    width: fit-content;
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

.reasoning-box {
    background: rgba(88, 166, 255, 0.1);
    border-left: 4px solid var(--accent-primary);
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 8px;
    width: fit-content;
    max-width: 100%;
}

.reasoning-box summary {
    cursor: pointer;
    user-select: none;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--accent-primary);
    outline: none;
}

.text-accent-primary {
    color: var(--accent-primary);
}
</style>
