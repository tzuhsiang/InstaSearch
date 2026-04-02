<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import { Send, Bot, User, Sparkles, Trash2 } from 'lucide-vue-next'

const messages = ref([
    { 
      role: 'assistant', 
      text: '你好！我是透過 LangGraph 連接 MCP Server 的 InstaSearch 助理。我可以即時幫你查詢並分析最新的 Instagram 食記與發文趨勢。你想查詢什麼呢？',
      html: marked('你好！我是透過 LangGraph 連接 MCP Server 的 InstaSearch 助理。我可以即時幫你查詢並分析最新的 Instagram 食記與發文趨勢。你想查詢什麼呢？'),
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

const clearHistory = () => {
    messages.value = [
        { 
          role: 'assistant', 
          text: '對話已清除。你好，我可以為你做什麼？',
          html: marked('對話已清除。你好，我可以為你做什麼？'),
          isGenerating: false,
          reasoning: []
        }
    ]
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
        html: '<p style="color:var(--text-secondary);"><span class="loading-pulse"></span> 等待模型產出...</p>',
        isGenerating: true,
        reasoning: [],
        suggestions: [],
        error: false
    }
    messages.value.push(assistMsg)
    scrollToBottom()
    
    loading.value = true
    let isFirstChunk = true;
    
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
                            assistMsg.reasoning.push({ text: data.content, isStep: data.type === 'step' })
                        } else if (data.type === 'result') {
                            assistMsg.isGenerating = false // Close reasoning box when result starts
                        } else if (data.type === 'stream_text') {
                            if (isFirstChunk) {
                                assistMsg.html = ''
                                assistMsg.text = ''
                                isFirstChunk = false
                            }
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
  <div class="page-container w-full h-screen p-4 flex justify-center">
      <!-- Main Chat UI Container, replacing full-width with a nice centered layout -->
      <div class="chat-wrapper w-full max-w-4xl flex flex-col items-center h-full rounded-[24px] glass-panel shadow-[0_0_40px_rgba(0,0,0,0.3)] border border-[var(--glass-border)] bg-[rgba(22,27,34,0.6)] overflow-hidden">
        
        <!-- Header -->
        <div class="chat-header w-full shrink-0 flex justify-between items-center px-6 py-4 border-b border-[var(--glass-border)] bg-[rgba(22,27,34,0.4)] backdrop-blur-md">
            <h1 class="page-title flex items-center gap-2 text-[1.2rem] font-bold tracking-wide text-[var(--accent-primary)]">
                <Sparkles class="text-[var(--accent-primary)]" size="22" /> InstaSearch Agent
            </h1>
            <div class="flex items-center gap-5">
                <div class="status-indicator flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
                    <span class="status-dot" :class="loading ? 'busy' : 'online'"></span>
                    <span>{{ loading ? '思考中...' : '線上' }}</span>
                </div>
                <button @click="clearHistory" class="clear-btn flex items-center gap-1.5 text-xs px-3 py-1.5 border border-[var(--glass-border)] text-[var(--text-secondary)] rounded-lg hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition-all">
                    <Trash2 size="14" /> 清除對話
                </button>
            </div>
        </div>
        
        <!-- Messages Area -->
        <div class="messages-area w-full flex-1 overflow-y-auto px-4 py-8 md:px-8" ref="chatContainer">
            <div class="flex flex-col gap-6">
                <!-- Message Loop -->
                <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
                    <div class="avatar shadow-md mt-1">
                        <!-- Using Bot / User Icons instead of SVGs -->
                        <Bot v-if="msg.role === 'assistant'" size="22" class="text-white opacity-80" />
                        <User v-else size="20" class="text-white" />
                    </div>
                    
                    <div class="message-content">
                        <!-- Reasoning Box (Matches index.html Green Style) -->
                        <details class="reasoning-box shadow-md" v-if="msg.role === 'assistant' && msg.reasoning && msg.reasoning.length > 0" :open="msg.isGenerating">
                            <summary class="flex items-center">展開思考與執行過程</summary>
                            <div class="reasoning-content mt-2 text-sm">
                                <div v-for="(r, i) in msg.reasoning" :key="i" class="reasoning-item py-1" :class="{'text-[var(--accent-primary)] font-medium': r.isStep}">
                                    {{ r.text }}
                                </div>
                            </div>
                        </details>
                        
                        <!-- Main text bubble -->
                        <div class="bubble markdown-body shadow-md" v-if="msg.html" v-html="msg.html"></div>

                        <!-- Suggestions Container -->
                        <div class="suggestions-container mt-3 pt-3" v-if="msg.role === 'assistant' && !msg.isGenerating && (msg.suggestions?.length > 0 || (idx === 0 && defaultSuggestions.length > 0))">
                            <div class="text-[0.8rem] text-[var(--text-secondary)] mb-2 tracking-wide uppercase font-semibold">💡 您可以試著問我：</div>
                            <div class="flex flex-wrap gap-2">
                                <button 
                                    v-for="sugg in (msg.suggestions?.length > 0 ? msg.suggestions : defaultSuggestions)" 
                                    :key="sugg"
                                    @click="sendSuggestion(sugg)" 
                                    class="suggestion-btn text-[0.85rem] px-3.5 py-1.5 border border-[var(--accent-primary)] text-[var(--accent-primary)] rounded-lg hover:bg-[var(--accent-primary)] hover:text-white transition-colors duration-200 shadow-sm bg-[rgba(88,166,255,0.05)]">
                                    {{ sugg }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Input Area -->
        <div class="input-area w-full p-4 md:p-6 bg-[rgba(1,4,9,0.5)] border-t border-[var(--glass-border)] backdrop-blur-sm">
            <div class="input-wrapper relative flex items-center max-w-3xl mx-auto">
                <input v-model="input" @keyup.enter="sendMessage" placeholder="例如：請問最近信義區有哪些熱門酒吧？" class="chat-input w-full bg-[#010409] border border-[var(--glass-border)] text-[var(--text-primary)] px-5 py-3.5 rounded-xl pr-14 focus:outline-none focus:border-[var(--accent-primary)] focus:-translate-y-[1px] transition-all shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]" />
                <button @click="sendMessage" class="send-btn absolute right-2.5 bg-[var(--accent-primary)] text-white p-2.5 rounded-lg disabled:opacity-50 disabled:bg-[var(--glass-border)] disabled:text-[var(--text-secondary)] hover:bg-blue-400 transition-all shadow-md active:scale-95" :disabled="loading || !input.trim()">
                    <Send size="18" />
                </button>
            </div>
        </div>
        
      </div>
  </div>
</template>

<style scoped>
.page-container {
    background: radial-gradient(circle at center, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

.message-wrapper {
    display: flex;
    gap: 16px;
    max-width: 90%;
    animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message-wrapper.user {
    align-self: flex-end;
    flex-direction: row-reverse;
}

.message-wrapper.assistant {
    align-self: flex-start;
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
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(88,166,255,0.2) 0%, rgba(35,134,54,0.1) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--glass-border);
    flex-shrink: 0;
}

.user .avatar {
    background: linear-gradient(135deg, var(--accent-primary) 0%, #3178c6 100%);
    border-color: var(--accent-primary);
}

.assistant .avatar {
    background: var(--bg-secondary);
}

.bubble {
    padding: 14px 20px;
    border-radius: 12px;
    background: var(--bg-secondary);
    line-height: 1.6;
    border: 1px solid var(--glass-border);
    font-size: 0.95rem;
    overflow-wrap: break-word;
    word-break: break-word;
    color: var(--text-primary);
}

.user .bubble {
    background: var(--accent-primary);
    color: white;
    border: none;
    border-bottom-right-radius: 2px;
}

.assistant .bubble {
    border-bottom-left-radius: 2px;
    background: rgba(33, 38, 45, 0.85); /* Slightly transparent github dark matching index.html */
    backdrop-filter: blur(8px);
}

.reasoning-box {
    background-color: rgba(35, 134, 54, 0.1);
    border-left: 3px solid #238636;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 12px;
    width: fit-content;
    max-width: 100%;
    transition: all 0.3s ease;
}

.reasoning-box summary {
    cursor: pointer;
    user-select: none;
    font-size: 0.85rem;
    font-weight: 500;
    color: #7ee787;
    outline: none;
    list-style: none; /* Hide default arrow */
    display: flex;
    align-items: center;
}

.reasoning-box summary::-webkit-details-marker {
    display: none;
}

.reasoning-box summary::before {
    content: '▶';
    display: inline-block;
    margin-right: 8px;
    font-size: 0.70rem;
    transition: transform 0.2s;
}

.reasoning-box[open] summary::before {
    transform: rotate(90deg);
}

.reasoning-content {
    color: #7ee787;
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.reasoning-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.status-dot.online {
    background-color: #238636;
    box-shadow: 0 0 5px #238636;
}

.status-dot.busy {
    background-color: #d29922;
    box-shadow: 0 0 5px #d29922;
    animation: statusPulse 1.5s infinite;
}

@keyframes statusPulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(210, 153, 34, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(210, 153, 34, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(210, 153, 34, 0); }
}

.loading-pulse {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #d29922;
    margin-right: 6px;
    animation: statusPulse 1.5s infinite;
}

/* markdown overrides matching index.html */
:deep(.markdown-body p) { margin-bottom: 0.75em; margin-top: 0; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
:deep(.markdown-body li) { margin-left: 1.5em; list-style-type: disc; margin-bottom: 0.25em; }
:deep(.markdown-body h1), :deep(.markdown-body h2), :deep(.markdown-body h3) { font-weight: 600; margin-top: 1.25em; margin-bottom: 0.5em; }
:deep(.markdown-body code) { background: rgba(110,118,129,0.4); padding: 0.2em 0.4em; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
</style>
