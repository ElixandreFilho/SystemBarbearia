import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource/instrument-serif/400.css'
import '@fontsource/manrope/400.css'
import '@fontsource/manrope/500.css'
import '@fontsource/manrope/600.css'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import App from './App.vue'
import router from './router'
import './styles/main.css'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'barbearia',
    themes: {
      barbearia: {
        colors: {
          ink: '#0A0D12',
          'navy-deep': '#0F1B2E',
          navy: '#1F3B63',
          'steel-blue': '#5D8AC4',
          paper: '#F4F6F9',
          slate: '#8B96A8',
          primary: '#5D8AC4',
          secondary: '#8B96A8',
          background: '#F4F6F9',
          surface: '#F4F6F9',
        },
      },
    },
  },
  defaults: {
    VAppBar: {
      elevation: 0,
    },
    VBtn: {
      rounded: 'sm',
      elevation: 0,
    },
    VCard: {
      rounded: '0',
      elevation: 0,
    },
    VTextField: {
      variant: 'underlined',
      density: 'comfortable',
      hideDetails: 'auto',
    },
  },
})

createApp(App).use(createPinia()).use(vuetify).use(router).mount('#app')
