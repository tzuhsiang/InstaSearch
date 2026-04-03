<script setup>
import { onMounted, onUnmounted } from 'vue'
import { X, Calendar, Star, MapPin } from 'lucide-vue-next'

const props = defineProps({
  post: {
    type: Object,
    required: true
  },
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const handleEsc = (e) => {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  window.addEventListener('keydown', handleEsc)
  // Disable scroll on body
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEsc)
  // Re-enable scroll
  document.body.style.overflow = ''
})
</script>

<template>
  <Transition name="fade">
    <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
      <Transition name="zoom">
        <div class="modal-content glass-panel" v-if="isOpen">
          <button class="close-header-btn" @click="emit('close')">
            <X size="24" />
          </button>

          <div class="modal-body">
            <!-- Left Side: Content Labels -->
            <div class="info-section">
              <div class="meta-row">
                <div class="meta-item">
                  <Calendar size="16" class="meta-icon" />
                  <span>{{ new Date(post.datetime).toLocaleString() }}</span>
                </div>
                <div class="meta-item score">
                  <Star size="16" class="meta-icon star" />
                  <span>相關度評分: {{ post.score.toFixed(2) }}</span>
                </div>
              </div>

              <h2 class="section-title">貼文內文</h2>
              <div class="content-text markdown-body">
                {{ post.content }}
              </div>

              <div class="extra-info" v-if="post.id">
                <div class="info-tag">ID: {{ post.id }}</div>
              </div>
            </div>

            <!-- Right Side: Images -->
            <div class="media-section" v-if="post.media && post.media.length">
              <div class="image-gallery">
                <img 
                  v-for="(m, idx) in post.media" 
                  :key="idx" 
                  :src="m.url" 
                  class="full-post-img"
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.modal-content {
  position: relative;
  width: 98%;
  max-width: 1600px;
  max-height: 95vh;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.close-header-btn {
  position: absolute;
  top: 1.25rem;
  right: 1.25rem;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: white;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s;
}

.close-header-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.modal-body {
  display: grid;
  grid-template-columns: 1fr 3fr;
  height: 100%;
  overflow: hidden;
}

@media (max-width: 768px) {
  .modal-body {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }
}

.media-section {
  background: #000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
}

.image-gallery {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  padding: 1.5rem;
  width: 100%;
}

.full-post-img {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.info-section {
  padding: 2.5rem;
  overflow-y: auto;
  background: rgba(30, 41, 59, 0.4);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  border-bottom: 1px solid var(--glass-border);
  padding-bottom: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.meta-icon {
  color: var(--accent-primary);
}

.meta-icon.star {
  color: #fbbf24;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.content-text {
  line-height: 1.8;
  color: var(--text-primary);
  font-size: 1rem;
  white-space: pre-wrap;
}

.extra-info {
  margin-top: auto;
  padding-top: 1rem;
}

.info-tag {
  display: inline-block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 4px 10px;
  border-radius: 6px;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.zoom-enter-active, .zoom-leave-active {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
}
.zoom-enter-from, .zoom-leave-to {
  transform: scale(0.95);
  opacity: 0;
}
</style>
