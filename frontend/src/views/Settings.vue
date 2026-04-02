<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Save, Loader2 } from 'lucide-vue-next'

const settings = ref({
    azure_openai_api_key: '',
    azure_openai_endpoint: '',
    azure_deployment_name: ''
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
                <label>Azure OpenAI API Key</label>
                <input type="password" v-model="settings.azure_openai_api_key" class="input-field" placeholder="API Key" />
            </div>
            
            <div class="form-group">
                <label>Azure OpenAI Endpoint</label>
                <input v-model="settings.azure_openai_endpoint" class="input-field" placeholder="https://<resource>.openai.azure.com/" />
            </div>

            <div class="form-group">
                <label>Azure Deployment Name</label>
                <input v-model="settings.azure_deployment_name" class="input-field" placeholder="e.g. gpt-4o" />
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
.input-field {
    background: var(--bg-primary);
    border: 1px solid var(--glass-border);
    padding: 10px;
    border-radius: 8px;
    color: white;
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
