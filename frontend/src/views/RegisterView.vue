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
const showPassword = ref(false)

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
    await router.push(auth.user?.role === 'ADMIN' ? '/admin' : '/dashboard')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível criar sua conta'
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
          <v-card-title>Criar conta</v-card-title>
          <v-card-subtitle>Informe e-mail ou telefone</v-card-subtitle>
        </v-card-item>
        <v-card-text>
          <v-alert v-if="errorMessage" type="error" variant="tonal">{{ errorMessage }}</v-alert>
          <v-form @submit.prevent="submit">
            <v-text-field v-model="fullName" class="auth-input" label="Nome completo" prepend-inner-icon="mdi-account-outline" autocomplete="name" required />
            <v-text-field v-model="email" class="auth-input" label="E-mail" prepend-inner-icon="mdi-email-outline" type="email" autocomplete="email" />
            <v-text-field v-model="phone" class="auth-input" label="Telefone" prepend-inner-icon="mdi-phone-outline" autocomplete="tel" />
            <v-text-field
              v-model="password"
              class="auth-input"
              label="Senha"
              :type="showPassword ? 'text' : 'password'"
              prepend-inner-icon="mdi-lock-outline"
              autocomplete="new-password"
              hint="Mínimo de 8 caracteres"
              persistent-hint
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
            <v-btn block type="submit" :loading="loading">Criar conta</v-btn>
          </v-form>
          <div class="auth-link-row">
            <router-link to="/login">Já tenho uma conta</router-link>
          </div>
        </v-card-text>
    </v-card>
  </main>
</template>
