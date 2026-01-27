<script setup>
import Sidebar from './components/Sidebar.vue'
</script>

<template>
  <Sidebar />
  <router-view class="flex-1" />
</template>

<style scoped>
.flex-1 {
    flex: 1;
}
</style>
