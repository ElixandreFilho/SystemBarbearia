<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const fullName = ref('')
const email = ref('')
const phone = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    await auth.register({
      full_name: fullName.value,
      email: email.value || undefined,
      phone: phone.value || undefined,
      password: password.value,
    })
    await router.push('/dashboard')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível criar sua conta'
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
          <v-card-title>Criar conta</v-card-title>
          <v-card-subtitle>Informe e-mail ou telefone</v-card-subtitle>
        </v-card-item>
        <v-card-text>
          <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
          <v-form @submit.prevent="submit">
            <v-text-field v-model="fullName" label="Nome completo" autocomplete="name" required />
            <v-text-field v-model="email" label="E-mail" type="email" autocomplete="email" />
            <v-text-field v-model="phone" label="Telefone" autocomplete="tel" />
            <v-text-field v-model="password" label="Senha" type="password" autocomplete="new-password" hint="Mínimo de 8 caracteres" persistent-hint required />
            <v-btn block type="submit" :loading="loading">Criar conta</v-btn>
          </v-form>
          <div class="auth-link-row">
            <router-link to="/login">Já tenho uma conta</router-link>
          </div>
        </v-card-text>
      </v-card>
    </section>
  </main>
</template>
