<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import { activeBatch, api, errText } from '../api/client'
import type { Application, Batch, FormApi, FormTemplate } from '../types'

const batch = ref<Batch | null>(null)
const template = ref<FormTemplate | null>(null)
const application = ref<Application | null>(null)
const rule = ref<unknown[]>([])
const formData = ref<Record<string, unknown>>({})
const fApi = ref<FormApi | null>(null)
const submitting = ref(false)
const notice = ref('')

onMounted(async () => {
  batch.value = await activeBatch()
  if (!batch.value) return
  if (batch.value.stage !== 'exam') {
    notice.value = `当前批次处于「${batch.value.stage}」阶段，暂未开放笔试提交`
    return
  }
  try {
    application.value = (
      await api.get<Application>('/applications/mine', { params: { batch_id: batch.value.id } })
    ).data
  } catch {
    notice.value = '尚未报名，请先完成报名'
    return
  }
  if (application.value.exempt_exam) {
    notice.value = '您是免笔试考生，无需提交答卷'
    return
  }
  try {
    template.value = (await api.get<FormTemplate>(`/forms/${batch.value.id}/exam`)).data
  } catch {
    notice.value = '笔试题尚未发布'
    return
  }
  rule.value = Array.isArray(template.value.schema_json?.rule)
    ? template.value.schema_json.rule
    : []
})

async function submit() {
  if (!application.value || !template.value) return
  if (fApi.value) {
    try {
      await fApi.value.validate()
    } catch {
      showFailToast('答卷未通过校验')
      return
    }
  }
  submitting.value = true
  try {
    await api.post('/submissions', {
      application_id: application.value.id,
      template_id: template.value.id,
      data: formData.value,
    })
    showSuccessToast('提交成功，窗口期内可重复修改')
  } catch (e) {
    showFailToast(errText(e, '提交失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="笔试答卷" left-arrow @click-left="$router.back()" />
    <van-notice-bar v-if="notice" :text="notice" class="card" />
    <template v-if="rule.length">
      <div class="card paper">
        <form-create-mobile v-model="formData" :rule="rule" :api="fApi" />
      </div>
      <div class="submit">
        <van-button type="primary" block round :loading="submitting" @click="submit">
          提交答卷
        </van-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 96px;
}
.card {
  margin-top: 16px;
}
.paper {
  background: #fff;
  padding: 12px 4px;
}
.submit {
  position: fixed;
  bottom: 16px;
  left: 16px;
  right: 16px;
}
</style>
