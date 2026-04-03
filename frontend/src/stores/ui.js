import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
    const isAgentOpen = ref(false)

    function toggleAgent() {
        isAgentOpen.value = !isAgentOpen.value
    }

    function openAgent() {
        isAgentOpen.value = true
    }

    function closeAgent() {
        isAgentOpen.value = false
    }

    return {
        isAgentOpen,
        toggleAgent,
        openAgent,
        closeAgent
    }
})
