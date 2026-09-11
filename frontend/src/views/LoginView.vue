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
const showPassword = ref(false)

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
  <main class="auth-page">
    <v-card class="auth-card">
        <v-card-item>
          <div class="auth-brand-icon" aria-hidden="true">
            <v-icon icon="mdi-content-cut" />
          </div>
          <v-card-title>Entrar</v-card-title>
          <v-card-subtitle>Acesse sua conta da barbearia</v-card-subtitle>
        </v-card-item>
        <v-card-text>
          <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
          <v-form @submit.prevent="submit">
            <v-text-field
              v-model="identifier"
              class="auth-input"
              label="E-mail ou telefone"
              prepend-inner-icon="mdi-account-outline"
              autocomplete="username"
              required
            />
            <v-text-field
              v-model="password"
              class="auth-input"
              label="Senha"
              :type="showPassword ? 'text' : 'password'"
              prepend-inner-icon="mdi-lock-outline"
              autocomplete="current-password"
              required
            >
              <template #append-inner>
                <v-fade-transition mode="out-in">
                  <v-icon
                    :key="showPassword ? 'visible' : 'hidden'"
                    class="password-toggle"
                    :icon="showPassword ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
                    role="button"
                    tabindex="0"
                    :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                    @click="showPassword = !showPassword"
                    @keydown.enter="showPassword = !showPassword"
                  />
                </v-fade-transition>
              </template>
            </v-text-field>
            <v-btn block type="submit" :loading="loading">Entrar</v-btn>
          </v-form>
          <div class="auth-link-row">
            <router-link to="/cadastro">Ainda não tenho cadastro</router-link>
          </div>
        </v-card-text>
    </v-card>
  </main>
</template>
