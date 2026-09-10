<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <v-container class="py-10">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card rounded="lg" elevation="4">
          <v-card-item>
            <v-card-title>Olá, {{ auth.user?.full_name }}!</v-card-title>
            <v-card-subtitle>Área inicial do cliente</v-card-subtitle>
          </v-card-item>
          <v-card-text>
            <p class="text-body-1 mb-4">A autenticação está funcionando. O catálogo e os agendamentos serão adicionados nas próximas fases.</p>
            <v-chip color="success" variant="tonal">Sessão ativa</v-chip>
            <v-btn variant="text" color="primary" class="ml-2" @click="logout">Sair</v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
