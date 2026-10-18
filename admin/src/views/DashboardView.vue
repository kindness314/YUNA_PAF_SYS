<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { Batch, BatchStats, FunnelKey } from '../types'

const route = useRoute()
const batches = ref<Batch[]>([])
const batchId = ref<number>()
const stats = ref<BatchStats | null>(null)

const FUNNEL_LABELS: Record<FunnelKey, string> = {
  applied: '报名',
  submitted: '交卷',
  advanced: '进面',
  interviewed: '已面',
  admitted: '拟录取',
}

const fullscreenLink = computed(() => `${route.path}?fullscreen=1`)

async function loadBatches() {
  batches.value = (await api.get<Batch[]>('/batches')).data
  batchId.value = batches.value.find((b) => b.is_active)?.id ?? batches.value[0]?.id
  if (batchId.value) await loadStats()
}

async function loadStats() {
  if (!batchId.value) return
  stats.value = (await api.get<BatchStats>(`/batches/${batchId.value}/stats`)).data
}

const funnelOption = computed(() => {
  const f = stats.value?.funnel
  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'funnel',
        left: '8%',
        width: '84%',
        top: 8,
        bottom: 8,
        label: { show: true, position: 'inside', formatter: '{b} {c}' },
        data: (Object.keys(FUNNEL_LABELS) as FunnelKey[]).map((k) => ({
          name: FUNNEL_LABELS[k],
          value: f?.[k] ?? 0,
        })),
      },
    ],
  }
})

const rate = (a: number, b: number) => (b > 0 ? `${Math.round((a / b) * 100)}%` : '-')

onMounted(loadBatches)
</script>

<template>
  <div>
    <div class="bar">
      <el-select v-model="batchId" style="width: 240px" placeholder="选择批次" @change="loadStats">
        <el-option
          v-for="b in batches"
          :key="b.id"
          :label="`${b.name}（${b.stage}）`"
          :value="b.id"
        />
      </el-select>
      <router-link v-if="route.query.fullscreen !== '1'" :to="fullscreenLink">
        <el-button>投屏模式</el-button>
      </router-link>
    </div>

    <el-row v-if="stats" :gutter="16" class="cards">
      <el-col v-for="(v, k) in stats.funnel" :key="k" :span="4">
        <el-card>
          <el-statistic :title="FUNNEL_LABELS[k as FunnelKey] ?? k" :value="v" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card><v-chart class="chart" :option="funnelOption" autoresize /></el-card>
      </el-col>
      <el-col :span="14">
        <el-card>
          <template #header>各部门进度总表</template>
          <el-table :data="stats?.dept_stats ?? []" stripe>
            <el-table-column prop="dept" label="部门" min-width="90" />
            <el-table-column prop="applied" label="报名" width="70" />
            <el-table-column prop="exempt_exam" label="免笔试" width="70" />
            <el-table-column prop="submitted" label="交卷" width="70" />
            <el-table-column prop="advanced" label="进面" width="70" />
            <el-table-column prop="admitted" label="拟录取" width="70" />
            <el-table-column label="录取率" width="80">
              <template #default="{ row }">{{ rate(row.admitted, row.applied) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.cards {
  margin-bottom: 16px;
}
.chart {
  height: 320px;
}
</style>
