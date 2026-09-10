<script setup lang="ts">
import { ref } from 'vue'

const apiStatus = ref('Verificando API...')

async function checkApi() {
  try {
    const response = await fetch('http://localhost:8000/health')
    apiStatus.value = response.ok ? 'API conectada' : 'API indisponível'
  } catch {
    apiStatus.value = 'API indisponível'
  }
}

checkApi()
</script>

<template>
  <v-app>
    <v-app-bar color="primary" elevation="2">
      <v-app-bar-title>Sistema Barbearia</v-app-bar-title>
    </v-app-bar>

    <v-main>
      <v-container class="py-10">
        <v-row justify="center">
          <v-col cols="12" md="8" lg="6">
            <v-card rounded="lg" elevation="4">
              <v-card-item>
                <v-card-title>Fundação pronta</v-card-title>
                <v-card-subtitle>Fase 0 · Frontend Vue + Vuetify</v-card-subtitle>
              </v-card-item>
              <v-card-text>
                <p class="text-body-1 mb-4">
                  A base do sistema está configurada para evoluir conforme a especificação.
                </p>
                <v-chip :color="apiStatus === 'API conectada' ? 'success' : 'warning'" variant="tonal">
                  {{ apiStatus }}
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>
