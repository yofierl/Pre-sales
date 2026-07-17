<template>
  <div>
    <!-- 材料上传 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <span>上传材料</span>
      </template>

      <el-upload
        :http-request="handleUpload"
        :show-file-list="false"
        accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg"
        :disabled="uploading"
      >
        <el-button type="primary" :loading="uploading">选择文件</el-button>
        <template #tip>
          <span style="font-size: 12px; color: #999; margin-left: 12px">
            支持 PDF、Word、Excel、图片格式
          </span>
        </template>
      </el-upload>

      <el-table :data="materials" style="width: 100%; margin-top: 16px" v-if="materials.length > 0">
        <el-table-column prop="original_name" label="文件名" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="parse_status" label="解析状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.parse_status === 'succeeded'" type="success" size="small">成功</el-tag>
            <el-tag v-else-if="row.parse_status === 'failed'" type="danger" size="small">失败</el-tag>
            <el-tag v-else size="small">待解析</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 补充说明和启动分析 -->
    <el-card>
      <template #header>
        <span>启动需求分析</span>
      </template>
      <el-input
        v-model="supplement"
        type="textarea"
        :rows="3"
        placeholder="可选：补充说明，例如项目背景、重点功能等"
        style="margin-bottom: 16px"
      />
      <el-button type="primary" :loading="analyzing" @click="handleStartAnalysis" :disabled="analyzing">
        {{ analyzing ? '分析中…' : '生成需求草稿' }}
      </el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMaterials, uploadMaterial, deleteMaterial } from '@/api/materials'
import { startAnalysisRun, getRun } from '@/api/runs'
import type { MaterialItem } from '@/api/materials'
import type { RunResponse } from '@/types/run'

const props = defineProps<{ projectId: string }>()
const emit = defineEmits<{
  analysisDone: [payload: RunResponse]
}>()

const materials = ref<MaterialItem[]>([])
const uploading = ref(false)
const analyzing = ref(false)
const supplement = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function loadMaterials() {
  try {
    const resp = await getMaterials(props.projectId)
    materials.value = resp.items
  } catch { /* 静默处理 */ }
}

async function handleUpload(options: { file: File; onSuccess?: () => void }) {
  uploading.value = true
  try {
    await uploadMaterial(props.projectId, options.file)
    ElMessage.success('上传成功')
    await loadMaterials()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteMaterial(props.projectId, id)
    await loadMaterials()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handleStartAnalysis() {
  analyzing.value = true
  try {
    const { run_id } = await startAnalysisRun(props.projectId, supplement.value || undefined)
    // 开始轮询
    pollTimer = setInterval(async () => {
      try {
        const run = await getRun(run_id)
        if (run.status === 'succeeded') {
          stopPoll()
          analyzing.value = false
          emit('analysisDone', run)
        } else if (run.status === 'failed') {
          stopPoll()
          analyzing.value = false
          ElMessage.error(`分析失败: ${run.error_message || '未知错误'}`)
        }
      } catch {
        stopPoll()
        analyzing.value = false
        ElMessage.error('轮询任务状态失败')
      }
    }, 1000)
  } catch (err) {
    analyzing.value = false
    ElMessage.error(err instanceof Error ? err.message : '启动分析失败')
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(loadMaterials)
onUnmounted(stopPoll)
</script>
