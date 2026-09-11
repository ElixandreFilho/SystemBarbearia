<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../services/api'
import { useAuthStore } from '../stores/auth'

interface Service {
  id: string
  name: string
  description: string | null
  price_cents: number
  duration_minutes: number
  is_active: boolean
}

interface BusinessHour {
  id?: string
  weekday: number
  start_time: string
  end_time: string
}

interface DayForm extends BusinessHour {
  label: string
  enabled: boolean
}

const router = useRouter()
const auth = useAuthStore()
const services = ref<Service[]>([])
const days = ref<DayForm[]>([
  { weekday: 0, label: 'Segunda-feira', enabled: false, start_time: '09:00', end_time: '18:00' },
  { weekday: 1, label: 'Terça-feira', enabled: false, start_time: '09:00', end_time: '18:00' },
  { weekday: 2, label: 'Quarta-feira', enabled: false, start_time: '09:00', end_time: '18:00' },
  { weekday: 3, label: 'Quinta-feira', enabled: false, start_time: '09:00', end_time: '18:00' },
  { weekday: 4, label: 'Sexta-feira', enabled: false, start_time: '09:00', end_time: '18:00' },
  { weekday: 5, label: 'Sábado', enabled: false, start_time: '09:00', end_time: '14:00' },
  { weekday: 6, label: 'Domingo', enabled: false, start_time: '09:00', end_time: '14:00' },
])
const form = ref({ id: '', name: '', description: '', price: '', duration: '30' })
const loading = ref(true)
const saving = ref(false)
const savingHours = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const token = () => auth.accessToken ?? undefined

const editing = () => Boolean(form.value.id)

function formatMoney(cents: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100)
}

function resetForm() {
  form.value = { id: '', name: '', description: '', price: '', duration: '30' }
}

function editService(service: Service) {
  form.value = {
    id: service.id,
    name: service.name,
    description: service.description ?? '',
    price: (service.price_cents / 100).toFixed(2).replace('.', ','),
    duration: String(service.duration_minutes),
  }
}

async function loadAdminData() {
  loading.value = true
  try {
    const [serviceData, hourData] = await Promise.all([
      apiRequest<Service[]>('/admin/services', {}, token()),
      apiRequest<BusinessHour[]>('/admin/business-hours', {}, token()),
    ])
    services.value = serviceData
    hourData.forEach((hour) => {
      const day = days.value.find((item) => item.weekday === hour.weekday)
      if (day) {
        day.enabled = true
        day.start_time = hour.start_time.slice(0, 5)
        day.end_time = hour.end_time.slice(0, 5)
      }
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar a área administrativa.'
  } finally {
    loading.value = false
  }
}

async function saveService() {
  const price = Number(form.value.price.replace(',', '.'))
  const duration = Number(form.value.duration)
  if (!form.value.name.trim() || !Number.isFinite(price) || !Number.isFinite(duration)) return
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  const payload = {
    name: form.value.name.trim(),
    description: form.value.description.trim() || undefined,
    price_cents: Math.round(price * 100),
    duration_minutes: duration,
  }
  try {
    const saved = await apiRequest<Service>(form.value.id ? `/admin/services/${form.value.id}` : '/admin/services', {
      method: form.value.id ? 'PATCH' : 'POST',
      body: JSON.stringify(payload),
    }, token())
    if (form.value.id) {
      services.value = services.value.map((service) => service.id === saved.id ? saved : service)
    } else {
      services.value = [...services.value, saved].sort((a, b) => a.name.localeCompare(b.name))
    }
    successMessage.value = form.value.id ? 'Serviço atualizado.' : 'Serviço criado.'
    resetForm()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível salvar o serviço.'
  } finally {
    saving.value = false
  }
}

async function deactivateService(service: Service) {
  if (!window.confirm(`Desativar o serviço “${service.name}”?`)) return
  try {
    await apiRequest<void>(`/admin/services/${service.id}`, { method: 'DELETE' }, token())
    service.is_active = false
    successMessage.value = 'Serviço desativado.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível desativar o serviço.'
  }
}

async function saveBusinessHours() {
  savingHours.value = true
  errorMessage.value = ''
  try {
    const payload = days.value.filter((day) => day.enabled).map(({ weekday, start_time, end_time }) => ({
      weekday,
      start_time: `${start_time}:00`,
      end_time: `${end_time}:00`,
    }))
    await apiRequest<BusinessHour[]>('/admin/business-hours', { method: 'PUT', body: JSON.stringify(payload) }, token())
    successMessage.value = 'Horários de funcionamento atualizados.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível salvar os horários.'
  } finally {
    savingHours.value = false
  }
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}

onMounted(loadAdminData)
</script>

<template>
  <main class="admin-content">
    <v-container class="admin-container">
      <header class="admin-intro">
        <div>
          <p class="section-kicker">Painel administrativo</p>
          <h1>Gestão da barbearia.</h1>
          <p>Configure o catálogo e os horários de atendimento.</p>
        </div>
        <v-btn class="logout-button" variant="text" @click="logout">Sair</v-btn>
      </header>

      <v-alert v-if="errorMessage" type="error" variant="tonal" closable @click:close="errorMessage = ''">{{ errorMessage }}</v-alert>
      <v-alert v-if="successMessage" type="success" variant="tonal" closable @click:close="successMessage = ''">{{ successMessage }}</v-alert>
      <v-progress-linear v-if="loading" indeterminate color="steel-blue" class="loading-line" />

      <v-row v-else class="admin-grid">
        <v-col cols="12" lg="7">
          <section class="admin-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Catálogo</p>
                <h2>Serviços</h2>
              </div>
              <v-btn variant="outlined" color="slate" @click="resetForm">Novo serviço</v-btn>
            </div>
            <div v-if="!services.length" class="empty-state">Nenhum serviço cadastrado.</div>
            <div v-for="service in services" :key="service.id" class="service-row" :class="{ 'service-row--inactive': !service.is_active }">
              <div>
                <strong>{{ service.name }}</strong>
                <span>{{ service.duration_minutes }} min · {{ formatMoney(service.price_cents) }}</span>
              </div>
              <div class="row-actions">
                <v-chip size="small" variant="outlined">{{ service.is_active ? 'Ativo' : 'Inativo' }}</v-chip>
                <v-btn variant="text" size="small" @click="editService(service)">Editar</v-btn>
                <v-btn v-if="service.is_active" variant="text" size="small" @click="deactivateService(service)">Desativar</v-btn>
              </div>
            </div>
          </section>

          <section class="admin-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Agenda</p>
                <h2>Horários de funcionamento</h2>
              </div>
            </div>
            <div v-for="day in days" :key="day.weekday" class="day-row">
              <v-checkbox v-model="day.enabled" :label="day.label" hide-details color="steel-blue" />
              <v-text-field v-model="day.start_time" type="time" variant="outlined" density="compact" hide-details :disabled="!day.enabled" />
              <span class="day-separator">até</span>
              <v-text-field v-model="day.end_time" type="time" variant="outlined" density="compact" hide-details :disabled="!day.enabled" />
            </div>
            <v-btn class="save-button" :loading="savingHours" @click="saveBusinessHours">Salvar horários</v-btn>
          </section>
        </v-col>

        <v-col cols="12" lg="5">
          <section class="form-panel">
            <p class="section-kicker">{{ editing() ? 'Editar serviço' : 'Novo serviço' }}</p>
            <h2>{{ editing() ? 'Atualizar serviço' : 'Cadastrar serviço' }}</h2>
            <v-text-field v-model="form.name" label="Nome do serviço" variant="outlined" />
            <v-textarea v-model="form.description" label="Descrição" rows="3" variant="outlined" />
            <v-row>
              <v-col cols="7"><v-text-field v-model="form.price" label="Preço (R$)" placeholder="35,00" variant="outlined" /></v-col>
              <v-col cols="5"><v-text-field v-model="form.duration" label="Minutos" type="number" variant="outlined" /></v-col>
            </v-row>
            <v-btn class="save-button" block :loading="saving" @click="saveService">
              {{ editing() ? 'Salvar alterações' : 'Cadastrar serviço' }}
            </v-btn>
          </section>
        </v-col>
      </v-row>
    </v-container>
  </main>
</template>

<style scoped>
.admin-content { min-height: calc(100dvh - 64px); background: var(--paper); padding: 40px 20px 72px; }
.admin-container { max-width: 1180px; }
.admin-intro, .section-heading, .service-row, .day-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.admin-intro { align-items: flex-start; margin-bottom: 32px; }
.admin-intro h1, .section-heading h2, .form-panel h2 { margin: 0; color: var(--ink); font-family: 'Instrument Serif', serif; font-weight: 400; }
.admin-intro h1 { font-size: clamp(2.3rem, 5vw, 3.5rem); line-height: 1; }
.admin-intro p:not(.section-kicker) { margin: 12px 0 0; color: var(--slate); }
.section-kicker { margin: 0 0 8px; color: var(--steel-blue); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.section-heading h2, .form-panel h2 { font-size: 2rem; line-height: 1.05; }
.admin-section, .form-panel { border: 1px solid var(--hairline); padding: 24px; background: rgba(255, 255, 255, 0.3); }
.form-panel { position: sticky; top: 88px; background: var(--navy-deep); }
.form-panel h2 { margin-bottom: 24px; color: var(--paper); }
.form-panel :deep(.v-label), .form-panel :deep(input), .form-panel :deep(textarea) { color: var(--paper); }
.form-panel :deep(.v-field__outline) { color: rgba(244, 246, 249, 0.4); }
.admin-section + .admin-section { margin-top: 24px; }
.loading-line { margin: 24px 0; }
.service-row, .day-row { padding: 16px 0; border-bottom: 1px solid var(--hairline); }
.service-row:last-child { border-bottom: 0; }
.service-row strong, .service-row span { display: block; }
.service-row span { margin-top: 5px; color: var(--slate); font-size: 0.82rem; }
.service-row--inactive { opacity: 0.58; }
.row-actions { display: flex; align-items: center; gap: 4px; }
.row-actions :deep(.v-chip) { border-radius: 4px; }
.day-row :deep(.v-checkbox) { min-width: 190px; }
.day-row :deep(.v-input) { max-width: 140px; }
.day-separator { color: var(--slate); font-size: 0.8rem; }
.save-button { min-height: 46px; margin-top: 20px; border-radius: 4px !important; background: var(--steel-blue) !important; color: var(--paper) !important; text-transform: none; }
.logout-button { color: var(--steel-blue); text-transform: none; }
.empty-state { padding: 32px 0; color: var(--slate); }
@media (max-width: 960px) { .form-panel { position: static; } }
@media (max-width: 600px) { .admin-content { padding: 28px 12px 56px; } .admin-section, .form-panel { padding: 18px; } .service-row { align-items: flex-start; flex-direction: column; } .row-actions { width: 100%; justify-content: flex-end; } .day-row { flex-wrap: wrap; } .day-row :deep(.v-checkbox) { min-width: 100%; } .day-row :deep(.v-input) { flex: 1; } }
</style>
