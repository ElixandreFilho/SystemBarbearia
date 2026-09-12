<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const identifier = ref('')
const password = ref('')
const showPassword = ref(false)
const errorMessage = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    await auth.login({ identifier: identifier.value, password: password.value })
    await router.push(auth.user?.role === 'ADMIN' ? '/admin' : '/dashboard')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'Não foi possível entrar'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page login-page">
    <v-card class="login-card" elevation="8">
      <div class="login-brand">
        <div class="login-est"></div>
        <v-icon icon="mdi-content-cut" class="login-scissors" aria-hidden="true" />
        <div class="login-est">BARBER SHOP</div>
        <h1>CORTES</h1>
        <p>Acesse sua conta</p>
      </div>

      <v-card-text class="login-form-wrap">
        <v-alert v-if="errorMessage" type="error" variant="tonal" class="login-error">
          {{ errorMessage }}
        </v-alert>

        <v-form @submit.prevent="submit">
          <v-text-field
            v-model="identifier"
            label="E-mail ou Usuário"
            prepend-inner-icon="mdi-email"
            variant="outlined"
            autocomplete="username"
            class="login-field"
            required
          />

          <v-text-field
            v-model="password"
            label="Senha"
            prepend-inner-icon="mdi-lock"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            :type="showPassword ? 'text' : 'password'"
            variant="outlined"
            autocomplete="current-password"
            class="login-field"
            required
            @click:append-inner="showPassword = !showPassword"
          />

          <v-btn type="submit" block class="login-submit" :loading="loading">
            Entrar
          </v-btn>
        </v-form>

        <div class="login-links">
          <v-btn variant="text" class="forgot-link" to="/recuperar-senha">
            Esqueceu sua senha?
          </v-btn>
          <v-btn variant="text" class="register-link" to="/cadastro">
            Criar nova conta
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  min-height: 100dvh;
  place-items: center;
  padding: 24px 16px;
  background-color: #0a0d12 !important;
  background-image:
    linear-gradient(135deg, rgba(10, 13, 18, 0.92), rgba(15, 27, 46, 0.9)),
    url('https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=1800&q=80');
  background-position: center;
  background-size: cover;
}

.login-card {
  width: min(100%, 400px);
  border: 1px solid rgba(93, 138, 196, 0.2) !important;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28) !important;
}

.login-brand {
  padding: 32px 24px 8px;
  color: #0a0d12;
  text-align: center;
}

.login-est {
  color: #8b96a8;
  font-family: 'Manrope', sans-serif;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.18em;
}

.login-scissors {
  display: block;
  width: 48px;
  height: 48px;
  margin: 10px auto;
  color: #1f3b63;
  font-size: 28px;
}

.login-brand h1 {
  margin: 8px 0 0;
  color: #0f1b2e;
  font-family: 'Manrope', sans-serif;
  font-size: clamp(2rem, 10vw, 2.8rem);
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: 1;
}

.login-brand p {
  margin: 12px 0 0;
  color: #8b96a8;
  font-family: 'Manrope', sans-serif;
  font-size: 0.9rem;
}

.login-form-wrap {
  padding: 24px;
}

.login-field {
  margin-bottom: 16px;
}

.login-field :deep(.v-field) {
  min-height: 52px;
  border-radius: 8px;
  background: #ffffff;
}

.login-field :deep(.v-field--focused) {
  box-shadow: 0 0 0 3px rgba(93, 138, 196, 0.15);
}

.login-submit {
  min-height: 48px;
  margin-top: 4px;
  border-radius: 8px !important;
  background: #0f1b2e !important;
  color: #ffffff !important;
  font-family: 'Manrope', sans-serif;
  font-weight: 600;
  text-transform: none;
  transition: transform 120ms ease, background-color 180ms ease;
}

.login-submit:hover {
  background: #1f3b63 !important;
}

.login-submit:active {
  transform: scale(0.97);
}

.login-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  margin-top: 18px;
}

.login-links .v-btn {
  min-height: 44px;
  padding-inline: 4px;
  font-family: 'Manrope', sans-serif;
  font-size: 0.78rem;
  text-transform: none;
}

.forgot-link {
  color: #0a0d12;
}

.register-link {
  color: #5d8ac4;
}

.login-error {
  margin-bottom: 16px;
}

@media (max-width: 420px) {
  .login-page {
    align-items: start;
    padding: 16px;
  }

  .login-card {
    width: 100%;
  }

  .login-brand {
    padding-top: 26px;
  }

  .login-form-wrap {
    padding: 20px;
  }

  .login-links {
    justify-content: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-submit {
    transition: none;
  }
}
</style>
