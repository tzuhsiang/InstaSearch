<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import { Send, Bot, User, Sparkles, Trash2, X } from 'lucide-vue-next'
import { useUIStore } from '../stores/ui'

const ui = useUIStore()

const messages = ref([
    { 
      role: 'assistant', 
      text: '你好！我是 InstaSearch 助理。我可以即時幫你查詢並分析最新的 Instagram 食記與發文趨勢。你想查詢什麼呢？',
      html: marked('你好！我是 InstaSearch 助理。我可以幫你查詢並分析最新的 Instagram 食記與發文趨勢。你想查詢什麼呢？'),
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
        const res = await fetch('/api/chat/config')
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
    
    const history = messages.value.map(m => ({ role: m.role, content: m.text }))
    messages.value.push({ role: 'user', text, html: marked(text) })
    
    const assistMsg = {
        role: 'assistant',
        text: '',
        html: '<p style="color:var(--text-secondary);"><span class="loading-pulse"></span> 模型思考中...</p>',
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
        const response = await fetch('/api/chat/chat', {
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
                            assistMsg.isGenerating = false 
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
  <div class="agent-chat-container">
      <!-- Chat Header -->
      <div class="chat-header">
          <div class="header-main">
              <Sparkles class="sparkle-icon" size="20" />
              <span class="header-title">AI Assistant</span>
          </div>
          <div class="header-actions">
              <button @click="clearHistory" class="icon-btn" title="清除對話">
                  <Trash2 size="18" />
              </button>
              <button @click="ui.closeAgent" class="icon-btn close-btn" title="關閉">
                  <X size="20" />
              </button>
          </div>
      </div>

      <!-- Messages Area -->
      <div class="messages-area" ref="chatContainer">
          <div class="messages-stack">
              <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
                  <div class="avatar">
                      <Bot v-if="msg.role === 'assistant'" size="18" class="bot-icon" />
                      <User v-else size="18" class="user-icon" />
                  </div>
                  
                  <div class="message-content">
                      <!-- Reasoning Box -->
                      <details class="reasoning-box" v-if="msg.role === 'assistant' && msg.reasoning && msg.reasoning.length > 0" :open="msg.isGenerating">
                          <summary>展開思考過程</summary>
                          <div class="reasoning-content">
                              <div v-for="(r, i) in msg.reasoning" :key="i" class="reasoning-item" :class="{'step-item': r.isStep}">
                                  {{ r.text }}
                              </div>
                          </div>
                      </details>
                      
                      <!-- Main bubble -->
                      <div class="bubble markdown-body" v-if="msg.html" v-html="msg.html"></div>

                      <!-- Suggestions -->
                      <div class="suggestions-box" v-if="msg.role === 'assistant' && !msg.isGenerating && (msg.suggestions?.length > 0 || (idx === 0 && defaultSuggestions.length > 0))">
                          <div class="suggestion-tip">建議問題：</div>
                          <div class="suggestion-list">
                              <button 
                                  v-for="sugg in (msg.suggestions?.length > 0 ? msg.suggestions : defaultSuggestions)" 
                                  :key="sugg"
                                  @click="sendSuggestion(sugg)" 
                                  class="suggestion-pill">
                                  {{ sugg }}
                              </button>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
      </div>
      
      <!-- Input Area -->
      <div class="input-area">
          <div class="input-wrapper">
              <textarea 
                v-model="input" 
                @keyup.enter.exact="sendMessage" 
                placeholder="輸入指令..." 
                rows="1"
                class="chat-textarea"
              ></textarea>
              <button @click="sendMessage" class="send-btn" :disabled="loading || !input.trim()">
                  <Send size="20" />
              </button>
          </div>
          <div class="footer-tag">Powered by LangGraph & MCP</div>
      </div>
  </div>
</template>

<style scoped>
.agent-chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-sidebar);
    color: var(--text-primary);
    border-left: 1px solid var(--glass-border);
}

.chat-header {
    padding: 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--glass-border);
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(10px);
}

.header-main {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.sparkle-icon {
    color: var(--accent-primary);
}

.header-title {
    font-weight: 700;
    letter-spacing: 0.5px;
    background: linear-gradient(to right, #fff, var(--text-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.header-actions {
    display: flex;
    gap: 0.5rem;
}

.icon-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 6px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}

.icon-btn:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-primary);
}

.close-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
}

.messages-area {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
}

.messages-stack {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.message-wrapper {
    display: flex;
    gap: 1rem;
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

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 1px solid var(--glass-border);
}

.assistant .avatar {
    background: var(--bg-secondary);
}

.user .avatar {
    background: var(--accent-primary);
}

.message-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.user .message-content {
    align-items: flex-end;
}

.bubble {
    padding: 0.75rem 1rem;
    border-radius: 12px;
    font-size: 0.95rem;
    line-height: 1.5;
    word-break: break-all;
}

.assistant .bubble {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border-bottom-left-radius: 2px;
}

.user .bubble {
    background: var(--accent-primary);
    color: white;
    border-bottom-right-radius: 2px;
}

.reasoning-box {
    background: rgba(34, 197, 94, 0.05);
    border-left: 2px solid var(--success);
    margin-bottom: 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
}

.reasoning-box summary {
    padding: 6px 12px;
    cursor: pointer;
    color: var(--success);
    font-weight: 500;
}

.reasoning-content {
    padding: 8px 12px;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.step-item {
    color: var(--accent-primary);
    font-weight: 500;
}

.suggestions-box {
    margin-top: 1rem;
    border-top: 1px solid var(--glass-border);
    padding-top: 0.75rem;
}

.suggestion-tip {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
}

.suggestion-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.suggestion-pill {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.2);
    color: var(--accent-primary);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
}

.suggestion-pill:hover {
    background: var(--accent-primary);
    color: white;
}

.input-area {
    padding: 1.25rem;
    background: rgba(15, 23, 42, 0.8);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--glass-border);
}

.input-wrapper {
    position: relative;
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    background: var(--bg-primary);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 8px;
}

.chat-textarea {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-primary);
    padding: 8px;
    resize: none;
    outline: none;
    font-family: inherit;
    font-size: 0.95rem;
    max-height: 120px;
}

.send-btn {
    background: var(--accent-primary);
    color: white;
    border: none;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
}

.send-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.footer-tag {
    text-align: center;
    font-size: 0.65rem;
    color: var(--text-secondary);
    margin-top: 0.75rem;
    letter-spacing: 1px;
}

.loading-pulse {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-primary);
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% { transform: scale(0.8); opacity: 0.5; }
    50% { transform: scale(1.1); opacity: 1; }
    100% { transform: scale(0.8); opacity: 0.5; }
}

/* Scrollbar */
.messages-area::-webkit-scrollbar {
    width: 5px;
}
.messages-area::-webkit-scrollbar-track {
    background: transparent;
}
.messages-area::-webkit-scrollbar-thumb {
    background: var(--glass-border);
    border-radius: 10px;
}
</style>
