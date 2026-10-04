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
import './styles/design-tokens.css'
import './styles/main.css'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'barbearia',
    themes: {
      barbearia: {
        colors: {
          ink: 'rgb(var(--color-ink-rgb))',
          'navy-deep': 'rgb(var(--color-navy-deep-rgb))',
          navy: 'rgb(var(--color-navy-rgb))',
          'steel-blue': 'rgb(var(--color-steel-blue-rgb))',
          paper: 'rgb(var(--color-paper-rgb))',
          slate: 'rgb(var(--color-slate-rgb))',
          primary: 'rgb(var(--color-steel-blue-rgb))',
          secondary: 'rgb(var(--color-slate-rgb))',
          background: 'rgb(var(--color-paper-rgb))',
          surface: 'rgb(var(--color-paper-rgb))',
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
