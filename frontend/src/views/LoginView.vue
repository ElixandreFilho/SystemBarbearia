<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const identifier = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    await auth.login({ identifier: identifier.value, password: password.value })
    await router.push('/dashboard')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível entrar'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-container class="fill-height py-10">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card rounded="lg" elevation="4">
          <v-card-item>
            <v-card-title>Entrar</v-card-title>
            <v-card-subtitle>Acesse sua conta da barbearia</v-card-subtitle>
          </v-card-item>
          <v-card-text>
            <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">{{ errorMessage }}</v-alert>
            <v-form @submit.prevent="submit">
              <v-text-field v-model="identifier" label="E-mail ou telefone" autocomplete="username" required />
              <v-text-field v-model="password" label="Senha" type="password" autocomplete="current-password" required />
              <v-btn block color="primary" type="submit" :loading="loading">Entrar</v-btn>
            </v-form>
            <div class="text-center mt-5">
              <router-link to="/cadastro">Ainda não tenho cadastro</router-link>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
