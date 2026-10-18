<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import { activeBatch, api, errText } from '../api/client'
import type { Batch, FormApi, FormTemplate } from '../types'

const batch = ref<Batch | null>(null)
const rule = ref<unknown[]>([])
const formData = ref<Record<string, unknown>>({})
const fApi = ref<FormApi | null>(null)
const fixed = ref({ name: '', phone: '', dept_choice: '' })
const studentNo = localStorage.getItem('username') ?? ''
const submitting = ref(false)

onMounted(async () => {
  batch.value = await activeBatch()
  if (!batch.value) {
    showFailToast('暂无进行中的批次')
    return
  }
  try {
    const { data } = await api.get<FormTemplate>(`/forms/${batch.value.id}/application`)
    rule.value = Array.isArray(data.schema_json?.rule) ? data.schema_json.rule : []
  } catch {
    rule.value = [] // 未发布动态表单时仅填固定字段
  }
})

async function submit() {
  if (!batch.value) return
  if (!fixed.value.name || !fixed.value.phone || !fixed.value.dept_choice) {
    showFailToast('请完整填写基本信息')
    return
  }
  if (fApi.value) {
    try {
      await fApi.value.validate()
    } catch {
      showFailToast('动态表单未通过校验')
      return
    }
  }
  submitting.value = true
  try {
    await api.post('/applications', {
      batch_id: batch.value.id,
      student_no: studentNo,
      name: fixed.value.name,
      phone: fixed.value.phone,
      dept_choice: fixed.value.dept_choice,
      extra: formData.value,
    })
    showSuccessToast('报名成功')
  } catch (e) {
    showFailToast(errText(e, '提交失败，请确认是否已报名'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="我要报名" left-arrow @click-left="$router.back()" />
    <van-cell-group inset class="card" v-if="batch">
      <van-cell title="批次" :value="batch.name" />
      <van-field v-model="studentNo" label="学号" readonly />
      <van-field
        v-model="fixed.name"
        label="姓名"
        placeholder="请输入姓名"
        :rules="[{ required: true }]"
      />
      <van-field
        v-model="fixed.phone"
        label="手机号"
        type="tel"
        placeholder="请输入手机号"
        :rules="[{ required: true }]"
      />
      <van-field
        v-model="fixed.dept_choice"
        label="部门志愿"
        placeholder="如：技术部 / 宣传部"
        :rules="[{ required: true }]"
      />
    </van-cell-group>

    <div v-if="rule.length" class="card dynamic">
      <div class="dynamic-title">补充信息</div>
      <form-create-mobile v-model="formData" :rule="rule" :api="fApi" />
    </div>

    <div class="submit">
      <van-button type="primary" block round :loading="submitting" @click="submit">
        提交报名
      </van-button>
  </div>
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
.dynamic {
  background: #fff;
  padding: 12px 4px;
}
.dynamic-title {
  font-weight: 600;
  padding: 0 16px 8px;
}
.submit {
  position: fixed;
  bottom: 16px;
  left: 16px;
  right: 16px;
}
</style>
