<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">项目列表</h2>
      <el-button type="primary" @click="router.push('/projects/new')">新建项目</el-button>
    </div>

    <el-table :data="projects" style="width: 100%" v-loading="loading" @row-click="goWorkspace">
      <el-table-column prop="name" label="项目名称" min-width="150">
        <template #default="{ row }">
          {{ row.name || '(未命名)' }}
        </template>
      </el-table-column>
      <el-table-column prop="project_type" label="项目类型" width="120">
        <template #default="{ row }">
          {{ row.project_type === 'new' ? '新项目' : '旧项目二开' }}
        </template>
      </el-table-column>
      <el-table-column label="目标报价" width="140">
        <template #default="{ row }">
          {{ formatWan(row.target_gross_cents) }}
        </template>
      </el-table-column>
      <el-table-column prop="stage" label="阶段" width="120">
        <template #default="{ row }">
          {{ stageLabel(row.stage) }}
        </template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户名称" width="140">
        <template #default="{ row }">
          {{ row.customer_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && projects.length === 0" description="暂无项目，点击上方按钮新建" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getProjects } from '@/api/projects'
import type { Project } from '@/types/project'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)

const STAGE_MAP: Record<string, string> = {
  input: '录入中',
  draft_ready: '草稿就绪',
  quote_ready: '方案就绪',
  completed: '已完成',
}

function stageLabel(stage: string): string {
  return STAGE_MAP[stage] || stage
}

function formatWan(cents: number): string {
  return `${(cents / 100 / 10000).toFixed(2)} 万元`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

function goWorkspace(row: Project) {
  router.push(`/projects/${row.id}`)
}

onMounted(async () => {
  loading.value = true
  try {
    const resp = await getProjects()
    projects.value = resp.items
  } finally {
    loading.value = false
  }
})
</script>
