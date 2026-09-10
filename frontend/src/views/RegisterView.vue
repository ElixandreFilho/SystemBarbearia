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
  <v-container class="fill-height py-10">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card rounded="lg" elevation="4">
          <v-card-item>
            <v-card-title>Criar conta</v-card-title>
            <v-card-subtitle>Informe e-mail ou telefone</v-card-subtitle>
          </v-card-item>
          <v-card-text>
            <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">{{ errorMessage }}</v-alert>
            <v-form @submit.prevent="submit">
              <v-text-field v-model="fullName" label="Nome completo" autocomplete="name" required />
              <v-text-field v-model="email" label="E-mail" type="email" autocomplete="email" />
              <v-text-field v-model="phone" label="Telefone" autocomplete="tel" />
              <v-text-field v-model="password" label="Senha" type="password" autocomplete="new-password" hint="Mínimo de 8 caracteres" persistent-hint required />
              <v-btn block color="primary" type="submit" class="mt-4" :loading="loading">Criar conta</v-btn>
            </v-form>
            <div class="text-center mt-5">
              <router-link to="/login">Já tenho uma conta</router-link>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
