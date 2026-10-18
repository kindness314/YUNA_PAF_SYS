<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { errText, api } from '../api/client'
import type { Batch, Group, QueueEntry } from '../types'

const batches = ref<Batch[]>([])
const groups = ref<Group[]>([])
const batchId = ref<number>()
const groupId = ref<number>()
const entries = ref<QueueEntry[]>([])
const room = ref('1号房')
const checkinAppId = ref<number | undefined>(undefined)
const connected = ref(false)
let es: EventSource | null = null

async function loadBatches() {
  batches.value = (await api.get<Batch[]>('/batches')).data
  batchId.value = batches.value.find((b) => b.is_active)?.id ?? batches.value[0]?.id
  if (batchId.value) await loadGroups()
}

async function loadGroups() {
  closeSse()
  groupId.value = undefined
  entries.value = []
  if (!batchId.value) return
  groups.value = (await api.get<Group[]>('/queue/groups', { params: { batch_id: batchId.value } })).data
}

async function selectGroup() {
  closeSse()
  entries.value = []
  if (!groupId.value) return
  await loadEntries()
  openSse()
}

async function loadEntries() {
  if (!groupId.value) return
  entries.value = (await api.get<QueueEntry[]>(`/queue/groups/${groupId.value}/entries`)).data
}

// SSE 只当"刷新信号"用，数据一律重拉（PLAN.md 第 12 节）
function openSse() {
  const token = localStorage.getItem('token') ?? ''
  es = new EventSource(`/api/queue/groups/${groupId.value}/events?token=${token}`)
  es.onopen = () => (connected.value = true)
  es.onmessage = () => loadEntries()
  es.onerror = () => (connected.value = false)
}

function closeSse() {
  es?.close()
  es = null
  connected.value = false
}

async function checkin() {
  if (!checkinAppId.value || !groupId.value) return
  try {
    const { data } = await api.post<QueueEntry>('/queue/checkin', {
      group_id: groupId.value,
      application_id: checkinAppId.value,
    })
    ElMessage.success(`签到成功，号码 ${data.seq}`)
  } catch (e) {
    ElMessage.error(errText(e, '签到失败'))
  }
}

async function callNext() {
  if (!groupId.value) return
  const res = await api.post(`/queue/groups/${groupId.value}/call`, { room: room.value })
  if (res.status === 204) ElMessage.info('候考队列已空')
}

async function finish(id: number) {
  try {
    await api.post(`/queue/entries/${id}/finish`)
  } catch (e) {
    ElMessage.error(errText(e, '操作失败'))
  }
}

const STATUS_TEXT: Record<string, string> = {
  waiting: '候考',
  interviewing: '面试中',
  done: '已完成',
  skipped: '过号',
  absent: '缺考',
}

onMounted(loadBatches)
onUnmounted(closeSse)
</script>

<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>面试现场 · 叫号台</span>
        <el-tag :type="connected ? 'success' : 'info'" size="small">
          {{ connected ? '实时已连接' : '实时未连接（轮询兜底）' }}
        </el-tag>
      </div>
    </template>

    <div class="bar">
      <el-select v-model="batchId" style="width: 200px" placeholder="批次" @change="loadGroups">
        <el-option v-for="b in batches" :key="b.id" :label="b.name" :value="b.id" />
      </el-select>
      <el-select v-model="groupId" style="width: 180px" placeholder="面试组" @change="selectGroup">
        <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
      </el-select>
      <el-input-number v-model="checkinAppId" :controls="false" placeholder="报名记录ID" style="width: 140px" />
      <el-button @click="checkin">签到发号</el-button>
      <el-divider direction="vertical" />
      <el-input v-model="room" style="width: 110px" placeholder="房间" />
      <el-button type="primary" @click="callNext">叫下一位</el-button>
    </div>

    <el-table :data="entries" stripe>
      <el-table-column prop="seq" label="号码" width="80" />
      <el-table-column prop="application_id" label="报名ID" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'interviewing' ? 'warning' : row.status === 'done' ? 'success' : 'info'">
            {{ STATUS_TEXT[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="room" label="房间" width="110" />
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button v-if="row.status === 'interviewing'" size="small" type="success" @click="finish(row.id)">
            完成面试
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
</style>
