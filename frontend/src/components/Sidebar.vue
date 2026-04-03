<script setup>
import { RouterLink, useRoute } from 'vue-router'
import { Search, BarChart2, Settings, Sparkles, Radio } from 'lucide-vue-next'

const route = useRoute()

const links = [
  { name: '搜尋', path: '/', icon: Search },
  { name: '分析', path: '/analysis', icon: BarChart2 },
  { name: '設置', path: '/settings', icon: Settings },
]
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <Radio class="logo-icon" />
      <span>InstaSearch</span>
    </div>
    <nav>
      <RouterLink 
        v-for="link in links" 
        :key="link.path" 
        :to="link.path"
        class="nav-item"
        :class="{ active: route.path === link.path }"
      >
        <component :is="link.icon" size="20" />
        <span>{{ link.name }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 3rem;
  color: var(--text-primary);
}

.logo-icon {
  color: var(--accent-primary);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  color: var(--text-secondary);
  transition: all 0.2s;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.nav-item:hover {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.1), transparent);
  color: var(--accent-primary);
  border-left: 3px solid var(--accent-primary);
}
</style>
