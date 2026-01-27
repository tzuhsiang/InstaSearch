import { createRouter, createWebHistory } from 'vue-router'
import Search from '../views/Search.vue'
import Analysis from '../views/Analysis.vue'
import Agent from '../views/Agent.vue'
import Settings from '../views/Settings.vue'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'search',
            component: Search
        },
        {
            path: '/analysis',
            name: 'analysis',
            component: Analysis
        },
        {
            path: '/agent',
            name: 'agent',
            component: Agent
        },
        {
            path: '/settings',
            name: 'settings',
            component: Settings
        }
    ]
})

export default router
