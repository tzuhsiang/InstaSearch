import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        host: true, // Listen on all addresses
        port: 3000,
        strictPort: true,
        proxy: {
            '/api': {
                target: 'http://backend:8000',
                changeOrigin: true
            },
            '/images': {
                target: 'http://backend:8000',
                changeOrigin: true
            }
        }
    }
})
