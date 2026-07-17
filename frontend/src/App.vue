<template>
  <el-config-provider>
    <el-container style="min-height: 100vh">
      <el-header style="background: #409eff; display: flex; align-items: center">
        <h1 style="color: #fff; font-size: 18px; margin: 0; cursor: pointer" @click="router.push('/projects')">
          售前知识 Agent
        </h1>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>