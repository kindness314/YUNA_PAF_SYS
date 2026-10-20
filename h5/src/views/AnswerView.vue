<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { activeBatch, api } from '../api/client'
import type { Batch, FormTemplate } from '../types'

const batch = ref<Batch | null>(null)
const questions = ref<string[]>([])
const content = ref('')
const publishedAt = ref('')
const state = ref<'loading' | 'unpublished' | 'ok'>('loading')

onMounted(async () => {
  batch.value = await activeBatch()
  if (!batch.value) {
    state.value = 'unpublished'
    return
  }
  try {
    const { data } = await api.get<{ content: string; published_at: string | null }>(
      `/batches/${batch.value.id}/exam-answer`,
    )
    content.value = data.content
    publishedAt.value = data.published_at ?? ''
    state.value = 'ok'
  } catch {
    state.value = 'unpublished'
    return
  }
  // 题目取自笔试答卷模板，与作答页同源
  try {
    const { data } = await api.get<FormTemplate>(`/forms/${batch.value.id}/exam`)
    const rule = Array.isArray(data.schema_json?.rule) ? data.schema_json.rule : []
    questions.value = (rule as { title?: string; field?: string }[]).map(
      (f, i) => f.title ?? f.field ?? `题目 ${i + 1}`,
    )
  } catch {
    /* 无试卷模板时仅展示解析正文 */
  }
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="笔试解析" left-arrow @click-left="$router.back()" />
    <van-loading v-if="state === 'loading'" class="loading" size="24px" />
    <van-empty v-else-if="state === 'unpublished'" description="解析尚未发布，请留意协会通知" />
    <template v-else>
      <van-notice-bar
        v-if="publishedAt"
        wrapable
        :scrollable="false"
        :text="`发布时间:${publishedAt.slice(0, 19).replace('T', ' ')}`"
      />
      <van-cell-group v-if="questions.length" inset class="card" title="题目">
        <van-cell v-for="(q, i) in questions" :key="i" :title="`${i + 1}. ${q}`" />
      </van-cell-group>
      <van-cell-group inset class="card" title="参考答案与解析">
        <div class="answer">{{ content }}</div>
      </van-cell-group>
    </template>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
}
.loading {
  display: flex;
  justify-content: center;
  margin-top: 48px;
}
.card {
  margin-top: 16px;
}
.answer {
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}
</style>
