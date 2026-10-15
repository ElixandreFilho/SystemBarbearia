<script setup lang="ts">
import { computed } from "vue";

import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const userInitial = computed(
  () => auth.user?.full_name?.trim().charAt(0).toUpperCase() || "B",
);
</script>

<template>
  <v-app>
    <v-app-bar class="global-app-bar">
      <v-app-bar-title class="global-brand"
        ><span class="global-brand-mark">✂</span
        ><span>Barber<span>Shop</span></span></v-app-bar-title
      >
      <div v-if="auth.user" class="global-search">
        <v-icon icon="mdi-magnify" size="18" /><span
          >Buscar por cliente, serviço ou horário...</span
        >
      </div>
      <v-spacer />
      <div v-if="auth.user" class="global-user" :title="auth.user.full_name">
        <span class="global-user-name">{{ auth.user.full_name }}</span>
        <span class="global-user-avatar" aria-hidden="true">{{
          userInitial
        }}</span>
      </div>
    </v-app-bar>
    <v-main><router-view /></v-main>
  </v-app>
</template>
