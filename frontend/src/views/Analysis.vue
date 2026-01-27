<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const chartData = ref({
  labels: [],
  datasets: []
})
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8' }
    },
    x: {
        grid: { display: false },
        ticks: { color: '#94a3b8' }
    }
  },
  plugins: {
    legend: { display: false }
  }
}
const loading = ref(true)

const fetchData = async () => {
    try {
        const res = await axios.get('/api/analysis/trend')
        const data = res.data.data
        // Sort by date
        data.sort((a, b) => new Date(a.date) - new Date(b.date))
        
        chartData.value = {
            labels: data.map(d => d.date),
            datasets: [{
                label: '發文數',
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: '#3b82f6',
                borderWidth: 3,
                data: data.map(d => d.count),
                fill: true,
                tension: 0.4
            }]
        }
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

onMounted(fetchData)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
       <h1 class="page-title">數據分析</h1>
    </div>
    
    <div class="glass-panel p-6 chart-container">
       <h3 class="chart-title">每月發文趨勢</h3>
       <div class="chart-wrapper" v-if="!loading">
           <Line :data="chartData" :options="chartOptions" />
       </div>
       <div v-else class="loading">Loading...</div>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
    padding: 2rem;
    height: 500px;
    display: flex;
    flex-direction: column;
}
.chart-title {
    margin-top: 0;
    margin-bottom: 2rem;
    font-weight: 500;
}
.chart-wrapper {
    flex: 1;
    position: relative;
}
.loading {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
}
</style>
