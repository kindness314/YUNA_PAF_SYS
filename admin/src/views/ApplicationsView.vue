<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Application, Batch } from '../types'

const batches = ref<Batch[]>([])
const batchId = ref<number>()
const dept = ref('')
const rows = ref<Application[]>([])
const loading = ref(false)

async function loadBatches() {
  batches.value = (await api.get<Batch[]>('/batches')).data
  batchId.value = batches.value.find((b) => b.is_active)?.id ?? batches.value[0]?.id
  await load()
}

async function load() {
  if (!batchId.value) return
  loading.value = true
  try {
    rows.value = (
      await api.get<Application[]>('/applications', {
        params: { batch_id: batchId.value, dept: dept.value || undefined, size: 100 },
      })
    ).data
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const header = ['学号', '姓名', '手机号', '部门', '来源', '免笔试', '状态']
  const lines = rows.value.map((r) =>
    [r.student_no, r.name, r.phone, r.dept_choice, r.source, r.exempt_exam ? '是' : '否', r.status].join(','),
  )
  const blob = new Blob(['\ufeff' + [header.join(','), ...lines].join('\n')], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `报名名单-${batchId.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadBatches)
</script>

<template>
  <el-card>
    <template #header>报名管理</template>
    <div class="bar">
      <el-select v-model="batchId" style="width: 220px" placeholder="批次" @change="load">
        <el-option v-for="b in batches" :key="b.id" :label="b.name" :value="b.id" />
      </el-select>
      <el-input v-model="dept" style="width: 180px" placeholder="按部门筛选" clearable @change="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="exportCsv">导出 CSV</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="student_no" label="学号" width="130" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="dept_choice" label="部门志愿" width="110" />
      <el-table-column prop="source" label="来源" width="90" />
      <el-table-column label="免笔试" width="80">
        <template #default="{ row }">{{ row.exempt_exam ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="created_at" label="报名时间" min-width="170" />
    </el-table>
  </el-card>
</template>

<style scoped>
.bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
