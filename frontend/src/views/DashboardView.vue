<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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

interface Appointment {
  id: string
  date: string
  start_time: string
  end_time: string
  status: string
  total_price_cents: number
  total_duration_minutes: number
  notes: string | null
  service_ids: string[]
}

interface AvailabilityResponse {
  date: string
  duration_minutes: number
  slots: string[]
}

const router = useRouter()
const auth = useAuthStore()
const services = ref<Service[]>([])
const appointments = ref<Appointment[]>([])
const selectedServiceIds = ref<string[]>([])
const bookingDate = ref(formatDate(new Date()))
const selectedSlot = ref('')
const notes = ref('')
const availableSlots = ref<string[]>([])
const loading = ref(true)
const loadingSlots = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const editingAppointment = ref<Appointment | null>(null)
const editServiceIds = ref<string[]>([])
const editNotes = ref('')
const savingEdit = ref(false)

const minDate = formatDate(new Date())
const maxDate = formatDate(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000))
const token = () => auth.accessToken ?? undefined

const selectedServices = computed(() => services.value.filter((service) => selectedServiceIds.value.includes(service.id)))
const totalPrice = computed(() => selectedServices.value.reduce((total, service) => total + service.price_cents, 0))
const totalDuration = computed(() => selectedServices.value.reduce((total, service) => total + service.duration_minutes, 0))
const editServices = computed(() => services.value.filter((service) => editServiceIds.value.includes(service.id)))
const editTotalPrice = computed(() => editServices.value.reduce((total, service) => total + service.price_cents, 0))
const editTotalDuration = computed(() => editServices.value.reduce((total, service) => total + service.duration_minutes, 0))

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10)
}

function formatMoney(cents: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100)
}

function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`))
}

function formatTime(value: string) {
  return value.slice(0, 5)
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING: 'Pendente',
    CONFIRMED: 'Confirmado',
    COMPLETED: 'Concluído',
    CANCELLED: 'Cancelado',
    NO_SHOW: 'Não compareceu',
  }
  return labels[status] ?? status
}

function statusColor(status: string) {
  return status === 'CANCELLED' || status === 'NO_SHOW' ? 'slate' : 'steel-blue'
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [serviceData, appointmentData] = await Promise.all([
      apiRequest<Service[]>('/services', {}, token()),
      apiRequest<Appointment[]>('/appointments/me', {}, token()),
    ])
    services.value = serviceData
    appointments.value = appointmentData
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar seus dados.'
  } finally {
    loading.value = false
  }
}

async function loadAvailability() {
  selectedSlot.value = ''
  availableSlots.value = []
  if (!selectedServiceIds.value.length || !bookingDate.value) return

  loadingSlots.value = true
  try {
    const query = new URLSearchParams({ date: bookingDate.value })
    selectedServiceIds.value.forEach((id) => query.append('service_ids', id))
    const data = await apiRequest<AvailabilityResponse>(`/availability?${query.toString()}`, {}, token())
    availableSlots.value = data.slots
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível consultar os horários.'
  } finally {
    loadingSlots.value = false
  }
}

async function createAppointment() {
  if (!selectedSlot.value || !selectedServiceIds.value.length) return
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const appointment = await apiRequest<Appointment>('/appointments', {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({
        date: bookingDate.value,
        start_time: selectedSlot.value,
        service_ids: selectedServiceIds.value,
        notes: notes.value.trim() || undefined,
      }),
    }, token())
    appointments.value = [appointment, ...appointments.value]
    successMessage.value = 'Agendamento confirmado com sucesso.'
    selectedSlot.value = ''
    notes.value = ''
    await loadAvailability()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível criar o agendamento.'
  } finally {
    submitting.value = false
  }
}

async function cancelAppointment(appointment: Appointment) {
  if (!window.confirm('Deseja realmente cancelar este agendamento?')) return
  try {
    await apiRequest<void>(`/appointments/${appointment.id}`, { method: 'DELETE' }, token())
    appointment.status = 'CANCELLED'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível cancelar o agendamento.'
  }
}

function openEdit(appointment: Appointment) {
  editingAppointment.value = appointment
  editServiceIds.value = [...appointment.service_ids]
  editNotes.value = appointment.notes ?? ''
}

async function updateAppointment() {
  if (!editingAppointment.value || !editServiceIds.value.length) return
  savingEdit.value = true
  errorMessage.value = ''
  try {
    const updated = await apiRequest<Appointment>(`/appointments/${editingAppointment.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ service_ids: editServiceIds.value, notes: editNotes.value.trim() || undefined }),
    }, token())
    appointments.value = appointments.value.map((item) => item.id === updated.id ? updated : item)
    successMessage.value = 'Agendamento atualizado com sucesso.'
    editingAppointment.value = null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível atualizar o agendamento.'
  } finally {
    savingEdit.value = false
  }
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}

watch([selectedServiceIds, bookingDate], loadAvailability)
onMounted(loadDashboard)
</script>

<template>
  <main class="dashboard-content">
    <v-container class="dashboard-container">
      <header class="dashboard-intro">
        <div>
          <p class="section-kicker">Área do cliente</p>
          <h1>Olá, {{ auth.user?.full_name }}.</h1>
          <p>Escolha seu próximo horário na barbearia.</p>
        </div>
        <v-btn class="logout-button" variant="text" @click="logout">Sair</v-btn>
      </header>

      <v-alert v-if="errorMessage" type="error" variant="tonal" closable @click:close="errorMessage = ''">
        {{ errorMessage }}
      </v-alert>
      <v-alert v-if="successMessage" type="success" variant="tonal" closable @click:close="successMessage = ''">
        {{ successMessage }}
      </v-alert>

      <v-row class="dashboard-grid">
        <v-col cols="12" lg="7">
          <section class="dashboard-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Catálogo</p>
                <h2>Escolha seus serviços</h2>
              </div>
              <span v-if="selectedServices.length" class="selection-count">{{ selectedServices.length }} selecionado(s)</span>
            </div>

            <v-progress-linear v-if="loading" indeterminate color="steel-blue" class="loading-line" />
            <div v-else-if="!services.length" class="empty-state">
              <v-icon icon="mdi-content-cut" size="28" />
              <p>O catálogo ainda não possui serviços cadastrados.</p>
            </div>
            <v-row v-else>
              <v-col v-for="service in services" :key="service.id" cols="12" sm="6">
                <button
                  class="service-card"
                  :class="{ 'service-card--selected': selectedServiceIds.includes(service.id) }"
                  type="button"
                  @click="selectedServiceIds = selectedServiceIds.includes(service.id)
                    ? selectedServiceIds.filter((id) => id !== service.id)
                    : [...selectedServiceIds, service.id]"
                >
                  <span class="service-check">
                    <v-icon :icon="selectedServiceIds.includes(service.id) ? 'mdi-check' : 'mdi-plus'" size="18" />
                  </span>
                  <span class="service-content">
                    <strong>{{ service.name }}</strong>
                    <small>{{ service.description || 'Atendimento personalizado na barbearia.' }}</small>
                    <span class="service-meta">
                      <span>{{ service.duration_minutes }} min</span>
                      <b>{{ formatMoney(service.price_cents) }}</b>
                    </span>
                  </span>
                </button>
              </v-col>
            </v-row>
          </section>

          <section class="dashboard-section appointments-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Histórico</p>
                <h2>Meus agendamentos</h2>
              </div>
            </div>
            <div v-if="!appointments.length && !loading" class="empty-state empty-state--compact">
              <p>Você ainda não possui agendamentos.</p>
            </div>
            <div v-for="appointment in appointments" :key="appointment.id" class="appointment-row">
              <div>
                <strong>{{ formatDateLabel(appointment.date) }} · {{ formatTime(appointment.start_time) }}</strong>
                <span>{{ appointment.total_duration_minutes }} min · {{ formatMoney(appointment.total_price_cents) }}</span>
              </div>
              <div class="appointment-actions">
                <v-chip size="small" :color="statusColor(appointment.status)" variant="outlined">
                  {{ statusLabel(appointment.status) }}
                </v-chip>
                <v-btn
                  v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)"
                  class="edit-button"
                  variant="text"
                  size="small"
                  @click="openEdit(appointment)"
                >
                  Editar
                </v-btn>
                <v-btn
                  v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)"
                  class="cancel-button"
                  variant="text"
                  size="small"
                  @click="cancelAppointment(appointment)"
                >
                  Cancelar
                </v-btn>
              </div>
            </div>
          </section>
        </v-col>

        <v-col cols="12" lg="5">
          <section class="booking-panel">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Novo horário</p>
                <h2>Agende seu atendimento</h2>
              </div>
            </div>

            <div v-if="!selectedServices.length" class="booking-hint">
              <v-icon icon="mdi-arrow-left" size="18" />
              <span>Selecione ao menos um serviço para continuar.</span>
            </div>
            <template v-else>
              <div class="booking-summary">
                <span>{{ totalDuration }} minutos</span>
                <strong>{{ formatMoney(totalPrice) }}</strong>
              </div>
              <v-text-field
                v-model="bookingDate"
                class="dashboard-input"
                label="Data do atendimento"
                type="date"
                :min="minDate"
                :max="maxDate"
                variant="outlined"
              />
              <div class="slot-heading">
                <span>Horários disponíveis</span>
                <v-progress-circular v-if="loadingSlots" indeterminate size="16" width="2" color="steel-blue" />
              </div>
              <div v-if="!loadingSlots && !availableSlots.length" class="empty-slots">
                Nenhum horário disponível para esta data.
              </div>
              <div v-else class="slot-grid">
                <v-btn
                  v-for="slot in availableSlots"
                  :key="slot"
                  class="slot-button"
                  :class="{ 'slot-button--selected': selectedSlot === slot }"
                  variant="outlined"
                  @click="selectedSlot = slot"
                >
                  {{ formatTime(slot) }}
                </v-btn>
              </div>
              <v-textarea
                v-model="notes"
                class="dashboard-input"
                label="Observações (opcional)"
                rows="3"
                variant="outlined"
              />
              <v-btn class="book-button" block :disabled="!selectedSlot" :loading="submitting" @click="createAppointment">
                Confirmar agendamento
              </v-btn>
            </template>
          </section>
        </v-col>
      </v-row>
    </v-container>

    <v-dialog v-model="editingAppointment" max-width="520">
      <v-card class="edit-dialog">
        <v-card-title>Atualizar agendamento</v-card-title>
        <v-card-text>
          <p class="edit-dialog-intro">O horário permanece {{ editingAppointment ? formatTime(editingAppointment.start_time) : '' }}. Escolha os serviços desejados.</p>
          <v-select v-model="editServiceIds" label="Serviços" :items="services" item-title="name" item-value="id" multiple chips variant="outlined" />
          <div class="edit-summary">
            <span>{{ editTotalDuration }} minutos</span>
            <strong>{{ formatMoney(editTotalPrice) }}</strong>
          </div>
          <v-textarea v-model="editNotes" label="Observações (opcional)" rows="3" variant="outlined" />
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="editingAppointment = null">Voltar</v-btn>
          <v-btn class="book-button" :loading="savingEdit" :disabled="!editServiceIds.length" @click="updateAppointment">Salvar alteração</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </main>
</template>

<style scoped>
.dashboard-content { min-height: calc(100dvh - 64px); background: var(--paper); padding: 40px 20px 72px; }
.dashboard-container { max-width: 1180px; }
.dashboard-intro, .section-heading, .appointment-row, .booking-summary, .slot-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.dashboard-intro { align-items: flex-start; margin-bottom: 32px; }
.dashboard-intro h1, .section-heading h2 { margin: 0; color: var(--ink); font-family: 'Instrument Serif', serif; font-weight: 400; }
.dashboard-intro h1 { font-size: clamp(2.3rem, 5vw, 3.5rem); line-height: 1; }
.dashboard-intro p:not(.section-kicker) { margin: 12px 0 0; color: var(--slate); }
.section-kicker { margin: 0 0 8px; color: var(--steel-blue); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.section-heading h2 { font-size: 2rem; line-height: 1.05; }
.dashboard-grid { align-items: flex-start; }
.dashboard-section, .booking-panel { border: 1px solid var(--hairline); background: rgba(255, 255, 255, 0.28); padding: 24px; }
.booking-panel { position: sticky; top: 88px; border-color: rgba(31, 59, 99, 0.35); background: var(--navy-deep); color: var(--paper); }
.booking-panel .section-heading h2, .booking-panel .section-kicker { color: var(--paper); }
.booking-panel .section-kicker { color: var(--steel-blue); }
.loading-line { margin: 24px 0; }
.selection-count { color: var(--slate); font-size: 0.82rem; }
.service-card { display: flex; width: 100%; min-height: 148px; gap: 16px; padding: 20px; border: 1px solid var(--hairline); background: transparent; color: var(--ink); cursor: pointer; text-align: left; transition: border-color 180ms ease, background-color 180ms ease; }
.service-card:hover, .service-card--selected { border-color: var(--steel-blue); background: rgba(93, 138, 196, 0.08); }
.service-card:focus-visible { outline: 2px solid var(--steel-blue); outline-offset: 3px; }
.service-check { display: grid; width: 28px; height: 28px; flex: 0 0 28px; place-items: center; border: 1px solid var(--slate); color: var(--steel-blue); }
.service-card--selected .service-check { border-color: var(--steel-blue); background: var(--steel-blue); color: var(--paper); }
.service-content { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 8px; }
.service-content strong { font-size: 1rem; font-weight: 600; }
.service-content small, .appointment-row span { color: var(--slate); font-size: 0.8rem; line-height: 1.5; }
.service-meta { display: flex; justify-content: space-between; margin-top: auto; color: var(--slate); font-size: 0.82rem; }
.service-meta b { color: var(--navy); font-weight: 600; }
.appointments-section { margin-top: 24px; }
.appointment-row { padding: 18px 0; border-bottom: 1px solid var(--hairline); }
.appointment-row:last-child { border-bottom: 0; }
.appointment-row strong, .appointment-row span { display: block; }
.appointment-row span { margin-top: 5px; }
.appointment-actions { display: flex; align-items: center; gap: 8px; }
.appointment-actions :deep(.v-chip) { border-radius: 4px; }
.cancel-button { color: var(--slate); text-transform: none; }
.edit-button { color: var(--navy); text-transform: none; }
.booking-hint, .empty-state, .empty-slots { display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 120px; color: var(--slate); text-align: center; }
.empty-state { flex-direction: column; border: 1px dashed var(--hairline); }
.empty-state--compact { min-height: 80px; }
.booking-hint { min-height: 160px; justify-content: flex-start; }
.booking-summary { margin: 24px 0; padding-bottom: 16px; border-bottom: 1px solid var(--hairline-dark); color: var(--slate); font-size: 0.85rem; }
.booking-summary strong { color: var(--paper); font-size: 1.1rem; }
.dashboard-input { margin-bottom: 18px; }
.booking-panel :deep(.v-field) { color: var(--paper); }
.booking-panel :deep(.v-label), .booking-panel :deep(input), .booking-panel :deep(textarea) { color: var(--paper); }
.booking-panel :deep(.v-field__outline) { color: rgba(244, 246, 249, 0.4); }
.slot-heading { margin: 8px 0 12px; color: var(--paper); font-size: 0.86rem; font-weight: 600; }
.slot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 20px; }
.slot-button { border-color: rgba(244, 246, 249, 0.3) !important; border-radius: 4px !important; color: var(--paper) !important; text-transform: none; }
.slot-button--selected { border-color: var(--steel-blue) !important; background: var(--steel-blue) !important; }
.book-button { min-height: 48px; border-radius: 4px !important; background: var(--steel-blue) !important; color: var(--paper) !important; text-transform: none; }
.logout-button { color: var(--steel-blue); text-transform: none; }
.edit-dialog { border: 1px solid var(--hairline) !important; border-radius: 8px !important; background: var(--paper) !important; }
.edit-dialog-intro { margin: 0 0 20px; color: var(--slate); font-size: 0.88rem; }
.edit-summary { display: flex; justify-content: space-between; margin: 4px 0 18px; color: var(--slate); }
.edit-summary strong { color: var(--navy); }
@media (max-width: 960px) { .booking-panel { position: static; } }
@media (max-width: 600px) { .dashboard-content { padding: 28px 12px 56px; } .dashboard-intro { margin-bottom: 24px; } .dashboard-section, .booking-panel { padding: 18px; } .appointment-row { align-items: flex-start; flex-direction: column; } .appointment-actions { width: 100%; justify-content: space-between; } }
</style>
