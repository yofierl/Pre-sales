<template>
  <div v-loading="loading">
    <!-- 创建模式：空白工作台 -->
    <template v-if="isCreating">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
        <h2 style="margin: 0">新建项目</h2>
        <div>
          <el-button @click="router.push('/projects')">返回列表</el-button>
        </div>
      </div>
      <ProjectForm @submit="handleCreate" />
    </template>

    <!-- 编辑模式：项目工作台 -->
    <template v-else-if="project">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
        <h2 style="margin: 0">{{ project.name || '(未命名)' }}</h2>
        <div>
          <el-button @click="router.push('/projects')">返回列表</el-button>
          <el-button type="primary" @click="showEdit = true">编辑</el-button>
          <el-button type="danger" plain @click="handleDelete">删除</el-button>
        </div>
      </div>

      <el-card style="margin-bottom: 20px">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">{{ project.name || '(未命名)' }}</el-descriptions-item>
          <el-descriptions-item label="项目类型">
            {{ project.project_type === 'new' ? '新项目' : '旧项目二开' }}
          </el-descriptions-item>
          <el-descriptions-item label="目标报价">{{ formatWan(project.target_gross_cents) }}</el-descriptions-item>
          <el-descriptions-item label="报价单位">{{ project.quote_company }}</el-descriptions-item>
          <el-descriptions-item label="报价日期">{{ project.quote_date }}</el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ project.customer_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="阶段">{{ stageLabel(project.stage) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(project.created_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card>
        <template #header>
          <span>角色配置</span>
        </template>
        <el-table :data="project.roles" style="width: 100%">
          <el-table-column prop="name" label="角色名称" />
          <el-table-column label="单价（元/人天）" width="180">
            <template #default="{ row }">
              {{ (row.unit_price_cents / 100).toFixed(0) }}
            </template>
          </el-table-column>
          <el-table-column label="是否必选" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.is_required" type="danger" size="small">必选</el-tag>
              <el-tag v-else type="info" size="small">可选</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEdit" title="编辑项目" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="editForm.customer_name" placeholder="请输入客户名称" />
        </el-form-item>
        <el-form-item label="目标报价">
          <el-input v-model="editForm.target_price_wan" placeholder="万元">
            <template #append>万元</template>
          </el-input>
        </el-form-item>
        <el-form-item label="报价单位">
          <el-input v-model="editForm.quote_company" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProject, createProject, updateProject, deleteProject } from '@/api/projects'
import ProjectForm from '@/components/ProjectForm.vue'
import type { Project, ProjectCreate } from '@/types/project'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const loading = ref(false)
const showEdit = ref(false)

const isCreating = computed(() => route.params.id === 'new')

const editForm = reactive({
  name: '',
  customer_name: '',
  target_price_wan: '',
  quote_company: '',
})

const STAGE_MAP: Record<string, string> = {
  input: '录入中',
  draft_ready: '草稿就绪',
  quote_ready: '方案就绪',
  completed: '已完成',
}

function stageLabel(stage: string): string {
  return STAGE_MAP[stage] || stage
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

function formatWan(cents: number): string {
  return `${(cents / 100 / 10000).toFixed(2)} 万元`
}

async function loadProject() {
  const id = route.params.id as string
  if (!id || id === 'new') return
  loading.value = true
  try {
    project.value = await getProject(id)
    editForm.name = project.value.name || ''
    editForm.customer_name = project.value.customer_name || ''
    editForm.target_price_wan = (project.value.target_gross_cents / 100 / 10000).toString()
    editForm.quote_company = project.value.quote_company
  } finally {
    loading.value = false
  }
}

async function handleCreate(data: ProjectCreate) {
  try {
    const created = await createProject(data)
    ElMessage.success('项目创建成功')
    router.push(`/projects/${created.id}`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '创建失败')
  }
}

async function handleUpdate() {
  if (!project.value) return
  try {
    await updateProject(project.value.id, {
      name: editForm.name || null,
      customer_name: editForm.customer_name || null,
      target_price_wan: editForm.target_price_wan,
      quote_company: editForm.quote_company,
    })
    ElMessage.success('更新成功')
    showEdit.value = false
    await loadProject()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '更新失败')
  }
}

async function handleDelete() {
  if (!project.value) return
  try {
    await ElMessageBox.confirm('确定要删除该项目吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(project.value.id)
    ElMessage.success('删除成功')
    router.push('/projects')
  } catch {
    // 取消操作不做处理
  }
}

onMounted(loadProject)
</script>
