import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import App from './App.vue'
import router from './router'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'barbearia',
    themes: {
      barbearia: {
        colors: {
          primary: '#5D4037',
          secondary: '#D7A86E',
          background: '#FAF7F2',
        },
      },
    },
  },
})

createApp(App).use(createPinia()).use(vuetify).use(router).mount('#app')
