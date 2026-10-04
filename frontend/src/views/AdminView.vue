<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { ApexOptions } from 'apexcharts'
import ApexChart from 'vue3-apexcharts'

import { apiRequest } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { User } from '../types/auth'

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

interface SpecialDate {
  id: string
  date: string
  is_closed: boolean
  custom_open_time: string | null
  custom_close_time: string | null
  label: string | null
}

interface BlockedSlot {
  id: string
  date: string
  start_time: string
  end_time: string
  reason: string | null
}

interface Customer {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  is_active: boolean
}

interface AdminAppointment {
  id: string
  customer_id: string
  customer_name: string
  service_names: string[]
  date: string
  start_time: string
  end_time: string
  status: string
  total_price_cents: number
  total_duration_minutes: number
  notes: string | null
  possible_no_show: boolean
}

interface DashboardStats {
  total_appointments: number
  confirmed_appointments: number
  completed_appointments: number
  cancelled_appointments: number
  total_revenue_cents: number
  popular_services: { name: string; bookings: number }[]
}

interface ShopSettings {
  id: number
  name: string
  timezone: string
  capacity: number
  booking_window_days: number
  min_cancellation_notice_minutes: number
  no_show_grace_minutes: number
  slot_granularity_minutes: number
}

interface DayForm {
  weekday: number
  label: string
  morningEnabled: boolean
  morningStart: string
  morningEnd: string
  afternoonEnabled: boolean
  afternoonStart: string
  afternoonEnd: string
}

const router = useRouter()
const auth = useAuthStore()
const services = ref<Service[]>([])
const customers = ref<Customer[]>([])
const appointments = ref<AdminAppointment[]>([])
const specialDates = ref<SpecialDate[]>([])
const blockedSlots = ref<BlockedSlot[]>([])
const stats = ref<DashboardStats | null>(null)
const chartAppointments = ref<AdminAppointment[]>([])
const loadingCharts = ref(false)
const days = ref<DayForm[]>([
  { weekday: 0, label: 'Segunda-feira', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '18:00' },
  { weekday: 1, label: 'Terça-feira', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '18:00' },
  { weekday: 2, label: 'Quarta-feira', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '18:00' },
  { weekday: 3, label: 'Quinta-feira', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '18:00' },
  { weekday: 4, label: 'Sexta-feira', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '18:00' },
  { weekday: 5, label: 'Sábado', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '14:00' },
  { weekday: 6, label: 'Domingo', morningEnabled: false, morningStart: '09:00', morningEnd: '12:00', afternoonEnabled: false, afternoonStart: '14:00', afternoonEnd: '14:00' },
])
const form = ref({ id: '', name: '', description: '', price: '', duration: '30' })
const loading = ref(true)
const saving = ref(false)
const savingHours = ref(false)
const loadingAppointments = ref(false)
const creatingAppointment = ref(false)
const adminSection = ref('appointments')
const shopSettings = ref<ShopSettings | null>(null)
const settingsForm = ref({ name: '', timezone: '', capacity: '2', booking_window_days: '2', min_cancellation_notice_minutes: '60', no_show_grace_minutes: '30', slot_granularity_minutes: '30' })
const profileForm = ref({ full_name: auth.user?.full_name ?? '', email: auth.user?.email ?? '', phone: auth.user?.phone ?? '', password: '' })
const savingSettings = ref(false)
const savingProfile = ref(false)
const savingCustomer = ref(false)
const customerSearch = ref('')
const customerForm = ref({ id: '', full_name: '', email: '', phone: '', password: '' })
const savingException = ref(false)
const specialDateForm = ref({ date: formatDate(new Date()), label: '', is_closed: true, custom_open_time: '', custom_close_time: '' })
const blockedSlotForm = ref({ date: formatDate(new Date()), start_time: '12:00', end_time: '14:00', reason: '' })
const filterDate = ref(formatDate(new Date()))
const filterStatus = ref('')
const dashboardPeriod = ref<'today' | '7d' | '30d' | 'all'>('30d')
const manualDate = ref(formatDate(new Date()))
const manualCustomerId = ref('')
const manualServiceIds = ref<string[]>([])
const manualSlot = ref('')
const manualSlots = ref<string[]>([])
const manualNotes = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const swipeStartX = ref<number | null>(null)
const swipeAppointmentId = ref<string | null>(null)
const swipeOffset = ref(0)
const pendingAction = ref<{ type: 'complete' | 'cancel'; appointment: AdminAppointment } | null>(null)
const processingAction = ref(false)
const token = () => auth.accessToken ?? undefined

const editing = () => Boolean(form.value.id)
const activeServices = () => services.value.filter((service) => service.is_active)
const filteredCustomers = computed(() => {
  const query = customerSearch.value.trim().toLowerCase()
  if (!query) return customers.value
  return customers.value.filter((customer) => [customer.full_name, customer.email, customer.phone].some((value) => value?.toLowerCase().includes(query)))
})

const serviceChartSeries = computed(() => (stats.value?.popular_services ?? []).map((service) => service.bookings))
const serviceChartLabels = computed(() => (stats.value?.popular_services ?? []).map((service) => service.name))
const statusChartSeries = computed(() => [
  stats.value?.confirmed_appointments ?? 0,
  stats.value?.completed_appointments ?? 0,
  stats.value?.cancelled_appointments ?? 0,
])
const serviceChartOptions = computed<ApexOptions>(() => ({
  chart: { type: 'donut', toolbar: { show: false }, fontFamily: 'Manrope, sans-serif' },
  labels: serviceChartLabels.value,
  colors: ['var(--color-steel-blue)', 'var(--color-navy)', 'var(--color-slate)', 'var(--color-navy-deep)', 'var(--color-paper)'],
  dataLabels: { enabled: false },
  legend: { position: 'bottom', fontFamily: 'Manrope, sans-serif', labels: { colors: 'var(--color-paper)' } },
  stroke: { colors: ['var(--color-navy-deep)'] },
  plotOptions: { pie: { donut: { size: '66%', labels: { show: true, total: { show: true, label: 'Agendamentos', color: 'var(--color-slate)' } } } } },
  tooltip: { theme: 'dark' },
}))
const statusChartOptions = computed<ApexOptions>(() => ({
  chart: { type: 'donut', toolbar: { show: false }, fontFamily: 'Manrope, sans-serif' },
  labels: ['Confirmados', 'Concluídos', 'Cancelados'],
  colors: ['var(--color-steel-blue)', 'var(--color-navy)', 'var(--color-slate)'],
  dataLabels: { enabled: false },
  legend: { position: 'bottom', fontFamily: 'Manrope, sans-serif', labels: { colors: 'var(--color-paper)' } },
  stroke: { colors: ['var(--color-navy-deep)'] },
  plotOptions: { pie: { donut: { size: '66%', labels: { show: true, total: { show: true, label: 'Status', color: 'var(--color-slate)' } } } } },
  tooltip: { theme: 'dark' },
}))
const heatmapSeries = computed(() => {
  const counts = new Map<string, number>()
  chartAppointments.value.forEach((appointment) => {
    if (appointment.status !== 'CANCELLED') counts.set(appointment.date, (counts.get(appointment.date) ?? 0) + 1)
  })
  const days = Array.from({ length: 30 }, (_, index) => {
    const date = new Date()
    date.setHours(12, 0, 0, 0)
    date.setDate(date.getDate() - (29 - index))
    const key = formatDate(date)
    return { x: date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }), y: counts.get(key) ?? 0 }
  })
  return [{ name: 'Atendimentos', data: days }]
})
const heatmapChartOptions = computed<ApexOptions>(() => ({
  chart: { type: 'heatmap', toolbar: { show: false }, fontFamily: 'Manrope, sans-serif' },
  dataLabels: { enabled: false },
  colors: ['var(--color-steel-blue)'],
  plotOptions: { heatmap: { radius: 2, shadeIntensity: 0.55, colorScale: { ranges: [{ from: 0, to: 0, color: 'rgba(var(--color-slate-rgb), 0.12)', name: 'Sem atendimentos' }] } } },
  legend: { show: false },
  xaxis: { labels: { style: { colors: 'var(--color-slate)', fontFamily: 'Manrope, sans-serif' } } },
  tooltip: { y: { formatter: (value) => `${value} atendimento(s)` } },
}))

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

function resetCustomerForm() {
  customerForm.value = { id: '', full_name: '', email: '', phone: '', password: '' }
}

function editCustomer(customer: Customer) {
  customerForm.value = { id: customer.id, full_name: customer.full_name, email: customer.email ?? '', phone: customer.phone ?? '', password: '' }
}

async function saveCustomer() {
  errorMessage.value = ''
  if (!customerForm.value.full_name.trim()) {
    errorMessage.value = 'Informe o nome completo do cliente.'
    return
  }
  if (!customerForm.value.id && customerForm.value.password.length < 8) {
    errorMessage.value = 'A senha temporária precisa ter pelo menos 8 caracteres.'
    return
  }
  if (customerForm.value.password && customerForm.value.password.length < 8) {
    errorMessage.value = 'A nova senha precisa ter pelo menos 8 caracteres.'
    return
  }
  savingCustomer.value = true
  try {
    const payload: Record<string, string> = { full_name: customerForm.value.full_name.trim() }
    if (customerForm.value.email.trim()) payload.email = customerForm.value.email.trim()
    if (customerForm.value.phone.trim()) payload.phone = customerForm.value.phone.trim()
    if (customerForm.value.password) payload.password = customerForm.value.password
    const saved = await apiRequest<Customer>(customerForm.value.id ? `/admin/customers/${customerForm.value.id}` : '/admin/customers', {
      method: customerForm.value.id ? 'PATCH' : 'POST',
      body: JSON.stringify(payload),
    }, token())
    customers.value = customerForm.value.id
      ? customers.value.map((customer) => customer.id === saved.id ? saved : customer)
      : [saved, ...customers.value]
    successMessage.value = customerForm.value.id ? 'Cliente atualizado.' : 'Cliente cadastrado.'
    resetCustomerForm()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível salvar o cliente.'
  } finally {
    savingCustomer.value = false
  }
}

async function deactivateCustomer(customer: Customer) {
  if (!window.confirm(`Desativar o cadastro de ${customer.full_name}?`)) return
  try {
    await apiRequest<void>(`/admin/customers/${customer.id}`, { method: 'DELETE' }, token())
    customer.is_active = false
    customers.value = [...customers.value]
    successMessage.value = 'Cliente desativado.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível desativar o cliente.'
  }
}

async function loadAdminData() {
  loading.value = true
  try {
    const [serviceData, hourData, customerData, settingsData, specialData, blockedData] = await Promise.all([
      apiRequest<Service[]>('/admin/services', {}, token()),
      apiRequest<BusinessHour[]>('/admin/business-hours', {}, token()),
      apiRequest<Customer[]>('/admin/customers?limit=100', {}, token()),
      apiRequest<ShopSettings>('/admin/settings', {}, token()),
      apiRequest<SpecialDate[]>('/admin/special-dates', {}, token()),
      apiRequest<BlockedSlot[]>('/admin/blocked-slots', {}, token()),
    ])
    services.value = serviceData
    customers.value = customerData
    specialDates.value = specialData
    blockedSlots.value = blockedData
    shopSettings.value = settingsData
    settingsForm.value = {
      name: settingsData.name,
      timezone: settingsData.timezone,
      capacity: String(settingsData.capacity),
      booking_window_days: String(settingsData.booking_window_days),
      min_cancellation_notice_minutes: String(settingsData.min_cancellation_notice_minutes),
      no_show_grace_minutes: String(settingsData.no_show_grace_minutes),
      slot_granularity_minutes: String(settingsData.slot_granularity_minutes),
    }
    hourData.forEach((hour) => {
      const day = days.value.find((item) => item.weekday === hour.weekday)
      if (day) {
        const start = hour.start_time.slice(0, 5)
        const end = hour.end_time.slice(0, 5)
        if (start < '14:00') {
          day.morningEnabled = true
          day.morningStart = start
          day.morningEnd = end
        } else {
          day.afternoonEnabled = true
          day.afternoonStart = start
          day.afternoonEnd = end
        }
      }
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar a área administrativa.'
  } finally {
    loading.value = false
  }
}

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10)
}

function formatTime(value: string) {
  return value.slice(0, 5)
}

function statusLabel(status: string) {
  const labels: Record<string, string> = { PENDING: 'Pendente', CONFIRMED: 'Confirmado', COMPLETED: 'Concluído', CANCELLED: 'Cancelado', NO_SHOW: 'Não compareceu' }
  return labels[status] ?? status
}

function statusColor(status: string) {
  return status === 'CANCELLED' || status === 'NO_SHOW' ? 'slate' : 'steel-blue'
}

async function loadAppointments() {
  loadingAppointments.value = true
  try {
    const query = new URLSearchParams()
    if (filterDate.value) query.set('date', filterDate.value)
    if (filterStatus.value) query.set('status', filterStatus.value)
    appointments.value = await apiRequest<AdminAppointment[]>(`/admin/appointments?${query.toString()}`, {}, token())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar os agendamentos.'
  } finally {
    loadingAppointments.value = false
  }
}

async function loadStats() {
  try {
    const query = new URLSearchParams()
    if (dashboardPeriod.value !== 'all') {
      const start = new Date()
      start.setHours(12, 0, 0, 0)
      if (dashboardPeriod.value === '7d') start.setDate(start.getDate() - 6)
      if (dashboardPeriod.value === '30d') start.setDate(start.getDate() - 29)
      query.set('from', formatDate(start))
      query.set('to', formatDate(new Date()))
    }
    stats.value = await apiRequest<DashboardStats>(`/admin/appointments/dashboard${query.toString() ? `?${query.toString()}` : ''}`, {}, token())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar os indicadores.'
  }
}

async function loadChartAppointments() {
  loadingCharts.value = true
  try {
    chartAppointments.value = await apiRequest<AdminAppointment[]>('/admin/appointments', {}, token())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível carregar os dados dos gráficos.'
  } finally {
    loadingCharts.value = false
  }
}

async function loadManualSlots() {
  manualSlot.value = ''
  manualSlots.value = []
  if (!manualDate.value || !manualServiceIds.value.length) return
  try {
    const query = new URLSearchParams({ date: manualDate.value })
    manualServiceIds.value.forEach((id) => query.append('service_ids', id))
    const availability = await apiRequest<{ slots: string[] }>(`/availability?${query.toString()}`, {}, token())
    manualSlots.value = [...new Set(availability.slots)]
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível consultar os horários.'
  }
}

async function createManualAppointment() {
  if (!manualCustomerId.value || !manualServiceIds.value.length || !manualSlot.value) return
  creatingAppointment.value = true
  try {
    await apiRequest<AdminAppointment>('/admin/appointments', {
      method: 'POST',
      body: JSON.stringify({ customer_id: manualCustomerId.value, date: manualDate.value, start_time: manualSlot.value, service_ids: manualServiceIds.value, notes: manualNotes.value.trim() || undefined }),
    }, token())
    successMessage.value = 'Agendamento criado para o cliente.'
    manualSlot.value = ''
    manualNotes.value = ''
    await Promise.all([loadAppointments(), loadStats(), loadManualSlots()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível criar o agendamento.'
  } finally {
    creatingAppointment.value = false
  }
}

async function cancelAdminAppointment(appointment: AdminAppointment) {
  pendingAction.value = { type: 'cancel', appointment }
}

async function completeAppointment(appointment: AdminAppointment) {
  pendingAction.value = { type: 'complete', appointment }
}

async function confirmPendingAction() {
  if (!pendingAction.value) return
  const action = pendingAction.value
  pendingAction.value = null
  processingAction.value = true
  try {
    if (action.type === 'cancel') {
      await apiRequest<AdminAppointment>(`/admin/appointments/${action.appointment.id}/cancel`, {
        method: 'PATCH',
        body: JSON.stringify({ reason: 'Cancelado pelo administrador' }),
      }, token())
      successMessage.value = 'Agendamento cancelado.'
    } else {
      await apiRequest<AdminAppointment>(`/admin/appointments/${action.appointment.id}/complete`, { method: 'PATCH' }, token())
      successMessage.value = 'Atendimento concluído.'
    }
    await Promise.all([loadAppointments(), loadStats()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível atualizar o agendamento.'
  } finally {
    processingAction.value = false
  }
}

async function markNoShow(appointment: AdminAppointment) {
  if (!window.confirm(`Confirmar que ${appointment.customer_name} não compareceu ao atendimento?`)) return
  try {
    await apiRequest<AdminAppointment>(`/admin/appointments/${appointment.id}/no-show`, { method: 'PATCH' }, token())
    successMessage.value = 'Agendamento marcado como “Não compareceu”.'
    await Promise.all([loadAppointments(), loadStats()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível atualizar o agendamento.'
  }
}

function beginAppointmentSwipe(event: PointerEvent, appointment: AdminAppointment) {
  if ((event.target as HTMLElement).closest('button, input, select, textarea')) return
  swipeStartX.value = event.clientX
  swipeAppointmentId.value = appointment.id
  swipeOffset.value = 0
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
}

function moveAppointmentSwipe(event: PointerEvent, appointment: AdminAppointment) {
  if (swipeStartX.value === null || swipeAppointmentId.value !== appointment.id) return
  const distance = event.clientX - swipeStartX.value
  swipeOffset.value = Math.max(-140, Math.min(140, distance))
}

async function finishAppointmentSwipe(appointment: AdminAppointment) {
  if (swipeStartX.value === null || swipeAppointmentId.value !== appointment.id) return
  const distance = swipeOffset.value
  swipeStartX.value = null
  swipeAppointmentId.value = null
  swipeOffset.value = 0
  if (Math.abs(distance) < 90) return
  if (distance > 0 && appointment.status === 'CONFIRMED') completeAppointment(appointment)
  if (distance < 0 && ['PENDING', 'CONFIRMED'].includes(appointment.status)) cancelAdminAppointment(appointment)
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
    const payload = days.value.flatMap((day) => {
      const intervals = []
      if (day.morningEnabled) intervals.push({ weekday: day.weekday, start_time: `${day.morningStart}:00`, end_time: `${day.morningEnd}:00` })
      if (day.afternoonEnabled) intervals.push({ weekday: day.weekday, start_time: `${day.afternoonStart}:00`, end_time: `${day.afternoonEnd}:00` })
      return intervals
    })
    await apiRequest<BusinessHour[]>('/admin/business-hours', { method: 'PUT', body: JSON.stringify(payload) }, token())
    successMessage.value = 'Horários de funcionamento atualizados.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível salvar os horários.'
  } finally {
    savingHours.value = false
  }
}

async function createSpecialDate() {
  savingException.value = true
  try {
    const saved = await apiRequest<SpecialDate>('/admin/special-dates', {
      method: 'POST',
      body: JSON.stringify({ date: specialDateForm.value.date, label: specialDateForm.value.label.trim() || undefined, is_closed: specialDateForm.value.is_closed, custom_open_time: specialDateForm.value.is_closed ? undefined : `${specialDateForm.value.custom_open_time}:00`, custom_close_time: specialDateForm.value.is_closed ? undefined : `${specialDateForm.value.custom_close_time}:00` }),
    }, token())
    specialDates.value = [...specialDates.value, saved].sort((a, b) => a.date.localeCompare(b.date))
    successMessage.value = 'Data especial cadastrada.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível cadastrar a data especial.'
  } finally {
    savingException.value = false
  }
}

async function removeSpecialDate(item: SpecialDate) {
  if (!window.confirm(`Remover a exceção de ${formatDateLabel(item.date)}?`)) return
  try {
    await apiRequest<void>(`/admin/special-dates/${item.id}`, { method: 'DELETE' }, token())
    specialDates.value = specialDates.value.filter((entry) => entry.id !== item.id)
    successMessage.value = 'Data especial removida.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível remover a data especial.'
  }
}

async function createBlockedSlot() {
  savingException.value = true
  try {
    const saved = await apiRequest<BlockedSlot>('/admin/blocked-slots', {
      method: 'POST',
      body: JSON.stringify({ date: blockedSlotForm.value.date, start_time: `${blockedSlotForm.value.start_time}:00`, end_time: `${blockedSlotForm.value.end_time}:00`, reason: blockedSlotForm.value.reason.trim() || undefined }),
    }, token())
    blockedSlots.value = [...blockedSlots.value, saved].sort((a, b) => `${a.date}${a.start_time}`.localeCompare(`${b.date}${b.start_time}`))
    successMessage.value = 'Bloqueio de horário cadastrado.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível cadastrar o bloqueio.'
  } finally {
    savingException.value = false
  }
}

async function removeBlockedSlot(item: BlockedSlot) {
  if (!window.confirm(`Remover o bloqueio de ${formatDateLabel(item.date)}?`)) return
  try {
    await apiRequest<void>(`/admin/blocked-slots/${item.id}`, { method: 'DELETE' }, token())
    blockedSlots.value = blockedSlots.value.filter((entry) => entry.id !== item.id)
    successMessage.value = 'Bloqueio removido.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível remover o bloqueio.'
  }
}

function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`))
}

async function saveShopSettings() {
  savingSettings.value = true
  try {
    const saved = await apiRequest<ShopSettings>('/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        name: settingsForm.value.name.trim(),
        timezone: settingsForm.value.timezone.trim(),
        capacity: Number(settingsForm.value.capacity),
        booking_window_days: Number(settingsForm.value.booking_window_days),
        min_cancellation_notice_minutes: Number(settingsForm.value.min_cancellation_notice_minutes),
        no_show_grace_minutes: Number(settingsForm.value.no_show_grace_minutes),
        slot_granularity_minutes: Number(settingsForm.value.slot_granularity_minutes),
      }),
    }, token())
    shopSettings.value = saved
    successMessage.value = 'Dados da barbearia atualizados.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível salvar as configurações.'
  } finally {
    savingSettings.value = false
  }
}

async function saveProfile() {
  savingProfile.value = true
  try {
    const payload: Record<string, string> = {
      full_name: profileForm.value.full_name.trim(),
      email: profileForm.value.email.trim(),
      phone: profileForm.value.phone.trim(),
    }
    if (profileForm.value.password) payload.password = profileForm.value.password
    const updated = await apiRequest<User>('/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }, token())
    auth.user = updated
    profileForm.value.password = ''
    successMessage.value = 'Perfil atualizado.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Não foi possível atualizar o perfil.'
  } finally {
    savingProfile.value = false
  }
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}

onMounted(async () => {
  await loadAdminData()
  await Promise.all([loadAppointments(), loadStats(), loadChartAppointments()])
})
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

      <nav class="admin-navigation" aria-label="Navegação administrativa">
        <button
          v-for="item in [
            { key: 'appointments', label: 'Agendamentos', icon: 'mdi-calendar-month-outline' },
            { key: 'dashboard', label: 'Dashboard', icon: 'mdi-view-dashboard-outline' },
            { key: 'services', label: 'Serviços', icon: 'mdi-content-cut' },
            { key: 'customers', label: 'Clientes', icon: 'mdi-account-group-outline' },
            { key: 'hours', label: 'Horários', icon: 'mdi-clock-outline' },
            { key: 'exceptions', label: 'Exceções', icon: 'mdi-calendar-alert-outline' },
            { key: 'settings', label: 'Configurações', icon: 'mdi-cog-outline' },
          ]"
          :key="item.key"
          class="admin-nav-item"
          :class="{ 'admin-nav-item--active': adminSection === item.key }"
          :aria-current="adminSection === item.key ? 'page' : undefined"
          type="button"
          @click="adminSection = item.key"
        >
          <v-icon :icon="item.icon" size="19" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <v-alert v-if="errorMessage" type="error" variant="tonal" closable @click:close="errorMessage = ''">{{ errorMessage }}</v-alert>
      <v-alert v-if="successMessage" type="success" variant="tonal" closable @click:close="successMessage = ''">{{ successMessage }}</v-alert>
      <v-progress-linear v-if="loading" indeterminate color="steel-blue" class="loading-line" />

      <v-row v-else class="admin-grid">
        <v-col v-if="adminSection === 'dashboard'" cols="12">
          <div class="dashboard-toolbar">
            <div>
              <p class="section-kicker">Visão geral</p>
              <h2>Desempenho da barbearia</h2>
            </div>
            <v-btn-toggle v-model="dashboardPeriod" mandatory density="comfortable" class="period-toggle" @update:model-value="loadStats">
              <v-btn value="today">Hoje</v-btn>
              <v-btn value="7d">7 dias</v-btn>
              <v-btn value="30d">30 dias</v-btn>
              <v-btn value="all">Todos</v-btn>
            </v-btn-toggle>
          </div>
          <section class="metrics-grid">
            <article class="metric-card">
              <span>Agendamentos ativos</span>
              <strong>{{ stats?.total_appointments ?? 0 }}</strong>
              <small>{{ stats?.confirmed_appointments ?? 0 }} confirmados</small>
            </article>
            <article class="metric-card">
              <span>Faturamento previsto</span>
              <strong>{{ formatMoney(stats?.total_revenue_cents ?? 0) }}</strong>
              <small>Reservas não canceladas</small>
            </article>
            <article class="metric-card">
              <span>Concluídos</span>
              <strong>{{ stats?.completed_appointments ?? 0 }}</strong>
              <small>Atendimentos realizados</small>
            </article>
            <article class="metric-card metric-card--cancelled">
              <span>Cancelados</span>
              <strong>{{ stats?.cancelled_appointments ?? 0 }}</strong>
              <small>Ficam fora do faturamento</small>
            </article>
            <article class="metric-card metric-card--accent">
              <span>Mais procurado</span>
              <strong>{{ stats?.popular_services?.[0]?.name || 'Ainda sem dados' }}</strong>
              <small>{{ stats?.popular_services?.[0]?.bookings || 0 }} agendamento(s)</small>
            </article>
          </section>
          <section class="dashboard-insights" aria-label="Resumo da operação">
            <article class="insight-panel">
              <div class="insight-heading">
                <div>
                  <p class="section-kicker">Catálogo</p>
                  <h2>Serviços mais procurados</h2>
                </div>
                <v-icon icon="mdi-chart-donut" aria-hidden="true" />
              </div>
              <div v-if="!serviceChartSeries.length" class="empty-state empty-state--compact">Ainda não há dados suficientes.</div>
              <ApexChart v-else type="donut" height="230" :options="serviceChartOptions" :series="serviceChartSeries" />
            </article>
            <article class="insight-panel">
              <div class="insight-heading">
                <div>
                  <p class="section-kicker">Status</p>
                  <h2>Resumo dos atendimentos</h2>
                </div>
                <v-icon icon="mdi-chart-arc" aria-hidden="true" />
              </div>
              <ApexChart type="donut" height="230" :options="statusChartOptions" :series="statusChartSeries" />
            </article>
            <article class="insight-panel insight-panel--heatmap">
              <div class="insight-heading">
                <div>
                  <p class="section-kicker">Ritmo da agenda</p>
                  <h2>Atendimentos nos últimos 30 dias</h2>
                </div>
                <v-progress-circular v-if="loadingCharts" indeterminate size="18" width="2" color="steel-blue" />
              </div>
              <ApexChart type="heatmap" height="190" :options="heatmapChartOptions" :series="heatmapSeries" />
            </article>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'dashboard'" cols="12">
          <section class="upcoming-panel">
            <div class="insight-heading">
              <div>
                <p class="section-kicker">Agenda</p>
                <h2>Próximos atendimentos</h2>
              </div>
              <v-btn variant="outlined" color="slate" size="small" @click="adminSection = 'appointments'">Ver agenda</v-btn>
            </div>
            <div v-if="!appointments.length" class="empty-state empty-state--compact">Nenhum atendimento encontrado para a data selecionada.</div>
            <div v-for="appointment in appointments.slice(0, 5)" :key="`upcoming-${appointment.id}`" class="upcoming-row">
              <div class="upcoming-time">{{ formatTime(appointment.start_time) }}</div>
              <div class="upcoming-main">
                <strong>{{ appointment.customer_name }}</strong>
                <span>{{ appointment.service_names.join(' · ') }}</span>
              </div>
              <span class="appointment-status" :class="`appointment-status--${appointment.status.toLowerCase()}`">
                <i aria-hidden="true" />{{ statusLabel(appointment.status) }}
              </span>
              <strong class="upcoming-price">{{ formatMoney(appointment.total_price_cents) }}</strong>
            </div>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'appointments'" cols="12" lg="7">
          <section class="admin-section agenda-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Operação</p>
                <h2>Agendamentos</h2>
                <small class="swipe-hint">No celular, deslize para a direita para concluir ou para a esquerda para cancelar.</small>
              </div>
              <v-btn variant="outlined" color="slate" @click="filterDate = ''; loadAppointments()">Ver todos</v-btn>
            </div>
            <div class="filter-bar">
              <v-text-field v-model="filterDate" label="Filtrar por data" type="date" variant="outlined" density="compact" hide-details @change="loadAppointments" />
              <v-select v-model="filterStatus" label="Status" :items="[{ title: 'Todos', value: '' }, { title: 'Confirmados', value: 'CONFIRMED' }, { title: 'Concluídos', value: 'COMPLETED' }, { title: 'Cancelados', value: 'CANCELLED' }]" variant="outlined" density="compact" hide-details @update:model-value="loadAppointments" />
            </div>
            <v-progress-linear v-if="loadingAppointments" indeterminate color="steel-blue" />
            <div v-else-if="!appointments.length" class="empty-state">Nenhum agendamento encontrado para este filtro.</div>
            <div
              v-for="appointment in appointments"
              :key="appointment.id"
              class="appointment-row"
              :class="{ 'appointment-row--dragging': swipeAppointmentId === appointment.id }"
              :style="swipeAppointmentId === appointment.id ? { transform: `translateX(${swipeOffset}px)` } : undefined"
              @pointerdown="beginAppointmentSwipe($event, appointment)"
              @pointermove="moveAppointmentSwipe($event, appointment)"
              @pointerup="finishAppointmentSwipe(appointment)"
              @pointercancel="swipeStartX = null; swipeAppointmentId = null; swipeOffset = 0"
            >
              <div>
                <strong>{{ formatTime(appointment.start_time) }} · {{ appointment.customer_name }}</strong>
                <span>{{ appointment.service_names.join(' · ') }} · {{ formatMoney(appointment.total_price_cents) }}</span>
              </div>
              <div class="appointment-row-actions">
                <span class="appointment-status" :class="`appointment-status--${appointment.status.toLowerCase()}`">
                  <i aria-hidden="true" />
                  {{ statusLabel(appointment.status) }}
                </span>
                <v-btn v-if="appointment.status === 'CONFIRMED'" class="complete-button" variant="outlined" size="small" @click="completeAppointment(appointment)">
                  Concluir
                </v-btn>
                <v-menu v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)" location="bottom end">
                  <template #activator="{ props }">
                    <v-btn v-bind="props" icon="mdi-dots-vertical" variant="text" size="small" class="appointment-menu-button" aria-label="Mais ações" />
                  </template>
                  <v-list density="compact" min-width="210">
                    <v-list-item v-if="appointment.possible_no_show" prepend-icon="mdi-account-off-outline" title="Não compareceu" @click="markNoShow(appointment)" />
                    <v-list-item v-if="appointment.status === 'CONFIRMED'" prepend-icon="mdi-check-circle-outline" title="Concluir atendimento" @click="completeAppointment(appointment)" />
                    <v-list-item prepend-icon="mdi-close-circle-outline" title="Cancelar agendamento" @click="cancelAdminAppointment(appointment)" />
                  </v-list>
                </v-menu>
                <v-btn v-if="appointment.possible_no_show" class="no-show-button" variant="outlined" size="small" @click="markNoShow(appointment)">
                  Marcar como não compareceu
                </v-btn>
                <v-btn v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)" class="cancel-appointment-button" variant="outlined" size="small" @click="cancelAdminAppointment(appointment)">
                  Cancelar
                </v-btn>
              </div>
            </div>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'appointments'" cols="12" lg="5">
          <section class="form-panel manual-panel">
            <p class="section-kicker">Operação</p>
            <h2>Agendar cliente</h2>
            <v-select v-model="manualCustomerId" label="Cliente" :items="customers" item-title="full_name" item-value="id" variant="outlined" />
            <v-select v-model="manualServiceIds" label="Serviços" :items="activeServices()" item-title="name" item-value="id" multiple chips variant="outlined" @update:model-value="loadManualSlots" />
            <v-text-field v-model="manualDate" label="Data" type="date" variant="outlined" @change="loadManualSlots" />
            <div class="manual-slots">
              <v-btn v-for="slot in manualSlots" :key="slot" class="manual-slot" :class="{ 'manual-slot--selected': manualSlot === slot }" variant="outlined" size="small" @click="manualSlot = slot">{{ formatTime(slot) }}</v-btn>
              <span v-if="!manualSlots.length" class="empty-slots">Selecione serviços e data.</span>
            </div>
            <v-textarea v-model="manualNotes" label="Observações" rows="2" variant="outlined" />
            <v-btn class="save-button" block :loading="creatingAppointment" :disabled="!manualCustomerId || !manualServiceIds.length || !manualSlot" @click="createManualAppointment">Confirmar agendamento</v-btn>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'services' || adminSection === 'hours'" cols="12" lg="7">
          <section v-if="adminSection === 'services'" class="admin-section">
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

          <section v-if="adminSection === 'hours'" class="admin-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Agenda</p>
                <h2>Horários de funcionamento</h2>
              </div>
            </div>
            <div v-for="day in days" :key="day.weekday" class="day-row">
              <strong class="day-label">{{ day.label }}</strong>
              <div class="day-period">
                <v-checkbox v-model="day.morningEnabled" label="Manhã" hide-details color="steel-blue" />
                <v-text-field v-model="day.morningStart" type="time" variant="outlined" density="compact" hide-details :disabled="!day.morningEnabled" />
                <span class="day-separator">até</span>
                <v-text-field v-model="day.morningEnd" type="time" variant="outlined" density="compact" hide-details :disabled="!day.morningEnabled" />
              </div>
              <div class="day-period">
                <v-checkbox v-model="day.afternoonEnabled" label="Tarde" hide-details color="steel-blue" />
                <v-text-field v-model="day.afternoonStart" type="time" variant="outlined" density="compact" hide-details :disabled="!day.afternoonEnabled" />
                <span class="day-separator">até</span>
                <v-text-field v-model="day.afternoonEnd" type="time" variant="outlined" density="compact" hide-details :disabled="!day.afternoonEnabled" />
              </div>
            </div>
            <v-btn class="save-button" :loading="savingHours" @click="saveBusinessHours">Salvar horários</v-btn>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'services'" cols="12" lg="5">
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

        <v-col v-if="adminSection === 'customers'" cols="12">
          <v-row>
            <v-col cols="12" lg="7">
              <section class="admin-section">
                <div class="section-heading">
                  <div><p class="section-kicker">Relacionamento</p><h2>Clientes</h2></div>
                  <v-btn variant="outlined" color="slate" @click="resetCustomerForm">Novo cliente</v-btn>
                </div>
                <v-text-field v-model="customerSearch" label="Buscar por nome, e-mail ou telefone" prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details class="customer-search" />
                <div v-if="!filteredCustomers.length" class="empty-state">Nenhum cliente encontrado.</div>
                <div v-for="customer in filteredCustomers" :key="customer.id" class="customer-row" :class="{ 'customer-row--inactive': !customer.is_active }">
                  <div><strong>{{ customer.full_name }}</strong><span>{{ customer.email || customer.phone || 'Sem contato cadastrado' }}</span></div>
                  <div class="row-actions"><v-chip size="small" variant="outlined">{{ customer.is_active ? 'Ativo' : 'Inativo' }}</v-chip><v-btn variant="text" size="small" @click="editCustomer(customer)">Editar</v-btn><v-btn v-if="customer.is_active" variant="text" size="small" @click="deactivateCustomer(customer)">Desativar</v-btn></div>
                </div>
              </section>
            </v-col>
            <v-col cols="12" lg="5">
              <section class="form-panel">
                <p class="section-kicker">{{ customerForm.id ? 'Editar cliente' : 'Novo cliente' }}</p>
                <h2>{{ customerForm.id ? 'Atualizar cadastro' : 'Cadastrar cliente' }}</h2>
                <v-text-field v-model="customerForm.full_name" label="Nome completo" variant="outlined" />
                <v-text-field v-model="customerForm.email" label="E-mail" type="email" variant="outlined" />
                <v-text-field v-model="customerForm.phone" label="Telefone" variant="outlined" />
                <v-text-field v-model="customerForm.password" :label="customerForm.id ? 'Nova senha (opcional)' : 'Senha temporária'" type="password" variant="outlined" :hint="customerForm.id ? 'Deixe em branco para manter a senha atual.' : 'Mínimo de 8 caracteres.'" persistent-hint />
                <v-btn class="save-button" block :loading="savingCustomer" @click="saveCustomer">{{ customerForm.id ? 'Salvar alterações' : 'Cadastrar cliente' }}</v-btn>
              </section>
            </v-col>
          </v-row>
        </v-col>

        <v-col v-if="adminSection === 'settings'" cols="12">
          <v-row>
            <v-col cols="12" md="6">
              <section class="settings-panel">
                <p class="section-kicker">Perfil do administrador</p>
                <h2>Seus dados</h2>
                <v-text-field v-model="profileForm.full_name" label="Nome completo" variant="outlined" />
                <v-text-field v-model="profileForm.email" label="E-mail" type="email" variant="outlined" />
                <v-text-field v-model="profileForm.phone" label="Telefone" variant="outlined" />
                <v-text-field v-model="profileForm.password" label="Nova senha (opcional)" type="password" hint="Deixe em branco para manter a senha atual." persistent-hint variant="outlined" />
                <v-btn class="save-button" :loading="savingProfile" @click="saveProfile">Salvar meu perfil</v-btn>
              </section>
            </v-col>
            <v-col cols="12" md="6">
              <section class="settings-panel settings-panel--dark">
                <p class="section-kicker">Dados da barbearia</p>
                <h2>Informações gerais</h2>
                <v-text-field v-model="settingsForm.name" label="Nome da barbearia" variant="outlined" />
                <v-text-field v-model="settingsForm.timezone" label="Fuso horário" variant="outlined" />
                <v-row>
                  <v-col cols="6"><v-text-field v-model="settingsForm.capacity" label="Atendimentos simultâneos" type="number" variant="outlined" /></v-col>
                  <v-col cols="6"><v-text-field v-model="settingsForm.booking_window_days" label="Dias para agendar" type="number" variant="outlined" /></v-col>
                </v-row>
                <v-row>
                  <v-col cols="6"><v-text-field v-model="settingsForm.min_cancellation_notice_minutes" label="Aviso para cancelar (min)" type="number" variant="outlined" /></v-col>
                  <v-col cols="6"><v-text-field v-model="settingsForm.slot_granularity_minutes" label="Intervalo (min)" type="number" variant="outlined" /></v-col>
                </v-row>
                <v-btn class="save-button" :loading="savingSettings" @click="saveShopSettings">Salvar dados da barbearia</v-btn>
              </section>
            </v-col>
          </v-row>
        </v-col>

        <v-col v-if="adminSection === 'exceptions'" cols="12">
          <v-row>
            <v-col cols="12" md="6">
              <section class="settings-panel">
                <p class="section-kicker">Exceções de calendário</p>
                <h2>Feriados e dias especiais</h2>
                <v-text-field v-model="specialDateForm.date" label="Data" type="date" variant="outlined" />
                <v-text-field v-model="specialDateForm.label" label="Descrição" placeholder="Feriado, evento ou horário especial" variant="outlined" />
                <v-checkbox v-model="specialDateForm.is_closed" label="Barbearia fechada nesta data" color="steel-blue" hide-details />
                <v-row v-if="!specialDateForm.is_closed">
                  <v-col cols="6"><v-text-field v-model="specialDateForm.custom_open_time" label="Abertura" type="time" variant="outlined" /></v-col>
                  <v-col cols="6"><v-text-field v-model="specialDateForm.custom_close_time" label="Fechamento" type="time" variant="outlined" /></v-col>
                </v-row>
                <v-btn class="save-button" :loading="savingException" @click="createSpecialDate">Adicionar exceção</v-btn>
                <div v-if="!specialDates.length" class="empty-state">Nenhuma data especial cadastrada.</div>
                <div v-for="item in specialDates" :key="item.id" class="exception-row">
                  <div><strong>{{ formatDateLabel(item.date) }}</strong><span>{{ item.label || (item.is_closed ? 'Fechado' : `${item.custom_open_time?.slice(0, 5)} às ${item.custom_close_time?.slice(0, 5)}`) }}</span></div>
                  <v-btn variant="text" size="small" @click="removeSpecialDate(item)">Remover</v-btn>
                </div>
              </section>
            </v-col>
            <v-col cols="12" md="6">
              <section class="settings-panel settings-panel--dark">
                <p class="section-kicker">Indisponibilidade pontual</p>
                <h2>Bloquear horário</h2>
                <v-text-field v-model="blockedSlotForm.date" label="Data" type="date" variant="outlined" />
                <v-row>
                  <v-col cols="6"><v-text-field v-model="blockedSlotForm.start_time" label="Início" type="time" variant="outlined" /></v-col>
                  <v-col cols="6"><v-text-field v-model="blockedSlotForm.end_time" label="Fim" type="time" variant="outlined" /></v-col>
                </v-row>
                <v-text-field v-model="blockedSlotForm.reason" label="Motivo (opcional)" variant="outlined" />
                <v-btn class="save-button" :loading="savingException" @click="createBlockedSlot">Bloquear horário</v-btn>
                <div v-if="!blockedSlots.length" class="empty-state">Nenhum horário bloqueado.</div>
                <div v-for="item in blockedSlots" :key="item.id" class="exception-row">
                  <div><strong>{{ formatDateLabel(item.date) }} · {{ formatTime(item.start_time) }}–{{ formatTime(item.end_time) }}</strong><span>{{ item.reason || 'Indisponibilidade manual' }}</span></div>
                  <v-btn variant="text" size="small" @click="removeBlockedSlot(item)">Remover</v-btn>
                </div>
              </section>
            </v-col>
          </v-row>
        </v-col>
      </v-row>

      <v-dialog :model-value="Boolean(pendingAction)" max-width="440" @update:model-value="(value) => !value && (pendingAction = null)">
        <v-card class="confirmation-dialog">
          <v-card-title>{{ pendingAction?.type === 'cancel' ? 'Cancelar agendamento?' : 'Concluir atendimento?' }}</v-card-title>
          <v-card-text>
            {{ pendingAction?.type === 'cancel'
              ? `Deseja cancelar o agendamento de ${pendingAction.appointment.customer_name}?`
              : `Deseja marcar o atendimento de ${pendingAction?.appointment.customer_name} como concluído?` }}
          </v-card-text>
          <v-card-actions>
            <v-btn variant="text" :disabled="processingAction" @click="pendingAction = null">Não, voltar</v-btn>
            <v-btn class="save-button" :loading="processingAction" @click="confirmPendingAction">Sim, confirmar</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
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
.admin-navigation { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; margin-bottom: 28px; padding: 8px; border: 1px solid var(--hairline); background: var(--surface-white-medium); backdrop-filter: blur(8px); }
.admin-nav-item { display: flex; min-height: 52px; align-items: center; justify-content: center; gap: 9px; border: 1px solid transparent; background: transparent; color: var(--navy); cursor: pointer; font-family: var(--font-ui); font-size: 0.84rem; font-weight: 600; transition: border-color var(--motion-fast), background-color var(--motion-fast), color var(--motion-fast), transform var(--motion-fast); }
.admin-nav-item:active { transform: scale(0.98); }
.admin-nav-item:hover, .admin-nav-item--active { border-color: var(--surface-steel-blue-border); background: var(--surface-steel-blue-subtle); color: var(--navy); }
.admin-nav-item--active { box-shadow: inset 0 -2px 0 var(--steel-blue); }
.section-kicker { margin: 0 0 8px; color: var(--steel-blue); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.section-heading h2, .form-panel h2 { font-size: 2rem; line-height: 1.05; }
.section-heading { margin-bottom: 4px; }
.admin-section, .form-panel { border: 1px solid var(--hairline); padding: 24px; background: var(--surface-white-soft); transition: border-color var(--motion-fast); }
.admin-section:hover { border-color: var(--hairline-strong); }
.form-panel { position: sticky; top: 88px; background: var(--navy-deep); }
.form-panel h2 { margin-bottom: 24px; color: var(--paper); }
.form-panel :deep(.v-label), .form-panel :deep(input), .form-panel :deep(textarea) { color: var(--paper); }
.form-panel :deep(.v-field__outline) { color: var(--surface-paper-outline-strong); }
.settings-panel { height: 100%; border: 1px solid var(--hairline); padding: 24px; background: var(--surface-white-soft); }
.settings-panel h2 { margin: 0 0 24px; color: var(--ink); font-family: 'Instrument Serif', serif; font-size: 2rem; font-weight: 400; }
.settings-panel--dark { background: var(--navy-deep); }
.settings-panel--dark h2 { color: var(--paper); }
.settings-panel--dark :deep(.v-label), .settings-panel--dark :deep(input) { color: var(--paper); }
.settings-panel--dark :deep(.v-field__outline) { color: var(--surface-paper-outline-strong); }
.metrics-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.metric-card { min-height: 132px; padding: 20px; border: 1px solid var(--hairline); background: var(--surface-white-soft); transition: border-color var(--motion-fast), transform var(--motion-fast); }
.metric-card:hover { border-color: var(--hairline-strong); transform: translateY(-2px); }
.metric-card--accent { border-color: var(--surface-navy-strong-border); background: var(--surface-steel-blue-soft); }
.metric-card--cancelled { border-color: var(--surface-slate-border); background: var(--surface-slate-soft); }
.metric-card span, .metric-card small { display: block; color: var(--slate); font-size: 0.78rem; }
.metric-card strong { display: block; overflow: hidden; margin: 10px 0 8px; color: var(--ink); font-size: clamp(1.3rem, 2vw, 1.8rem); font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.dashboard-insights { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.insight-panel { min-height: 220px; padding: 20px; border: 1px solid var(--hairline); background: var(--surface-white-soft); }
.insight-panel--heatmap { grid-column: 1 / -1; min-height: 240px; }
.insight-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 24px; }
.insight-heading h2 { margin: 0; color: var(--ink); font-family: var(--font-display); font-size: 1.55rem; font-weight: 400; line-height: 1.05; }
.insight-heading > .v-icon { color: var(--steel-blue); }
.insight-bar-row + .insight-bar-row { margin-top: 16px; }
.insight-bar-label { display: flex; justify-content: space-between; gap: 12px; color: var(--ink); font-size: 0.8rem; }
.insight-bar-label strong { color: var(--slate); font-weight: 600; }
.insight-bar-track { height: 6px; margin-top: 7px; overflow: hidden; background: rgba(var(--color-slate-rgb), 0.18); }
.insight-bar-fill { display: block; height: 100%; background: var(--steel-blue); transition: width var(--motion-normal); }
.insight-bar-fill--1 { background: var(--navy); }
.insight-bar-fill--2 { background: var(--slate); }
.status-summary { display: grid; gap: 14px; }
.status-summary > div { display: grid; grid-template-columns: 9px 1fr auto; align-items: center; gap: 9px; color: var(--slate); font-size: 0.82rem; }
.status-summary strong { color: var(--ink); font-size: 1rem; font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--slate); }
.status-dot--confirmed { background: var(--steel-blue); }
.status-dot--completed { background: var(--navy); }
.status-dot--cancelled { background: var(--slate); }
.agenda-section { height: 100%; }
.filter-bar { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0 12px; }
.appointment-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--hairline); touch-action: pan-y; user-select: none; transform: translateX(0); transition: transform 180ms ease, background-color 180ms ease; }
.appointment-row--dragging { z-index: 1; cursor: grabbing; background: var(--surface-steel-blue-soft); box-shadow: var(--shadow-drag); transition: none; }
.appointment-row:last-child { border-bottom: 0; }
.appointment-row strong, .appointment-row span { display: block; }
.appointment-row span { margin-top: 5px; color: var(--slate); font-size: 0.8rem; }
.appointment-row-actions { display: flex; align-items: center; gap: 8px; }
.appointment-row-actions :deep(.v-chip) { border-radius: 4px; }
.appointment-status { display: inline-flex; align-items: center; gap: 6px; color: var(--slate); font-size: 0.76rem; white-space: nowrap; }
.appointment-status i { width: 7px; height: 7px; border-radius: 50%; background: var(--slate); }
.appointment-status--confirmed i { background: var(--steel-blue); }
.appointment-status--completed i { background: var(--navy); }
.appointment-status--cancelled i, .appointment-status--no_show i { background: var(--slate); }
.appointment-menu-button { min-width: 40px; color: var(--slate); }
.no-show-button, .cancel-appointment-button { display: none !important; }
.swipe-hint { display: block; margin-top: 8px; color: var(--slate); font-size: 0.72rem; font-weight: 400; }
@media (min-width: 601px) { .swipe-hint { display: none; } }
.cancel-appointment-button { border-color: var(--surface-slate-border) !important; border-radius: 4px !important; color: var(--slate) !important; text-transform: none; }
.no-show-button { border-color: var(--surface-steel-blue-border-strong) !important; border-radius: 4px !important; color: var(--navy) !important; text-transform: none; }
.complete-button { border-color: var(--surface-navy-strong-border) !important; border-radius: 4px !important; color: var(--navy) !important; text-transform: none; }
.manual-panel { height: 100%; }
.manual-panel .section-kicker { color: var(--steel-blue); }
.manual-slots { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: -4px 0 20px; }
.manual-slot { border-color: var(--surface-paper-outline) !important; border-radius: 4px !important; color: var(--paper) !important; }
.manual-slot--selected { border-color: var(--steel-blue) !important; background: var(--steel-blue) !important; }
.manual-slots .empty-slots { grid-column: 1 / -1; min-height: 48px; font-size: 0.78rem; }
.admin-section + .admin-section { margin-top: 24px; }
.loading-line { margin: 24px 0; }
.service-row, .day-row { padding: 16px 0; border-bottom: 1px solid var(--hairline); transition: background-color var(--motion-fast); }
.service-row:hover, .day-row:hover { background: var(--surface-steel-blue-soft); }
.service-row:last-child { border-bottom: 0; }
.service-row strong, .service-row span { display: block; }
.service-row span { margin-top: 5px; color: var(--slate); font-size: 0.82rem; }
.service-row--inactive { opacity: 0.58; }
.customer-search { margin: 24px 0 8px; }
.customer-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--hairline); transition: background-color var(--motion-fast); }
.customer-row:hover { background: var(--surface-steel-blue-soft); }
.customer-row:last-child { border-bottom: 0; }
.customer-row strong, .customer-row span { display: block; }
.customer-row span { margin-top: 5px; color: var(--slate); font-size: 0.82rem; }
.customer-row--inactive { opacity: 0.58; }
.row-actions { display: flex; align-items: center; gap: 4px; }
.row-actions :deep(.v-chip) { border-radius: 4px; }
.day-row { align-items: flex-start; flex-wrap: wrap; }
.day-label { min-width: 130px; padding-top: 12px; }
.day-period { display: flex; flex: 1 1 330px; align-items: center; gap: 8px; }
.day-period :deep(.v-checkbox) { min-width: 92px; }
.day-period :deep(.v-input) { max-width: 120px; }
.day-separator { color: var(--slate); font-size: 0.8rem; }
.save-button { min-height: 46px; margin-top: 20px; border-radius: var(--radius-sm) !important; background: var(--steel-blue) !important; color: var(--paper) !important; text-transform: none; transition: transform var(--motion-fast), background-color var(--motion-fast); }
.save-button:hover { background: var(--color-steel-blue-hover) !important; }
.save-button:active { transform: scale(0.98); }
.logout-button { color: var(--steel-blue); text-transform: none; }
.empty-state { padding: 32px 0; color: var(--slate); }
.exception-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 0; border-bottom: 1px solid var(--hairline); }
.exception-row:last-child { border-bottom: 0; }
.exception-row strong, .exception-row span { display: block; }
.exception-row span { margin-top: 4px; color: var(--slate); font-size: 0.8rem; }
.settings-panel--dark .exception-row { border-color: var(--hairline-dark); }
.settings-panel--dark .exception-row strong { color: var(--paper); }
.confirmation-dialog { border: 1px solid var(--hairline) !important; border-radius: 8px !important; background: var(--paper) !important; }
.confirmation-dialog .v-card-title { color: var(--ink); font-family: 'Instrument Serif', serif; font-size: 1.7rem; font-weight: 400; }
.confirmation-dialog .v-card-text { color: var(--slate); }

/* Painel premium: navegação lateral no desktop e superfície escura consistente. */
.admin-content {
  min-height: calc(100dvh - 64px);
  background: var(--color-ink);
  color: var(--color-paper);
}
.admin-container { max-width: 1440px; }
.admin-intro h1, .section-heading h2, .form-panel h2, .settings-panel h2 { color: var(--color-paper); }
.admin-intro p:not(.section-kicker), .metric-card span, .metric-card small { color: var(--color-slate); }
.admin-navigation { background: var(--color-navy-deep); border-color: rgba(var(--color-slate-rgb), 0.22); }
.admin-navigation::before { content: 'Sistema Barbearia'; display: none; color: var(--color-paper); font-family: var(--font-display); font-size: 1.25rem; }
.admin-nav-item { color: var(--color-paper); }
.admin-nav-item:hover, .admin-nav-item--active { color: var(--color-paper); background: rgba(var(--color-steel-blue-rgb), 0.16); }
.admin-section, .metric-card, .insight-panel, .settings-panel { background: var(--color-navy-deep); border-color: rgba(var(--color-slate-rgb), 0.24); }
.admin-section:hover, .metric-card:hover { border-color: rgba(var(--color-steel-blue-rgb), 0.6); }
.dashboard-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 16px; }
.dashboard-toolbar h2 { margin: 0; color: var(--color-paper); font-family: var(--font-display); font-size: 2rem; font-weight: 400; line-height: 1; }
.period-toggle { border: 1px solid rgba(var(--color-slate-rgb), 0.28); background: var(--color-navy-deep); }
.period-toggle :deep(.v-btn) { min-height: 40px; color: var(--color-slate); text-transform: none; }
.period-toggle :deep(.v-btn--active) { background: var(--color-steel-blue); color: var(--color-paper); }
.metric-card strong, .insight-heading h2, .insight-bar-label, .status-summary strong { color: var(--color-paper); }
.metric-card--accent { background: rgba(var(--color-steel-blue-rgb), 0.16); }
.metric-card--cancelled { background: rgba(var(--color-slate-rgb), 0.12); }
.service-row:hover, .customer-row:hover, .day-row:hover { background: rgba(var(--color-steel-blue-rgb), 0.1); }
.service-row strong, .customer-row strong, .day-row strong, .appointment-row strong, .exception-row strong { color: var(--color-paper); }
.appointment-row { border-color: rgba(var(--color-paper-rgb), 0.14); }
.appointment-row span, .service-row span, .customer-row span, .exception-row span { color: var(--color-slate); }
.filter-bar :deep(.v-field), .manual-panel :deep(.v-field), .settings-panel--dark :deep(.v-field) { background: rgba(var(--color-ink-rgb), 0.34); }
.filter-bar :deep(input), .filter-bar :deep(.v-label), .manual-panel :deep(input), .manual-panel :deep(.v-label), .settings-panel--dark :deep(input), .settings-panel--dark :deep(.v-label) { color: var(--color-paper); }
.insight-panel--heatmap { background: var(--color-navy-deep); }
.upcoming-panel { margin-top: 12px; padding: 20px; border: 1px solid rgba(var(--color-slate-rgb), 0.24); background: var(--color-navy-deep); }
.upcoming-row { display: grid; grid-template-columns: 72px minmax(0, 1fr) auto auto; align-items: center; gap: 16px; padding: 14px 0; border-top: 1px solid rgba(var(--color-paper-rgb), 0.12); }
.upcoming-time { color: var(--color-steel-blue); font-size: 1.15rem; font-weight: 600; }
.upcoming-main strong, .upcoming-main span { display: block; }
.upcoming-main strong { color: var(--color-paper); font-size: 0.9rem; }
.upcoming-main span { margin-top: 4px; overflow: hidden; color: var(--color-slate); font-size: 0.78rem; text-overflow: ellipsis; white-space: nowrap; }
.upcoming-price { color: var(--color-paper); font-size: 0.85rem; }

@media (min-width: 961px) {
  .admin-container { padding-left: 248px; }
  .admin-navigation {
    position: fixed;
    z-index: 4;
    top: 64px;
    bottom: 0;
    left: 0;
    display: flex;
    width: 224px;
    flex-direction: column;
    gap: 6px;
    margin: 0;
    padding: 18px 12px;
    border-width: 0 1px 0 0;
    background: var(--color-navy-deep);
  }
  .admin-navigation::before { display: block; margin: 2px 14px 22px; }
  .admin-nav-item { justify-content: flex-start; min-height: 46px; padding: 0 14px; border-radius: var(--radius-sm); }
  .admin-nav-item--active { box-shadow: inset 3px 0 0 var(--color-steel-blue); }
}

@media (max-width: 960px) {
  .admin-content { background: var(--color-ink); }
  .admin-navigation { background: var(--color-navy-deep); }
  .admin-section, .form-panel, .metric-card, .insight-panel, .settings-panel { background: var(--color-navy-deep); }
  .admin-navigation::before { display: none; }
}
@media (max-width: 960px) { .form-panel { position: static; } .metrics-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .admin-content { padding: 28px 12px 100px; } .admin-intro { margin-bottom: 24px; } .admin-intro h1 { font-size: 2.25rem; } .admin-section, .form-panel, .insight-panel, .upcoming-panel { padding: 18px; } .dashboard-toolbar { align-items: flex-start; flex-direction: column; } .dashboard-toolbar h2 { font-size: 1.75rem; } .period-toggle { width: 100%; } .period-toggle :deep(.v-btn) { flex: 1; min-width: 0; padding-inline: 6px; font-size: 0.74rem; } .admin-navigation { position: fixed; z-index: 10; right: 0; bottom: 0; left: 0; display: flex; width: auto; grid-template-columns: none; gap: 2px; margin: 0; padding: 6px max(6px, env(safe-area-inset-left)) max(6px, env(safe-area-inset-bottom)); overflow-x: auto; border-width: 1px 0 0; } .admin-nav-item { min-width: 88px; min-height: 56px; flex: 0 0 88px; flex-direction: column; gap: 2px; padding-inline: 4px; font-size: 0.66rem; } .admin-nav-item .v-icon { display: block; } .admin-nav-item--active { box-shadow: inset 0 3px 0 var(--color-steel-blue); } .service-row { align-items: flex-start; flex-direction: column; } .row-actions { width: 100%; justify-content: flex-end; } .day-label { min-width: 100%; } .day-period { flex-basis: 100%; } .day-period :deep(.v-input) { flex: 1; } .metrics-grid, .filter-bar, .dashboard-insights { grid-template-columns: 1fr; } .insight-panel--heatmap { grid-column: auto; } .upcoming-row { grid-template-columns: 56px minmax(0, 1fr) auto; gap: 10px; } .upcoming-row .appointment-status { grid-column: 2; } .upcoming-price { grid-column: 3; grid-row: 1 / span 2; } .appointment-row { align-items: flex-start; flex-direction: column; } .appointment-row-actions { width: 100%; justify-content: space-between; } .manual-slots { grid-template-columns: repeat(3, 1fr); } }
</style>
