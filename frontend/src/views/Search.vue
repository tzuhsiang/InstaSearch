<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import { Search, Loader2, Bot, Calendar } from 'lucide-vue-next'

const query = ref('')
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const results = ref([])
const total = ref(0)
const loading = ref(false)
const analyzing = ref(null)
const analysisResult = ref({})

const search = async () => {
    loading.value = true
    try {
        const params = {
            q: query.value,
            page: page.value,
            size: 10,
            start_date: startDate.value || undefined,
            end_date: endDate.value || undefined
        }

        const res = await axios.get('/api/search', { params })
        results.value = res.data.results
        total.value = res.data.total
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const analyzePost = async (post) => {
    analyzing.value = post.id
    try {
        const res = await axios.post('/api/analysis/post', { content: post.content })
        analysisResult.value[post.id] = res.data.result
    } catch (e) {
        analysisResult.value[post.id] = "Analysis failed."
    } finally {
        analyzing.value = null
    }
}

watch(page, search)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
       <h1 class="page-title">搜尋食記</h1>
    </div>
    
    <div class="glass-panel p-6 mb-8 filter-bar">
       <div class="filter-group">
          <input v-model="query" @keyup.enter="search" placeholder="請輸入關鍵字..." class="input-field search-input" />
          <div class="date-inputs">
             <Calendar size="18" class="text-secondary" />
             <input type="date" v-model="startDate" class="input-field date-field" />
             <span class="separator">-</span>
             <input type="date" v-model="endDate" class="input-field date-field" />
          </div>
          <button @click="search" class="btn-primary search-btn">
             <Search size="18" /> 搜尋
          </button>
       </div>
    </div>

    <div v-if="loading" class="loading-state">
        <Loader2 class="animate-spin" size="48" style="color: var(--accent-primary)" />
    </div>

    <div v-else-if="results.length === 0 && query" class="empty-state">
        <p>沒有找到相關結果</p>
    </div>

    <div v-else class="results-grid">
        <div v-for="post in results" :key="post.id" class="post-card glass-panel">
             <div class="post-header">
                 <span class="post-date">{{ new Date(post.datetime).toLocaleDateString() }}</span>
                 <span class="score-badge">Score: {{ post.score.toFixed(1) }}</span>
             </div>
             <div class="post-content">
                 <p>{{ post.content }}</p>
             </div>
             <div v-if="post.media.length" class="post-media">
                 <img v-for="(m, idx) in post.media.slice(0, 3)" :key="idx" :src="m.url" class="post-img" loading="lazy" />
             </div>
             
             <div class="post-actions">
                 <button @click="analyzePost(post)" class="btn-secondary analyze-btn" :disabled="analyzing === post.id">
                     <Loader2 v-if="analyzing === post.id" class="animate-spin" size="16" />
                     <Bot v-else size="16" />
                     {{ analysisResult[post.id] ? '重新分析' : '貼文分析' }}
                 </button>
             </div>
             
             <div v-if="analysisResult[post.id]" class="analysis-box">
                 <div class="analysis-header">
                    <Bot size="16" /> 
                    <strong>AI 分析結果</strong>
                 </div>
                 <p>{{ analysisResult[post.id] }}</p>
             </div>
        </div>
    </div>
    
    <div class="pagination" v-if="total > 0">
         <button class="btn-secondary" :disabled="page <= 1" @click="page--">上一頁</button>
         <span class="page-info">第 {{ page }} 頁</span>
         <button class="btn-secondary" @click="page++" :disabled="results.length < 10 && page * 10 >= total">下一頁</button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
    padding: 1.5rem;
}
.filter-group {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
}
.search-input {
    flex: 2;
    min-width: 200px;
}
.date-inputs {
    flex: 1.5;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--bg-secondary);
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid var(--glass-border);
}
.date-field {
    background: transparent;
    border: none;
    color: var(--text-primary);
    padding: 6px;
    outline: none;
}
.search-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
}
.loading-state, .empty-state {
    display: flex;
    justify-content: center;
    padding: 4rem;
    color: var(--text-secondary);
}
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
}
.post-card {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    transition: transform 0.2s;
}
.post-card:hover {
    transform: translateY(-2px);
}
.post-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.post-date {
    color: var(--text-secondary);
    font-size: 0.85rem;
}
.score-badge {
    background: rgba(34, 197, 94, 0.1);
    color: var(--success);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
}
.post-content p {
    margin: 0;
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: var(--text-primary);
}
.post-media {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
}
.post-img {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid var(--glass-border);
}
.post-actions {
    margin-top: auto;
}
.analyze-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
}
.analysis-box {
    background: linear-gradient(to right, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
    border: 1px solid rgba(59, 130, 246, 0.2);
    padding: 1rem;
    border-radius: 8px;
    margin-top: 0.5rem;
    font-size: 0.9rem;
}
.analysis-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 0.5rem;
    color: var(--accent-primary);
}
.pagination {
    margin-top: 3rem;
    margin-bottom: 3rem;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
}
.page-info {
    color: var(--text-secondary);
}
</style>
