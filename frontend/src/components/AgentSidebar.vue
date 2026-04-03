<script setup>
import { useUIStore } from '../stores/ui'
import AgentChat from './AgentChat.vue'

const ui = useUIStore()
</script>

<template>
  <Transition name="slide">
    <aside v-if="ui.isAgentOpen" class="agent-sidebar">
      <AgentChat />
    </aside>
  </Transition>
</template>

<style scoped>
.agent-sidebar {
  width: 33.333%;
  height: 100vh;
  position: relative;
  z-index: 100;
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.3);
  background: var(--bg-sidebar);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@media (max-width: 1024px) {
  .agent-sidebar {
    width: 50%;
  }
}

@media (max-width: 768px) {
  .agent-sidebar {
    width: 100%;
    position: fixed;
    right: 0;
    top: 0;
  }
}
</style>
