<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import type { Batch, DesignerHandle, FormTemplate } from '../types'

const batches = ref<Batch[]>([])
const batchId = ref<number>()
const kind = ref<'application' | 'exam'>('application')
const name = ref('')
const version = ref(0)
const designer = ref<DesignerHandle | null>(null)

async function loadBatches() {
  batches.value = (await api.get<Batch[]>('/batches')).data
  batchId.value = batches.value.find((b) => b.is_active)?.id ?? batches.value[0]?.id
  await loadCurrent()
}

async function loadCurrent() {
  if (!batchId.value || !designer.value) return
  try {
    const { data } = await api.get<FormTemplate>(`/forms/${batchId.value}/${kind.value}`)
    designer.value.setRule(Array.isArray(data.schema_json?.rule) ? data.schema_json.rule : [])
    name.value = data.name
    version.value = data.version
  } catch {
    designer.value.setRule([])
    name.value = ''
    version.value = 0
  }
}

async function onKindOrBatchChange() {
  await nextTick() // 等 fc-designer 挂载完成
  await loadCurrent()
}

async function save() {
  if (!batchId.value || !designer.value) return
  const rule = designer.value.getRule()
  const { data } = await api.put<FormTemplate>(`/forms/${batchId.value}/${kind.value}`, {
    name: name.value,
    schema_json: { rule },
  })
  version.value = data.version
  ElMessage.success(`已保存为 v${data.version}，考生端即刻生效`)
}

onMounted(async () => {
  await loadBatches()
  await nextTick()
  await loadCurrent()
})
</script>

<template>
  <el-card>
    <template #header>表单设计（form-create 可视化设计器）</template>
    <div class="bar">
      <el-select v-model="batchId" style="width: 220px" placeholder="批次" @change="onKindOrBatchChange">
        <el-option v-for="b in batches" :key="b.id" :label="b.name" :value="b.id" />
      </el-select>
      <el-select v-model="kind" style="width: 160px" @change="onKindOrBatchChange">
        <el-option label="报名表单" value="application" />
        <el-option label="笔试答卷" value="exam" />
      </el-select>
      <el-input v-model="name" style="width: 220px" placeholder="表单名称" />
      <el-tag v-if="version > 0" type="info">当前 v{{ version }}</el-tag>
      <el-button type="primary" @click="save">保存发布</el-button>
    </div>
    <fc-designer ref="designer" style="height: 640px" />
  </el-card>
</template>

<style scoped>
.bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}
</style>
