import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
    const isAgentOpen = ref(false)
    const pendingSearch = ref(null)

    function toggleAgent() {
        isAgentOpen.value = !isAgentOpen.value
    }

    function openAgent() {
        isAgentOpen.value = true
    }

    function closeAgent() {
        isAgentOpen.value = false
    }

    function triggerSearch(params) {
        // params: { query, start_date, end_date }
        pendingSearch.value = { ...params, _ts: Date.now() }
    }

    return {
        isAgentOpen,
        pendingSearch,
        toggleAgent,
        openAgent,
        closeAgent,
        triggerSearch
    }
})
