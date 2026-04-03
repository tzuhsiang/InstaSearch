<script setup>
import Sidebar from './components/Sidebar.vue'
import AgentSidebar from './components/AgentSidebar.vue'
import { useUIStore } from './stores/ui'

const ui = useUIStore()
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    
    <main class="main-content" :class="{ 'with-sidebar': ui.isAgentOpen }">
      <router-view />
    </main>
    
    <AgentSidebar />
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  background: var(--bg-primary);
}

.main-content.with-sidebar {
  /* When sidebar is 1/3, main content should take the rest (minus the left sidebar) */
  /* But since it's in a flexbox, setting flex: 1 and having AgentSidebar at 1/3 width already handles it */
}

@media (max-width: 768px) {
  .main-content.with-sidebar {
    /* On mobile, sidebar is fixed/overlay, so main stays 100% */
  }
}
</style>
