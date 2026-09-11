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
  <main class="auth-shell">
    <section class="auth-brand-panel" aria-label="Identidade da barbearia">
      <div class="auth-brand-content">
        <div class="auth-brand-mark" aria-hidden="true"></div>
        <h1 class="auth-brand-title">Sistema<br />Barbearia</h1>
        <p class="auth-brand-copy">Seu horário, no seu ritmo. Uma experiência simples para cuidar do seu estilo.</p>
      </div>
    </section>

    <section class="auth-form-panel">
      <v-card class="auth-form-card">
        <v-card-item>
          <v-card-title>Entrar</v-card-title>
          <v-card-subtitle>Acesse sua conta da barbearia</v-card-subtitle>
        </v-card-item>
        <v-card-text>
          <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
          <v-form @submit.prevent="submit">
            <v-text-field v-model="identifier" label="E-mail ou telefone" autocomplete="username" required />
            <v-text-field v-model="password" label="Senha" type="password" autocomplete="current-password" required />
            <v-btn block type="submit" :loading="loading">Entrar</v-btn>
          </v-form>
          <div class="auth-link-row">
            <router-link to="/cadastro">Ainda não tenho cadastro</router-link>
          </div>
        </v-card-text>
      </v-card>
    </section>
  </main>
</template>
