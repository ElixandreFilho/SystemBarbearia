<script setup lang="ts">
import { computed } from 'vue'

import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const userInitial = computed(() => auth.user?.full_name?.trim().charAt(0).toUpperCase() || 'B')
</script>

<template>
  <v-app>
    <v-app-bar class="global-app-bar">
      <v-app-bar-title>Sistema Barbearia</v-app-bar-title>
      <v-spacer />
      <div v-if="auth.user" class="global-user" :title="auth.user.full_name">
        <span class="global-user-name">{{ auth.user.full_name }}</span>
        <span class="global-user-avatar" aria-hidden="true">{{ userInitial }}</span>
      </div>
    </v-app-bar>
    <v-main><router-view /></v-main>
  </v-app>
</template>
