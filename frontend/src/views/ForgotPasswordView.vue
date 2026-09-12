<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, apiRequest } from '../services/api'

const router = useRouter()
const email = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await apiRequest<{ message: string }>('/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify({ email: email.value }),
    })
    successMessage.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível solicitar a recuperação.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <v-card class="auth-card" elevation="0">
      <v-card-item>
        <div class="auth-brand-icon"><v-icon icon="mdi-lock-reset" aria-hidden="true" /></div>
        <v-card-title>Recuperar senha</v-card-title>
        <v-card-subtitle>Enviaremos as instruções para seu e-mail</v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
        <v-alert v-if="successMessage" type="success" variant="tonal">{{ successMessage }}</v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field v-model="email" label="E-mail" type="email" prepend-inner-icon="mdi-email-outline" autocomplete="email" variant="outlined" class="auth-input" required />
          <v-btn type="submit" block :loading="loading">Enviar instruções</v-btn>
        </v-form>
        <div class="auth-link-row"><router-link to="/login">Voltar para o login</router-link></div>
      </v-card-text>
    </v-card>
  </main>
</template>
