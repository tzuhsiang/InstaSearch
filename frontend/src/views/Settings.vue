<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Save, Loader2 } from 'lucide-vue-next'

const settings = ref({
    langflow_url: '',
    langflow_api_1: ''
})
const loading = ref(false)
const saving = ref(false)
const message = ref('')

const fetchSettings = async () => {
    loading.value = true
    try {
        const res = await axios.get('/api/settings')
        settings.value = res.data
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const saveSettings = async () => {
    saving.value = true
    message.value = ''
    try {
        await axios.post('/api/settings', settings.value)
        message.value = '設定已儲存 (Settings saved)'
        setTimeout(() => message.value = '', 3000)
    } catch (e) {
        message.value = '儲存失敗 (Failed to save)'
    } finally {
        saving.value = false
    }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
       <h1 class="page-title">系統設置</h1>
    </div>
    
    <div class="glass-panel text-white p-8 max-w-2xl">
        <div v-if="loading" class="flex justify-center p-4">
             <Loader2 class="animate-spin" />
        </div>
        <form v-else @submit.prevent="saveSettings" class="settings-form">
            <div class="form-group">
                <label>Langflow Base URL</label>
                <input v-model="settings.langflow_url" class="input-field" placeholder="http://langflow:7860" />
            </div>
            
            <div class="form-group">
                <label>Post Analysis API Endpoint</label>
                <input v-model="settings.langflow_api_1" class="input-field" placeholder="Full API URL" />
            </div>
            
            <div class="actions">
                <button type="submit" class="btn-primary" :disabled="saving" style="display: flex; align-items: center; gap: 8px;">
                    <Save size="18" />
                    {{ saving ? 'Saving...' : 'Save Settings' }}
                </button>
                <span v-if="message" class="message">{{ message }}</span>
            </div>
        </form>
    </div>
  </div>
</template>

<style scoped>
.glass-panel {
    padding: 2rem;
    max-width: 600px;
}
.settings-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}
.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.form-group label {
    font-size: 0.9rem;
    color: var(--text-secondary);
}
.actions {
    margin-top: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.message {
    color: var(--success);
    font-size: 0.9rem;
}
</style>
