<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, apiRequest } from '../services/api'

const route = useRoute()
const router = useRouter()
const password = ref('')
const confirmation = ref('')
const errorMessage = ref('')
const loading = ref(false)
const token = computed(() => String(route.query.token ?? ''))

async function submit() {
  errorMessage.value = ''
  if (!token.value) {
    errorMessage.value = 'Link de recuperação inválido.'
    return
  }
  if (password.value !== confirmation.value) {
    errorMessage.value = 'As senhas não coincidem.'
    return
  }
  loading.value = true
  try {
    await apiRequest('/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify({ token: token.value, password: password.value }),
    })
    await router.push('/login')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível redefinir a senha.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <v-card class="auth-card" elevation="0">
      <v-card-item>
        <div class="auth-brand-icon"><v-icon icon="mdi-lock-check-outline" aria-hidden="true" /></div>
        <v-card-title>Nova senha</v-card-title>
        <v-card-subtitle>Escolha uma senha segura para sua conta</v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field v-model="password" label="Nova senha" type="password" prepend-inner-icon="mdi-lock-outline" autocomplete="new-password" variant="outlined" class="auth-input" hint="Mínimo de 8 caracteres" persistent-hint required />
          <v-text-field v-model="confirmation" label="Confirmar senha" type="password" prepend-inner-icon="mdi-lock-outline" autocomplete="new-password" variant="outlined" class="auth-input" required />
          <v-btn type="submit" block :loading="loading">Salvar nova senha</v-btn>
        </v-form>
        <div class="auth-link-row"><router-link to="/login">Voltar para o login</router-link></div>
      </v-card-text>
    </v-card>
  </main>
</template>
