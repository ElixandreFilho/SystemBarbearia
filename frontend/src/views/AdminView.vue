<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import type { ApexOptions } from "apexcharts";
import ApexChart from "vue3-apexcharts";

import { apiRequest } from "../services/api";
import { useAuthStore } from "../stores/auth";
import type { User } from "../types/auth";
import { useAutoDismiss } from "../composables/useAutoDismiss";

interface Service {
  id: string;
  name: string;
  description: string | null;
  price_cents: number;
  duration_minutes: number;
  is_active: boolean;
}

interface BusinessHour {
  id?: string;
  weekday: number;
  start_time: string;
  end_time: string;
}

interface SpecialDate {
  id: string;
  date: string;
  is_closed: boolean;
  custom_open_time: string | null;
  custom_close_time: string | null;
  label: string | null;
}

interface BlockedSlot {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  reason: string | null;
}

interface Customer {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
}

interface AdminAppointment {
  id: string;
  customer_id: string;
  customer_name: string;
  service_names: string[];
  service_ids?: string[];
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  total_price_cents: number;
  total_duration_minutes: number;
  notes: string | null;
  possible_no_show: boolean;
}

interface ReorderPreview {
  date: string;
  orderedIds: string[];
  moved: AdminAppointment;
  fromTime: string;
  toTime: string;
  affected: {
    appointment: AdminAppointment;
    fromTime: string;
    toTime: string;
  }[];
}

interface DashboardStats {
  total_appointments: number;
  confirmed_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  total_revenue_cents: number;
  popular_services: { name: string; bookings: number }[];
}

interface ShopSettings {
  id: number;
  name: string;
  timezone: string;
  capacity: number;
  booking_window_days: number;
  min_cancellation_notice_minutes: number;
  no_show_grace_minutes: number;
  slot_granularity_minutes: number;
}

interface DayForm {
  weekday: number;
  label: string;
  morningEnabled: boolean;
  morningStart: string;
  morningEnd: string;
  afternoonEnabled: boolean;
  afternoonStart: string;
  afternoonEnd: string;
}

const router = useRouter();
const auth = useAuthStore();
const services = ref<Service[]>([]);
const customers = ref<Customer[]>([]);
const appointments = ref<AdminAppointment[]>([]);
const specialDates = ref<SpecialDate[]>([]);
const blockedSlots = ref<BlockedSlot[]>([]);
const stats = ref<DashboardStats | null>(null);
const chartAppointments = ref<AdminAppointment[]>([]);
const loadingCharts = ref(false);
const days = ref<DayForm[]>([
  {
    weekday: 0,
    label: "Segunda-feira",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "18:00",
  },
  {
    weekday: 1,
    label: "Terça-feira",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "18:00",
  },
  {
    weekday: 2,
    label: "Quarta-feira",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "18:00",
  },
  {
    weekday: 3,
    label: "Quinta-feira",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "18:00",
  },
  {
    weekday: 4,
    label: "Sexta-feira",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "18:00",
  },
  {
    weekday: 5,
    label: "Sábado",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "14:00",
  },
  {
    weekday: 6,
    label: "Domingo",
    morningEnabled: false,
    morningStart: "09:00",
    morningEnd: "12:00",
    afternoonEnabled: false,
    afternoonStart: "14:00",
    afternoonEnd: "14:00",
  },
]);
const form = ref({
  id: "",
  name: "",
  description: "",
  price: "",
  duration: "30",
});
const loading = ref(true);
const saving = ref(false);
const savingHours = ref(false);
const loadingAppointments = ref(false);
const creatingAppointment = ref(false);
const adminSection = ref("appointments");
const moreMenuOpen = ref(false);
const calendarDate = ref(formatDate(new Date()));
const clientsPanelOpen = ref(false);
const appointmentsListView = ref(true);
const manualPanelRef = ref<HTMLElement | null>(null);
const appointmentServiceFilter = ref("");
const draggedAppointmentId = ref<string | null>(null);
const dragOverAppointmentId = ref<string | null>(null);
const reorderPreview = ref<ReorderPreview | null>(null);
const savingReorder = ref(false);
const shopSettings = ref<ShopSettings | null>(null);
const settingsForm = ref({
  name: "",
  timezone: "",
  capacity: "2",
  booking_window_days: "2",
  min_cancellation_notice_minutes: "60",
  no_show_grace_minutes: "30",
  slot_granularity_minutes: "30",
});
const profileForm = ref({
  full_name: auth.user?.full_name ?? "",
  email: auth.user?.email ?? "",
  phone: auth.user?.phone ?? "",
  password: "",
});
const savingSettings = ref(false);
const savingProfile = ref(false);
const savingCustomer = ref(false);
const customerSearch = ref("");
const customerForm = ref({
  id: "",
  full_name: "",
  email: "",
  phone: "",
  password: "",
});
const savingException = ref(false);
const specialDateForm = ref({
  date: formatDate(new Date()),
  label: "",
  is_closed: true,
  custom_open_time: "",
  custom_close_time: "",
});
const blockedSlotForm = ref({
  date: formatDate(new Date()),
  start_time: "12:00",
  end_time: "14:00",
  reason: "",
});
const filterDate = ref(formatDate(new Date()));
const filterStatus = ref("");
const dashboardPeriod = ref<"today" | "7d" | "30d" | "all">("30d");
const manualDate = ref(formatDate(new Date()));
const manualCustomerId = ref("");
const manualServiceIds = ref<string[]>([]);
const manualSlot = ref("");
const manualSlots = ref<string[]>([]);
const manualNotes = ref("");
const editingAppointmentId = ref<string | null>(null);
const appointmentDialog = ref<AdminAppointment | null>(null);
const appointmentDialogOpen = ref(false);
const appointmentDialogEditMode = ref(false);
const reschedulePreview = ref<{
  appointment: AdminAppointment;
  date: string;
  time: string;
} | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
useAutoDismiss([errorMessage, successMessage]);
const swipeStartX = ref<number | null>(null);
const swipeAppointmentId = ref<string | null>(null);
const swipeOffset = ref(0);
const pendingAction = ref<{
  type: "complete" | "cancel";
  appointment: AdminAppointment;
} | null>(null);
const processingAction = ref(false);
const token = () => auth.accessToken ?? undefined;
const requiredRule = (value: unknown) =>
  Boolean(String(value ?? "").trim()) || "Campo obrigatório";
const positiveNumberRule = (value: unknown) =>
  Number(value) > 0 || "Informe um valor válido";

const primaryNavItems = [
  {
    key: "appointments",
    label: "Agendamentos",
    icon: "mdi-calendar-month-outline",
  },
  { key: "dashboard", label: "Dashboard", icon: "mdi-view-dashboard-outline" },
  { key: "customers", label: "Clientes", icon: "mdi-account-group-outline" },
  { key: "services", label: "Serviços", icon: "mdi-content-cut" },
];
const moreNavItems = [
  { key: "hours", label: "Horários", icon: "mdi-clock-outline" },
  { key: "exceptions", label: "Exceções", icon: "mdi-calendar-alert-outline" },
  { key: "settings", label: "Configurações", icon: "mdi-cog-outline" },
];

const editing = () => Boolean(form.value.id);
const activeServices = () =>
  services.value.filter((service) => service.is_active);
const serviceOptionTitle = (service: Service) =>
  `${service.name} · ${formatMoney(service.price_cents)}`;
const filteredCustomers = computed(() => {
  const query = customerSearch.value.trim().toLowerCase();
  if (!query) return customers.value;
  return customers.value.filter((customer) =>
    [customer.full_name, customer.email, customer.phone].some((value) =>
      value?.toLowerCase().includes(query),
    ),
  );
});
const visibleAppointments = computed(() => {
  const filtered = !appointmentServiceFilter.value
    ? appointments.value
    : appointments.value.filter((appointment) =>
    appointment.service_names.includes(appointmentServiceFilter.value),
  );
  return [...filtered].sort(
    (a, b) => Number(a.status === "CANCELLED") - Number(b.status === "CANCELLED"),
  );
});
const activeCalendarStatuses = ["PENDING", "CONFIRMED", "COMPLETED", "NO_SHOW"];

const calendarDays = computed(() => {
  const base = new Date(`${calendarDate.value}T12:00:00`);
  const mondayOffset = (base.getDay() + 6) % 7;
  base.setDate(base.getDate() - mondayOffset);
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(base);
    date.setDate(base.getDate() + index);
    const key = formatDate(date);
    return {
      key,
      day: date
        .toLocaleDateString("pt-BR", { weekday: "short" })
        .replace(".", ""),
      number: date.getDate(),
      month: date
        .toLocaleDateString("pt-BR", { month: "short" })
        .replace(".", ""),
      isToday: key === formatDate(new Date()),
    };
  });
});
const calendarTimes = computed(() =>
  Array.from({ length: 24 }, (_, index) => {
    const minutes = 7 * 60 + index * 30;
    return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
  }),
);
const calendarRangeLabel = computed(() => {
  const first = calendarDays.value[0];
  const last = calendarDays.value[6];
  return `${first.number} ${first.month} — ${last.number} ${last.month}`;
});

function shiftCalendar(days: number) {
  const next = new Date(`${calendarDate.value}T12:00:00`);
  next.setDate(next.getDate() + days);
  calendarDate.value = formatDate(next);
  filterDate.value = "";
  loadAppointments();
}

function setAppointmentsView(listView: boolean) {
  appointmentsListView.value = listView;
  filterDate.value = listView ? formatDate(new Date()) : "";
  loadAppointments();
}

async function startNewAppointment() {
  editingAppointmentId.value = null;
  manualCustomerId.value = "";
  manualServiceIds.value = [];
  manualDate.value = appointmentsListView.value
    ? filterDate.value || formatDate(new Date())
    : calendarDate.value;
  manualSlot.value = "";
  manualSlots.value = [];
  manualNotes.value = "";
  await nextTick();
  manualPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function openNewAppointment(date: string, slot: string) {
  appointmentDialog.value = null;
  appointmentDialogEditMode.value = false;
  editingAppointmentId.value = null;
  manualCustomerId.value = "";
  manualServiceIds.value = [];
  manualDate.value = date;
  manualSlot.value = slot;
  manualSlots.value = [slot];
  manualNotes.value = "";
  appointmentDialogOpen.value = true;
}

function openAppointmentDetails(appointment: AdminAppointment) {
  appointmentDialog.value = appointment;
  appointmentDialogEditMode.value = false;
  appointmentDialogOpen.value = true;
}

function editAppointmentFromDialog() {
  if (!appointmentDialog.value) return;
  const appointment = appointmentDialog.value;
  editingAppointmentId.value = appointment.id;
  manualCustomerId.value = appointment.customer_id;
  manualServiceIds.value = [
    ...(appointment.service_names.length
      ? (appointment.service_names
          .map(
            (name) =>
              services.value.find((service) => service.name === name)?.id,
          )
          .filter(Boolean) as string[])
      : []),
  ];
  manualDate.value = appointment.date;
  manualSlot.value = formatTime(appointment.start_time);
  manualSlots.value = [manualSlot.value];
  manualNotes.value = appointment.notes ?? "";
  appointmentDialogEditMode.value = true;
}

function cancelAppointmentDialogEdit() {
  appointmentDialogEditMode.value = false;
  editingAppointmentId.value = null;
}

function appointmentsAt(date: string, time: string) {
  return visibleAppointments.value.filter(
    (appointment) =>
      appointment.date === date &&
      appointment.start_time.slice(0, 5) === time &&
      activeCalendarStatuses.includes(appointment.status),
  );
}

function movableAppointments(date: string) {
  return appointments.value
    .filter(
      (appointment) =>
        appointment.date === date &&
        ["PENDING", "CONFIRMED"].includes(appointment.status),
    )
    .sort((a, b) =>
      `${a.start_time}-${a.id}`.localeCompare(`${b.start_time}-${b.id}`),
    );
}

function prepareReorder(date: string, sourceId: string, targetId: string) {
  const queue = movableAppointments(date);
  const sourceIndex = queue.findIndex((item) => item.id === sourceId);
  const targetIndex = queue.findIndex((item) => item.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
  const slots = queue.map((item) => item.start_time);
  const [moved] = queue.splice(sourceIndex, 1);
  queue.splice(targetIndex, 0, moved);
  const affected = queue
    .map((appointment, index) => ({
      appointment,
      fromTime: appointment.start_time,
      toTime: slots[index],
    }))
    .filter(
      (item) =>
        item.fromTime !== item.toTime && item.appointment.id !== moved.id,
    );
  reorderPreview.value = {
    date,
    orderedIds: queue.map((item) => item.id),
    moved,
    fromTime: slots[sourceIndex],
    toTime: slots[targetIndex],
    affected,
  };
}

function startAppointmentDrag(event: DragEvent, appointment: AdminAppointment) {
  if (!["PENDING", "CONFIRMED"].includes(appointment.status)) {
    event.preventDefault();
    return;
  }
  draggedAppointmentId.value = appointment.id;
  dragOverAppointmentId.value = appointment.id;
  event.dataTransfer?.setData("text/plain", appointment.id);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}

function overAppointmentDrag(event: DragEvent, appointment: AdminAppointment) {
  if (
    draggedAppointmentId.value &&
    appointment.date ===
      appointments.value.find((item) => item.id === draggedAppointmentId.value)
        ?.date
  ) {
    event.preventDefault();
    dragOverAppointmentId.value = appointment.id;
  }
}

function dropAppointment(event: DragEvent, appointment: AdminAppointment) {
  event.preventDefault();
  if (draggedAppointmentId.value)
    prepareReorder(
      appointment.date,
      draggedAppointmentId.value,
      appointment.id,
    );
  draggedAppointmentId.value = null;
  dragOverAppointmentId.value = null;
}

function overCalendarCell(event: DragEvent) {
  if (draggedAppointmentId.value) event.preventDefault();
}

function dropCalendarCell(event: DragEvent, date: string, time: string) {
  event.preventDefault();
  const appointment = appointments.value.find(
    (item) => item.id === draggedAppointmentId.value,
  );
  if (
    appointment &&
    (appointment.date !== date ||
      appointment.start_time.slice(0, 5) !== time) &&
    !appointmentsAt(date, time).length
  ) {
    reschedulePreview.value = { appointment, date, time };
  }
  endAppointmentDrag();
}

async function confirmReschedule() {
  if (!reschedulePreview.value) return;
  const preview = reschedulePreview.value;
  savingReorder.value = true;
  try {
    await apiRequest<AdminAppointment>(
      `/admin/appointments/${preview.appointment.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          date: preview.date,
          start_time: preview.time,
          service_ids: preview.appointment.service_ids?.length
            ? preview.appointment.service_ids
            : preview.appointment.service_names
                .map(
                  (name) =>
                    services.value.find((service) => service.name === name)?.id,
                )
                .filter((id): id is string => Boolean(id)),
          notes: preview.appointment.notes ?? undefined,
        }),
      },
      token(),
    );
    successMessage.value = `${preview.appointment.customer_name} foi realocado para ${preview.time}.`;
    reschedulePreview.value = null;
    await loadAppointments();
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível realocar o agendamento.";
  } finally {
    savingReorder.value = false;
  }
}

function endAppointmentDrag() {
  draggedAppointmentId.value = null;
  dragOverAppointmentId.value = null;
}

function prepareAccessibleMove(
  appointment: AdminAppointment,
  direction: -1 | 1,
) {
  const queue = movableAppointments(appointment.date);
  const index = queue.findIndex((item) => item.id === appointment.id);
  const target = queue[index + direction];
  if (target) prepareReorder(appointment.date, appointment.id, target.id);
}

async function confirmReorder() {
  if (!reorderPreview.value || savingReorder.value) return;
  savingReorder.value = true;
  try {
    const updated = await apiRequest<AdminAppointment[]>(
      "/admin/appointments/reorder",
      {
        method: "POST",
        body: JSON.stringify({
          date: reorderPreview.value.date,
          appointment_ids: reorderPreview.value.orderedIds,
        }),
      },
      token(),
    );
    const updatedById = new Map(
      updated.map((appointment) => [appointment.id, appointment]),
    );
    appointments.value = appointments.value.map(
      (appointment) => updatedById.get(appointment.id) ?? appointment,
    );
    successMessage.value = "Ordem dos agendamentos atualizada.";
    reorderPreview.value = null;
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível reorganizar os agendamentos.";
    await loadAppointments();
  } finally {
    savingReorder.value = false;
  }
}

function openCustomerBooking(customer: Customer) {
  manualCustomerId.value = customer.id;
  manualDate.value = calendarDate.value;
  clientsPanelOpen.value = false;
  adminSection.value = "appointments";
}

const serviceChartSeries = computed(() =>
  (stats.value?.popular_services ?? []).map((service) => service.bookings),
);
const serviceChartLabels = computed(() =>
  (stats.value?.popular_services ?? []).map((service) => service.name),
);
const statusChartSeries = computed(() => [
  stats.value?.confirmed_appointments ?? 0,
  stats.value?.completed_appointments ?? 0,
  stats.value?.cancelled_appointments ?? 0,
]);
const serviceChartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: "donut",
    toolbar: { show: false },
    fontFamily: "Manrope, sans-serif",
  },
  labels: serviceChartLabels.value,
  colors: [
    "var(--color-steel-blue)",
    "var(--color-navy)",
    "var(--color-slate)",
    "var(--color-navy-deep)",
    "var(--color-paper)",
  ],
  dataLabels: { enabled: false },
  legend: {
    position: "bottom",
    fontFamily: "Manrope, sans-serif",
    labels: { colors: "var(--color-paper)" },
  },
  stroke: { colors: ["var(--color-navy-deep)"] },
  plotOptions: {
    pie: {
      donut: {
        size: "66%",
        labels: {
          show: true,
          total: {
            show: true,
            label: "Agendamentos",
            color: "var(--color-slate)",
          },
        },
      },
    },
  },
  tooltip: { theme: "dark" },
}));
const statusChartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: "donut",
    toolbar: { show: false },
    fontFamily: "Manrope, sans-serif",
  },
  labels: ["Confirmados", "Concluídos", "Cancelados"],
  colors: [
    "var(--color-steel-blue)",
    "var(--color-navy)",
    "var(--color-slate)",
  ],
  dataLabels: { enabled: false },
  legend: {
    position: "bottom",
    fontFamily: "Manrope, sans-serif",
    labels: { colors: "var(--color-paper)" },
  },
  stroke: { colors: ["var(--color-navy-deep)"] },
  plotOptions: {
    pie: {
      donut: {
        size: "66%",
        labels: {
          show: true,
          total: { show: true, label: "Status", color: "var(--color-slate)" },
        },
      },
    },
  },
  tooltip: { theme: "dark" },
}));
const heatmapSeries = computed(() => {
  const counts = new Map<string, number>();
  chartAppointments.value.forEach((appointment) => {
    if (appointment.status !== "CANCELLED")
      counts.set(appointment.date, (counts.get(appointment.date) ?? 0) + 1);
  });
  const days = Array.from({ length: 30 }, (_, index) => {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() - (29 - index));
    const key = formatDate(date);
    return {
      x: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      y: counts.get(key) ?? 0,
    };
  });
  return [{ name: "Atendimentos", data: days }];
});
const heatmapChartOptions = computed<ApexOptions>(() => ({
  chart: {
    type: "heatmap",
    toolbar: { show: false },
    fontFamily: "Manrope, sans-serif",
  },
  dataLabels: { enabled: false },
  colors: ["var(--color-steel-blue)"],
  plotOptions: {
    heatmap: {
      radius: 2,
      shadeIntensity: 0.55,
      colorScale: {
        ranges: [
          {
            from: 0,
            to: 0,
            color: "rgba(var(--color-slate-rgb), 0.12)",
            name: "Sem atendimentos",
          },
        ],
      },
    },
  },
  legend: { show: false },
  xaxis: {
    labels: {
      style: {
        colors: "var(--color-slate)",
        fontFamily: "Manrope, sans-serif",
      },
    },
  },
  tooltip: { y: { formatter: (value) => `${value} atendimento(s)` } },
}));

function formatMoney(cents: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(cents / 100);
}

function resetForm() {
  form.value = { id: "", name: "", description: "", price: "", duration: "30" };
}

function selectAdminSection(section: string) {
  adminSection.value = section;
  moreMenuOpen.value = false;
}

function editService(service: Service) {
  form.value = {
    id: service.id,
    name: service.name,
    description: service.description ?? "",
    price: (service.price_cents / 100).toFixed(2).replace(".", ","),
    duration: String(service.duration_minutes),
  };
}

function resetCustomerForm() {
  customerForm.value = {
    id: "",
    full_name: "",
    email: "",
    phone: "",
    password: "",
  };
}

function editCustomer(customer: Customer) {
  customerForm.value = {
    id: customer.id,
    full_name: customer.full_name,
    email: customer.email ?? "",
    phone: customer.phone ?? "",
    password: "",
  };
}

async function saveCustomer() {
  errorMessage.value = "";
  if (!customerForm.value.full_name.trim()) {
    errorMessage.value = "Informe o nome completo do cliente.";
    return;
  }
  if (!customerForm.value.id && customerForm.value.password.length < 8) {
    errorMessage.value =
      "A senha temporária precisa ter pelo menos 8 caracteres.";
    return;
  }
  if (customerForm.value.password && customerForm.value.password.length < 8) {
    errorMessage.value = "A nova senha precisa ter pelo menos 8 caracteres.";
    return;
  }
  savingCustomer.value = true;
  try {
    const payload: Record<string, string> = {
      full_name: customerForm.value.full_name.trim(),
    };
    if (customerForm.value.email.trim())
      payload.email = customerForm.value.email.trim();
    if (customerForm.value.phone.trim())
      payload.phone = customerForm.value.phone.trim();
    if (customerForm.value.password)
      payload.password = customerForm.value.password;
    const saved = await apiRequest<Customer>(
      customerForm.value.id
        ? `/admin/customers/${customerForm.value.id}`
        : "/admin/customers",
      {
        method: customerForm.value.id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      },
      token(),
    );
    customers.value = customerForm.value.id
      ? customers.value.map((customer) =>
          customer.id === saved.id ? saved : customer,
        )
      : [saved, ...customers.value];
    successMessage.value = customerForm.value.id
      ? "Cliente atualizado."
      : "Cliente cadastrado.";
    resetCustomerForm();
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível salvar o cliente.";
  } finally {
    savingCustomer.value = false;
  }
}

async function deactivateCustomer(customer: Customer) {
  if (!window.confirm(`Desativar o cadastro de ${customer.full_name}?`)) return;
  try {
    await apiRequest<void>(
      `/admin/customers/${customer.id}`,
      { method: "DELETE" },
      token(),
    );
    customer.is_active = false;
    customers.value = [...customers.value];
    successMessage.value = "Cliente desativado.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível desativar o cliente.";
  }
}

async function loadAdminData() {
  loading.value = true;
  try {
    const [
      serviceData,
      hourData,
      customerData,
      settingsData,
      specialData,
      blockedData,
    ] = await Promise.all([
      apiRequest<Service[]>("/admin/services", {}, token()),
      apiRequest<BusinessHour[]>("/admin/business-hours", {}, token()),
      apiRequest<Customer[]>("/admin/customers?limit=100", {}, token()),
      apiRequest<ShopSettings>("/admin/settings", {}, token()),
      apiRequest<SpecialDate[]>("/admin/special-dates", {}, token()),
      apiRequest<BlockedSlot[]>("/admin/blocked-slots", {}, token()),
    ]);
    services.value = serviceData;
    customers.value = customerData;
    specialDates.value = specialData;
    blockedSlots.value = blockedData;
    shopSettings.value = settingsData;
    settingsForm.value = {
      name: settingsData.name,
      timezone: settingsData.timezone,
      capacity: String(settingsData.capacity),
      booking_window_days: String(settingsData.booking_window_days),
      min_cancellation_notice_minutes: String(
        settingsData.min_cancellation_notice_minutes,
      ),
      no_show_grace_minutes: String(settingsData.no_show_grace_minutes),
      slot_granularity_minutes: String(settingsData.slot_granularity_minutes),
    };
    hourData.forEach((hour) => {
      const day = days.value.find((item) => item.weekday === hour.weekday);
      if (day) {
        const start = hour.start_time.slice(0, 5);
        const end = hour.end_time.slice(0, 5);
        if (start < "14:00") {
          day.morningEnabled = true;
          day.morningStart = start;
          day.morningEnd = end;
        } else {
          day.afternoonEnabled = true;
          day.afternoonStart = start;
          day.afternoonEnd = end;
        }
      }
    });
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar a área administrativa.";
  } finally {
    loading.value = false;
  }
}

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatTime(value: string) {
  return value.slice(0, 5);
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING: "Pendente",
    CONFIRMED: "Confirmado",
    COMPLETED: "Concluído",
    CANCELLED: "Cancelado",
    NO_SHOW: "Não compareceu",
  };
  return labels[status] ?? status;
}

function statusColor(status: string) {
  return status === "CANCELLED" || status === "NO_SHOW"
    ? "slate"
    : "steel-blue";
}

async function loadAppointments() {
  loadingAppointments.value = true;
  try {
    const query = new URLSearchParams();
    if (filterDate.value) query.set("date", filterDate.value);
    if (filterStatus.value) query.set("status", filterStatus.value);
    appointments.value = await apiRequest<AdminAppointment[]>(
      `/admin/appointments?${query.toString()}`,
      {},
      token(),
    );
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar os agendamentos.";
  } finally {
    loadingAppointments.value = false;
  }
}

async function loadStats() {
  try {
    const query = new URLSearchParams();
    if (dashboardPeriod.value !== "all") {
      const start = new Date();
      start.setHours(12, 0, 0, 0);
      if (dashboardPeriod.value === "7d") start.setDate(start.getDate() - 6);
      if (dashboardPeriod.value === "30d") start.setDate(start.getDate() - 29);
      query.set("from", formatDate(start));
      query.set("to", formatDate(new Date()));
    }
    stats.value = await apiRequest<DashboardStats>(
      `/admin/appointments/dashboard${query.toString() ? `?${query.toString()}` : ""}`,
      {},
      token(),
    );
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar os indicadores.";
  }
}

async function loadChartAppointments() {
  loadingCharts.value = true;
  try {
    chartAppointments.value = await apiRequest<AdminAppointment[]>(
      "/admin/appointments",
      {},
      token(),
    );
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar os dados dos gráficos.";
  } finally {
    loadingCharts.value = false;
  }
}

async function loadManualSlots() {
  const requestedSlot = manualSlot.value;
  manualSlot.value = "";
  manualSlots.value = [];
  if (!manualDate.value || !manualServiceIds.value.length) return;
  try {
    const query = new URLSearchParams({ date: manualDate.value });
    manualServiceIds.value.forEach((id) => query.append("service_ids", id));
    const availability = await apiRequest<{ slots: string[] }>(
      `/availability?${query.toString()}`,
      {},
      token(),
    );
    manualSlots.value = [
      ...new Set([
        ...availability.slots,
        ...(appointmentDialogOpen.value && !appointmentDialog.value && requestedSlot
          ? [requestedSlot]
          : []),
      ]),
    ];
    if (appointmentDialogOpen.value && !appointmentDialog.value && requestedSlot) {
      manualSlot.value = requestedSlot;
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível consultar os horários.";
  }
}

async function createManualAppointment() {
  if (
    !manualCustomerId.value ||
    !manualServiceIds.value.length ||
    !manualSlot.value
  ) {
    errorMessage.value = "Selecione cliente, serviço e horário para continuar.";
    return false;
  }
  creatingAppointment.value = true;
  try {
    const isEditing = Boolean(editingAppointmentId.value);
    await apiRequest<AdminAppointment>(
      isEditing
        ? `/admin/appointments/${editingAppointmentId.value}`
        : "/admin/appointments",
      {
        method: isEditing ? "PATCH" : "POST",
        body: JSON.stringify({
          customer_id: manualCustomerId.value,
          date: manualDate.value,
          start_time: manualSlot.value,
          service_ids: manualServiceIds.value,
          notes: manualNotes.value.trim() || undefined,
        }),
      },
      token(),
    );
    successMessage.value = isEditing
      ? "Agendamento atualizado."
      : "Agendamento criado para o cliente.";
    editingAppointmentId.value = null;
    manualSlot.value = "";
    manualNotes.value = "";
    await Promise.all([loadAppointments(), loadStats(), loadManualSlots()]);
    return true;
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível criar o agendamento.";
    return false;
  } finally {
    creatingAppointment.value = false;
  }
}

async function submitAppointmentDialog() {
  const saved = await createManualAppointment();
  if (saved) appointmentDialogOpen.value = false;
}

async function cancelAdminAppointment(appointment: AdminAppointment) {
  pendingAction.value = { type: "cancel", appointment };
}

async function completeAppointment(appointment: AdminAppointment) {
  pendingAction.value = { type: "complete", appointment };
}

async function confirmPendingAction() {
  if (!pendingAction.value) return;
  const action = pendingAction.value;
  pendingAction.value = null;
  processingAction.value = true;
  try {
    if (action.type === "cancel") {
      await apiRequest<AdminAppointment>(
        `/admin/appointments/${action.appointment.id}/cancel`,
        {
          method: "PATCH",
          body: JSON.stringify({ reason: "Cancelado pelo administrador" }),
        },
        token(),
      );
      successMessage.value = "Agendamento cancelado.";
    } else {
      await apiRequest<AdminAppointment>(
        `/admin/appointments/${action.appointment.id}/complete`,
        { method: "PATCH" },
        token(),
      );
      successMessage.value = "Atendimento concluído.";
    }
    await Promise.all([loadAppointments(), loadStats()]);
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível atualizar o agendamento.";
  } finally {
    processingAction.value = false;
  }
}

async function deleteCancelledAppointment(appointment: AdminAppointment) {
  if (appointment.status !== "CANCELLED") return;
  if (
    !window.confirm(
      `Excluir definitivamente o agendamento cancelado de ${appointment.customer_name}?`,
    )
  )
    return;
  processingAction.value = true;
  try {
    await apiRequest<void>(`/admin/appointments/${appointment.id}`, {
      method: "DELETE",
    }, token());
    successMessage.value = "Agendamento excluÃ­do da lista.";
    await Promise.all([loadAppointments(), loadStats()]);
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "NÃ£o foi possÃ­vel excluir o agendamento.";
  } finally {
    processingAction.value = false;
  }
}

async function markNoShow(appointment: AdminAppointment) {
  if (
    !window.confirm(
      `Confirmar que ${appointment.customer_name} não compareceu ao atendimento?`,
    )
  )
    return;
  try {
    await apiRequest<AdminAppointment>(
      `/admin/appointments/${appointment.id}/no-show`,
      { method: "PATCH" },
      token(),
    );
    successMessage.value = "Agendamento marcado como “Não compareceu”.";
    await Promise.all([loadAppointments(), loadStats()]);
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível atualizar o agendamento.";
  }
}

function beginAppointmentSwipe(
  event: PointerEvent,
  appointment: AdminAppointment,
) {
  if ((event.target as HTMLElement).closest("button, input, select, textarea"))
    return;
  swipeStartX.value = event.clientX;
  swipeAppointmentId.value = appointment.id;
  swipeOffset.value = 0;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
}

function moveAppointmentSwipe(
  event: PointerEvent,
  appointment: AdminAppointment,
) {
  if (swipeStartX.value === null || swipeAppointmentId.value !== appointment.id)
    return;
  const distance = event.clientX - swipeStartX.value;
  swipeOffset.value = Math.max(-140, Math.min(140, distance));
}

async function finishAppointmentSwipe(appointment: AdminAppointment) {
  if (swipeStartX.value === null || swipeAppointmentId.value !== appointment.id)
    return;
  const distance = swipeOffset.value;
  swipeStartX.value = null;
  swipeAppointmentId.value = null;
  swipeOffset.value = 0;
  if (Math.abs(distance) < 90) return;
  if (distance > 0 && appointment.status === "CONFIRMED")
    completeAppointment(appointment);
  if (distance < 0 && ["PENDING", "CONFIRMED"].includes(appointment.status))
    cancelAdminAppointment(appointment);
}

async function saveService() {
  const price = Number(form.value.price.replace(",", "."));
  const duration = Number(form.value.duration);
  if (!form.value.name.trim()) {
    errorMessage.value = "Preencha o nome do serviço.";
    return;
  }
  if (!Number.isFinite(price) || price <= 0) {
    errorMessage.value = "Informe um preço válido para o serviço.";
    return;
  }
  if (!Number.isFinite(duration) || duration <= 0) {
    errorMessage.value = "Informe uma duração válida para o serviço.";
    return;
  }
  saving.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  const payload = {
    name: form.value.name.trim(),
    description: form.value.description.trim() || undefined,
    price_cents: Math.round(price * 100),
    duration_minutes: duration,
  };
  try {
    const saved = await apiRequest<Service>(
      form.value.id ? `/admin/services/${form.value.id}` : "/admin/services",
      {
        method: form.value.id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      },
      token(),
    );
    if (form.value.id) {
      services.value = services.value.map((service) =>
        service.id === saved.id ? saved : service,
      );
    } else {
      services.value = [...services.value, saved].sort((a, b) =>
        a.name.localeCompare(b.name),
      );
    }
    successMessage.value = form.value.id
      ? "Serviço atualizado."
      : "Serviço criado.";
    resetForm();
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível salvar o serviço.";
  } finally {
    saving.value = false;
  }
}

async function deactivateService(service: Service) {
  if (!window.confirm(`Desativar o serviço “${service.name}”?`)) return;
  try {
    await apiRequest<void>(
      `/admin/services/${service.id}`,
      { method: "DELETE" },
      token(),
    );
    service.is_active = false;
    successMessage.value = "Serviço desativado.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível desativar o serviço.";
  }
}

async function saveBusinessHours() {
  savingHours.value = true;
  errorMessage.value = "";
  try {
    const payload = days.value.flatMap((day) => {
      const intervals = [];
      if (day.morningEnabled)
        intervals.push({
          weekday: day.weekday,
          start_time: `${day.morningStart}:00`,
          end_time: `${day.morningEnd}:00`,
        });
      if (day.afternoonEnabled)
        intervals.push({
          weekday: day.weekday,
          start_time: `${day.afternoonStart}:00`,
          end_time: `${day.afternoonEnd}:00`,
        });
      return intervals;
    });
    await apiRequest<BusinessHour[]>(
      "/admin/business-hours",
      { method: "PUT", body: JSON.stringify(payload) },
      token(),
    );
    successMessage.value = "Horários de funcionamento atualizados.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível salvar os horários.";
  } finally {
    savingHours.value = false;
  }
}

async function createSpecialDate() {
  savingException.value = true;
  try {
    const saved = await apiRequest<SpecialDate>(
      "/admin/special-dates",
      {
        method: "POST",
        body: JSON.stringify({
          date: specialDateForm.value.date,
          label: specialDateForm.value.label.trim() || undefined,
          is_closed: specialDateForm.value.is_closed,
          custom_open_time: specialDateForm.value.is_closed
            ? undefined
            : `${specialDateForm.value.custom_open_time}:00`,
          custom_close_time: specialDateForm.value.is_closed
            ? undefined
            : `${specialDateForm.value.custom_close_time}:00`,
        }),
      },
      token(),
    );
    specialDates.value = [...specialDates.value, saved].sort((a, b) =>
      a.date.localeCompare(b.date),
    );
    successMessage.value = "Data especial cadastrada.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível cadastrar a data especial.";
  } finally {
    savingException.value = false;
  }
}

async function removeSpecialDate(item: SpecialDate) {
  if (!window.confirm(`Remover a exceção de ${formatDateLabel(item.date)}?`))
    return;
  try {
    await apiRequest<void>(
      `/admin/special-dates/${item.id}`,
      { method: "DELETE" },
      token(),
    );
    specialDates.value = specialDates.value.filter(
      (entry) => entry.id !== item.id,
    );
    successMessage.value = "Data especial removida.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível remover a data especial.";
  }
}

async function createBlockedSlot() {
  savingException.value = true;
  try {
    const saved = await apiRequest<BlockedSlot>(
      "/admin/blocked-slots",
      {
        method: "POST",
        body: JSON.stringify({
          date: blockedSlotForm.value.date,
          start_time: `${blockedSlotForm.value.start_time}:00`,
          end_time: `${blockedSlotForm.value.end_time}:00`,
          reason: blockedSlotForm.value.reason.trim() || undefined,
        }),
      },
      token(),
    );
    blockedSlots.value = [...blockedSlots.value, saved].sort((a, b) =>
      `${a.date}${a.start_time}`.localeCompare(`${b.date}${b.start_time}`),
    );
    successMessage.value = "Bloqueio de horário cadastrado.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível cadastrar o bloqueio.";
  } finally {
    savingException.value = false;
  }
}

async function removeBlockedSlot(item: BlockedSlot) {
  if (!window.confirm(`Remover o bloqueio de ${formatDateLabel(item.date)}?`))
    return;
  try {
    await apiRequest<void>(
      `/admin/blocked-slots/${item.id}`,
      { method: "DELETE" },
      token(),
    );
    blockedSlots.value = blockedSlots.value.filter(
      (entry) => entry.id !== item.id,
    );
    successMessage.value = "Bloqueio removido.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível remover o bloqueio.";
  }
}

function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(
    new Date(`${value}T12:00:00`),
  );
}

async function saveShopSettings() {
  savingSettings.value = true;
  try {
    const saved = await apiRequest<ShopSettings>(
      "/admin/settings",
      {
        method: "PATCH",
        body: JSON.stringify({
          name: settingsForm.value.name.trim(),
          timezone: settingsForm.value.timezone.trim(),
          capacity: Number(settingsForm.value.capacity),
          booking_window_days: Number(settingsForm.value.booking_window_days),
          min_cancellation_notice_minutes: Number(
            settingsForm.value.min_cancellation_notice_minutes,
          ),
          no_show_grace_minutes: Number(
            settingsForm.value.no_show_grace_minutes,
          ),
          slot_granularity_minutes: Number(
            settingsForm.value.slot_granularity_minutes,
          ),
        }),
      },
      token(),
    );
    shopSettings.value = saved;
    successMessage.value = "Dados da barbearia atualizados.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível salvar as configurações.";
  } finally {
    savingSettings.value = false;
  }
}

async function saveProfile() {
  savingProfile.value = true;
  try {
    const payload: Record<string, string> = {
      full_name: profileForm.value.full_name.trim(),
      email: profileForm.value.email.trim(),
      phone: profileForm.value.phone.trim(),
    };
    if (profileForm.value.password)
      payload.password = profileForm.value.password;
    const updated = await apiRequest<User>(
      "/auth/me",
      { method: "PATCH", body: JSON.stringify(payload) },
      token(),
    );
    auth.user = updated;
    profileForm.value.password = "";
    successMessage.value = "Perfil atualizado.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "Não foi possível atualizar o perfil.";
  } finally {
    savingProfile.value = false;
  }
}

async function logout() {
  await auth.logout();
  await router.push("/login");
}

onMounted(async () => {
  await loadAdminData();
  await Promise.all([loadAppointments(), loadStats(), loadChartAppointments()]);
});
</script>

<template>
  <main class="admin-content">
    <v-container class="admin-container">
      <header class="admin-intro">
        <div>
          <p class="section-kicker">Painel administrativo</p>
          <h1>
            {{
              adminSection === "appointments"
                ? "Agendamentos"
                : "Gestão da barbearia."
            }}
          </h1>
          <p>Configure o catálogo e os horários de atendimento.</p>
        </div>
        <v-btn class="logout-button" variant="text" @click="logout">Sair</v-btn>
      </header>

      <nav class="admin-navigation" aria-label="Navegação administrativa">
        <button
          v-for="item in primaryNavItems"
          :key="item.key"
          class="admin-nav-item"
          :class="{ 'admin-nav-item--active': adminSection === item.key }"
          :aria-current="adminSection === item.key ? 'page' : undefined"
          type="button"
          @click="selectAdminSection(item.key)"
        >
          <v-icon :icon="item.icon" size="19" />
          <span>{{ item.label }}</span>
        </button>
        <button
          class="admin-nav-more"
          type="button"
          :aria-expanded="moreMenuOpen"
          @click="moreMenuOpen = true"
        >
          <v-icon icon="mdi-dots-horizontal" size="19" />
          <span>Mais</span>
        </button>
        <button
          v-for="item in moreNavItems"
          :key="`desktop-${item.key}`"
          class="admin-nav-item admin-nav-item--desktop-only"
          :class="{ 'admin-nav-item--active': adminSection === item.key }"
          :aria-current="adminSection === item.key ? 'page' : undefined"
          type="button"
          @click="selectAdminSection(item.key)"
        >
          <v-icon :icon="item.icon" size="19" />
          <span>{{ item.label }}</span>
        </button>
        <button class="admin-logout-nav" type="button" @click="logout">
          <v-icon icon="mdi-logout-variant" size="19" />
          <span>Sair</span>
        </button>
      </nav>

      <v-alert
        v-if="errorMessage"
        type="error"
        variant="tonal"
        closable
        @click:close="errorMessage = ''"
        >{{ errorMessage }}</v-alert
      >
      <v-alert
        v-if="successMessage"
        type="success"
        variant="tonal"
        closable
        @click:close="successMessage = ''"
        >{{ successMessage }}</v-alert
      >
      <v-progress-linear
        v-if="loading"
        indeterminate
        color="steel-blue"
        class="loading-line"
      />

      <v-row v-else class="admin-grid">
        <v-col v-if="adminSection === 'dashboard'" cols="12">
          <div class="dashboard-toolbar">
            <div>
              <p class="section-kicker">Visão geral</p>
              <h2>Desempenho da barbearia</h2>
            </div>
            <v-btn-toggle
              v-model="dashboardPeriod"
              mandatory
              density="comfortable"
              class="period-toggle"
              @update:model-value="loadStats"
            >
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
              <small
                >{{ stats?.confirmed_appointments ?? 0 }} confirmados</small
              >
            </article>
            <article class="metric-card">
              <span>Faturamento previsto</span>
              <strong>{{
                formatMoney(stats?.total_revenue_cents ?? 0)
              }}</strong>
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
              <strong>{{
                stats?.popular_services?.[0]?.name || "Ainda sem dados"
              }}</strong>
              <small
                >{{
                  stats?.popular_services?.[0]?.bookings || 0
                }}
                agendamento(s)</small
              >
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
              <div
                v-if="!serviceChartSeries.length"
                class="empty-state empty-state--compact"
              >
                Ainda não há dados suficientes.
              </div>
              <ApexChart
                v-else
                type="donut"
                height="230"
                :options="serviceChartOptions"
                :series="serviceChartSeries"
              />
            </article>
            <article class="insight-panel">
              <div class="insight-heading">
                <div>
                  <p class="section-kicker">Status</p>
                  <h2>Resumo dos atendimentos</h2>
                </div>
                <v-icon icon="mdi-chart-arc" aria-hidden="true" />
              </div>
              <ApexChart
                type="donut"
                height="230"
                :options="statusChartOptions"
                :series="statusChartSeries"
              />
            </article>
            <article class="insight-panel insight-panel--heatmap">
              <div class="insight-heading">
                <div>
                  <p class="section-kicker">Ritmo da agenda</p>
                  <h2>Atendimentos nos últimos 30 dias</h2>
                </div>
                <v-progress-circular
                  v-if="loadingCharts"
                  indeterminate
                  size="18"
                  width="2"
                  color="steel-blue"
                />
              </div>
              <ApexChart
                type="heatmap"
                height="190"
                :options="heatmapChartOptions"
                :series="heatmapSeries"
              />
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
              <v-btn
                variant="outlined"
                color="slate"
                size="small"
                @click="adminSection = 'appointments'"
                >Ver agenda</v-btn
              >
            </div>
            <div
              v-if="!appointments.length"
              class="empty-state empty-state--compact"
            >
              Nenhum atendimento encontrado para a data selecionada.
            </div>
            <div
              v-for="appointment in appointments.slice(0, 5)"
              :key="`upcoming-${appointment.id}`"
              class="upcoming-row"
            >
              <div class="upcoming-time">
                {{ formatTime(appointment.start_time) }}
              </div>
              <div class="upcoming-main">
                <strong>{{ appointment.customer_name }}</strong>
                <span>{{ appointment.service_names.join(" · ") }}</span>
              </div>
              <span
                class="appointment-status"
                :class="`appointment-status--${appointment.status.toLowerCase()}`"
              >
                <i aria-hidden="true" />{{ statusLabel(appointment.status) }}
              </span>
              <strong class="upcoming-price">{{
                formatMoney(appointment.total_price_cents)
              }}</strong>
            </div>
          </section>
        </v-col>

        <v-col
          v-if="adminSection === 'appointments'"
          cols="12"
          lg="8"
          class="calendar-column"
        >
          <section v-if="!appointmentsListView" class="calendar-shell">
            <div class="calendar-toolbar">
              <div>
                <p class="section-kicker">Operação</p>
                <h2>Agendamentos</h2>
                <span>Gerencie os horários e atendimentos da barbearia</span>
              </div>
              <div class="calendar-actions">
                <v-btn
                  variant="outlined"
                  color="slate"
                  @click="shiftCalendar(-7)"
                  aria-label="Semana anterior"
                  ><v-icon icon="mdi-chevron-left"
                /></v-btn>
                <strong>{{ calendarRangeLabel }}</strong>
                <v-btn
                  variant="outlined"
                  color="slate"
                  @click="shiftCalendar(7)"
                  aria-label="Próxima semana"
                  ><v-icon icon="mdi-chevron-right"
                /></v-btn>
                <v-btn
                  class="new-appointment-button"
                  prepend-icon="mdi-plus"
                  @click="startNewAppointment"
                  >Novo horário</v-btn
                >
                <div class="view-toggle">
                  <v-btn
                    :class="{ 'view-toggle-active': !appointmentsListView }"
                    prepend-icon="mdi-calendar-month-outline"
                    @click="setAppointmentsView(false)"
                    >Mostrar por Calendário</v-btn
                  ><v-btn
                    :class="{ 'view-toggle-active': appointmentsListView }"
                    prepend-icon="mdi-format-list-bulleted"
                    @click="setAppointmentsView(true)"
                    >Mostrar por Lista</v-btn
                  >
                </div>
                <v-btn
                  class="clients-toggle-button"
                  prepend-icon="mdi-account-group-outline"
                  @click="clientsPanelOpen = !clientsPanelOpen"
                  >Lista de clientes</v-btn
                >
              </div>
            </div>
            <div class="calendar-legend">
              <span><i class="legend-dot legend-dot--confirmed" />Agendado</span
              ><span><i class="legend-dot legend-dot--available" />Livre</span
              ><span
                ><i class="legend-dot legend-dot--pending" />Pré-agendado</span
              >
            </div>
            <v-progress-linear
              v-if="loadingAppointments"
              indeterminate
              color="steel-blue"
            />
            <div class="calendar-board">
              <div class="calendar-corner">GMT-3</div>
              <div
                v-for="day in calendarDays"
                :key="day.key"
                class="calendar-day-header"
                :class="{ 'calendar-day-header--today': day.isToday }"
              >
                <span>{{ day.day }}</span
                ><strong>{{ day.number }}</strong>
              </div>
              <template v-for="time in calendarTimes" :key="time">
                <div class="calendar-time">{{ time }}</div>
                <div
                  v-for="day in calendarDays"
                  :key="`${day.key}-${time}`"
                  class="calendar-cell"
                  @dragover="overCalendarCell"
                  @drop="dropCalendarCell($event, day.key, time)"
                >
                  <div
                    v-for="appointment in appointmentsAt(day.key, time)"
                    :key="appointment.id"
                    class="calendar-appointment-wrap"
                    :class="{
                      'calendar-appointment-wrap--dragging':
                        draggedAppointmentId === appointment.id,
                      'calendar-appointment-wrap--target':
                        dragOverAppointmentId === appointment.id,
                    }"
                  >
                    <button
                      class="calendar-appointment"
                      :class="`calendar-appointment--${appointment.status.toLowerCase()}`"
                      type="button"
                      :draggable="
                        ['PENDING', 'CONFIRMED'].includes(appointment.status)
                      "
                      :aria-label="`${appointment.customer_name}, ${formatTime(appointment.start_time)}. Abrir detalhes.`"
                      @click="openAppointmentDetails(appointment)"
                      @dragstart="startAppointmentDrag($event, appointment)"
                      @dragover="overAppointmentDrag($event, appointment)"
                      @drop="dropAppointment($event, appointment)"
                      @dragend="endAppointmentDrag"
                      @keydown.up.prevent="
                        prepareAccessibleMove(appointment, -1)
                      "
                      @keydown.down.prevent="
                        prepareAccessibleMove(appointment, 1)
                      "
                    >
                      <strong>{{ appointment.customer_name }}</strong
                      ><span
                        >{{ formatTime(appointment.start_time) }}–{{
                          formatTime(appointment.end_time)
                        }}</span
                      ><small>{{ appointment.service_names[0] }}</small>
                    </button>
                  </div>
                  <button
                    v-if="!appointmentsAt(day.key, time).length"
                    class="calendar-add"
                    type="button"
                    aria-label="Adicionar agendamento neste horário"
                    @click="openNewAppointment(day.key, time)"
                  >
                    +
                  </button>
                </div>
              </template>
            </div>
            <div v-if="clientsPanelOpen" class="clients-panel">
              <div class="clients-panel-header">
                <div>
                  <p class="section-kicker">Relacionamento</p>
                  <h3>Lista de clientes</h3>
                  <span>{{ filteredCustomers.length }} clientes</span>
                </div>
                <v-btn
                  icon="mdi-close"
                  variant="text"
                  aria-label="Fechar lista"
                  @click="clientsPanelOpen = false"
                />
              </div>
              <v-text-field
                v-model="customerSearch"
                prepend-inner-icon="mdi-magnify"
                placeholder="Buscar cliente..."
                variant="outlined"
                density="compact"
                hide-details
              />
              <div class="client-list">
                <div
                  v-for="customer in filteredCustomers"
                  :key="customer.id"
                  class="client-list-row"
                >
                  <span class="client-avatar">{{
                    customer.full_name.trim().charAt(0).toUpperCase()
                  }}</span>
                  <div>
                    <strong>{{ customer.full_name }}</strong
                    ><small>{{
                      customer.email ||
                      customer.phone ||
                      "Sem contato cadastrado"
                    }}</small>
                  </div>
                  <v-btn
                    size="small"
                    variant="outlined"
                    @click="openCustomerBooking(customer)"
                    >Agendar</v-btn
                  >
                </div>
                <div v-if="!filteredCustomers.length" class="empty-state">
                  Nenhum cliente encontrado.
                </div>
              </div>
            </div>
          </section>
          <section v-else class="appointments-list-shell">
            <div class="calendar-toolbar list-toolbar">
              <div>
                <p class="section-kicker">Operação</p>
                <h2>Agendamentos</h2>
                <span>Visualização em lista dos atendimentos</span>
              </div>
              <div class="calendar-actions">
                <div class="view-toggle">
                  <v-btn
                    :class="{ 'view-toggle-active': appointmentsListView }"
                    prepend-icon="mdi-format-list-bulleted"
                    @click="setAppointmentsView(true)"
                    >Mostrar por Lista</v-btn
                  ><v-btn
                    :class="{ 'view-toggle-active': !appointmentsListView }"
                    prepend-icon="mdi-calendar-month-outline"
                    @click="setAppointmentsView(false)"
                    >Mostrar por Calendário</v-btn
                  >
                </div>
                <v-btn
                  class="clients-toggle-button"
                  prepend-icon="mdi-account-group-outline"
                  @click="clientsPanelOpen = !clientsPanelOpen"
                  >Lista de clientes</v-btn
                >
              </div>
            </div>
            <div class="list-filter-row">
              <v-text-field
                v-model="filterDate"
                label="Filtrar por data"
                type="date"
                variant="outlined"
                density="compact"
                hide-details
                @change="loadAppointments"
              /><v-select
                v-model="appointmentServiceFilter"
                label="Serviço"
                :items="[
                  { title: 'Todos os serviços', value: '' },
                  ...activeServices().map((service) => ({
                    title: service.name,
                    value: service.name,
                  })),
                ]"
                variant="outlined"
                density="compact"
                hide-details
              /><v-select
                v-model="filterStatus"
                label="Status"
                :items="[
                  { title: 'Todos', value: '' },
                  { title: 'Confirmados', value: 'CONFIRMED' },
                  { title: 'Concluídos', value: 'COMPLETED' },
                  { title: 'Cancelados', value: 'CANCELLED' },
                ]"
                variant="outlined"
                density="compact"
                hide-details
                @update:model-value="loadAppointments"
              /><v-btn
                variant="outlined"
                color="slate"
                @click="
                  filterDate = '';
                  filterStatus = '';
                  appointmentServiceFilter = '';
                  loadAppointments();
                "
                >Ver todos</v-btn
              >
            </div>
            <v-progress-linear
              v-if="loadingAppointments"
              indeterminate
              color="steel-blue"
            />
            <div v-if="!appointments.length" class="empty-state">
              Nenhum agendamento encontrado.
            </div>
            <div v-else class="appointments-list">
              <div
                v-for="appointment in visibleAppointments"
                :key="`list-${appointment.id}`"
                class="appointment-list-card"
                :class="{
                  'appointment-list-card--swiping':
                    swipeAppointmentId === appointment.id,
                  'appointment-list-card--completed':
                    appointment.status === 'COMPLETED',
                }"
                :style="
                  swipeAppointmentId === appointment.id
                    ? { transform: `translateX(${swipeOffset}px)` }
                    : undefined
                "
                @pointerdown="beginAppointmentSwipe($event, appointment)"
                @pointermove="moveAppointmentSwipe($event, appointment)"
                @pointerup="finishAppointmentSwipe(appointment)"
                @pointercancel="
                  swipeStartX = null;
                  swipeAppointmentId = null;
                  swipeOffset = 0;
                "
              >
                <div class="appointment-list-avatar">
                  <span>{{
                    appointment.customer_name.trim().charAt(0).toUpperCase()
                  }}</span>
                </div>
                <div class="appointment-list-person">
                  <strong>{{ appointment.customer_name }}</strong
                  ><small>Cliente da barbearia</small>
                </div>
                <div class="appointment-list-field">
                  <span>Serviço</span
                  ><strong>{{ appointment.service_names.join(" · ") }}</strong
                  ><small>{{ appointment.total_duration_minutes }} min</small>
                </div>
                <div class="appointment-list-field">
                  <span>Data</span
                  ><strong>{{ formatDateLabel(appointment.date) }}</strong>
                </div>
                <div class="appointment-list-field">
                  <span>Horário</span
                  ><strong>{{ formatTime(appointment.start_time) }}</strong>
                </div>
                <span
                  class="appointment-status"
                  :class="`appointment-status--${appointment.status.toLowerCase()}`"
                  ><i aria-hidden="true" />{{
                    statusLabel(appointment.status)
                  }}</span
                >
                <div class="appointment-list-actions">
                  <button
                    v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)"
                    type="button"
                    aria-label="Editar agendamento"
                    @click.stop="openAppointmentDetails(appointment)"
                  >
                    <v-icon icon="mdi-pencil-outline" size="18" />
                  </button>
                  <v-menu
                    v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)"
                    location="bottom end"
                    ><template #activator="{ props }"
                      ><v-btn
                        v-bind="props"
                        icon="mdi-dots-vertical"
                        variant="text"
                        size="small"
                        aria-label="Mais ações" /></template
                    ><v-list density="compact"
                      ><v-list-item
                        v-if="appointment.status === 'CONFIRMED'"
                        title="Concluir atendimento"
                        @click="completeAppointment(appointment)" /><v-list-item
                        title="Cancelar agendamento"
                        @click="cancelAdminAppointment(appointment)" /></v-list
                  ></v-menu>
                  <v-menu
                    v-if="appointment.status === 'CANCELLED'"
                    location="bottom end"
                  >
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-dots-vertical"
                        variant="text"
                        size="small"
                        aria-label="Ações do agendamento cancelado"
                      />
                    </template>
                    <v-list density="compact">
                      <v-list-item
                        prepend-icon="mdi-delete-outline"
                        title="Excluir da lista"
                        @click="deleteCancelledAppointment(appointment)"
                      />
                    </v-list>
                  </v-menu>
                </div>
              </div>
            </div>
          </section>
        </v-col>

        <v-col
          v-if="adminSection === 'appointments'"
          cols="12"
          lg="7"
          class="legacy-appointments"
        >
          <section class="admin-section agenda-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Operação</p>
                <h2>Agendamentos</h2>
                <small class="swipe-hint"
                  >No celular, deslize para a direita para concluir ou para a
                  esquerda para cancelar.</small
                >
              </div>
              <v-btn
                variant="outlined"
                color="slate"
                @click="
                  filterDate = '';
                  loadAppointments();
                "
                >Ver todos</v-btn
              >
            </div>
            <div class="filter-bar">
              <v-text-field
                v-model="filterDate"
                label="Filtrar por data"
                type="date"
                variant="outlined"
                density="compact"
                hide-details
                @change="loadAppointments"
              />
              <v-select
                v-model="filterStatus"
                label="Status"
                :items="[
                  { title: 'Todos', value: '' },
                  { title: 'Confirmados', value: 'CONFIRMED' },
                  { title: 'Concluídos', value: 'COMPLETED' },
                  { title: 'Cancelados', value: 'CANCELLED' },
                ]"
                variant="outlined"
                density="compact"
                hide-details
                @update:model-value="loadAppointments"
              />
            </div>
            <v-progress-linear
              v-if="loadingAppointments"
              indeterminate
              color="steel-blue"
            />
            <div v-else-if="!appointments.length" class="empty-state">
              Nenhum agendamento encontrado para este filtro.
            </div>
            <div
              v-for="appointment in appointments"
              :key="appointment.id"
              class="appointment-row"
              :class="{
                'appointment-row--dragging':
                  swipeAppointmentId === appointment.id,
              }"
              :style="
                swipeAppointmentId === appointment.id
                  ? { transform: `translateX(${swipeOffset}px)` }
                  : undefined
              "
              @pointerdown="beginAppointmentSwipe($event, appointment)"
              @pointermove="moveAppointmentSwipe($event, appointment)"
              @pointerup="finishAppointmentSwipe(appointment)"
              @pointercancel="
                swipeStartX = null;
                swipeAppointmentId = null;
                swipeOffset = 0;
              "
            >
              <div>
                <strong
                  >{{ formatTime(appointment.start_time) }} ·
                  {{ appointment.customer_name }}</strong
                >
                <span
                  >{{ appointment.service_names.join(" · ") }} ·
                  {{ formatMoney(appointment.total_price_cents) }}</span
                >
              </div>
              <div class="appointment-row-actions">
                <span
                  class="appointment-status"
                  :class="`appointment-status--${appointment.status.toLowerCase()}`"
                >
                  <i aria-hidden="true" />
                  {{ statusLabel(appointment.status) }}
                </span>
                <v-btn
                  v-if="appointment.status === 'CONFIRMED'"
                  class="complete-button"
                  variant="outlined"
                  size="small"
                  @click="completeAppointment(appointment)"
                >
                  Concluir
                </v-btn>
                <v-menu
                  v-if="['PENDING', 'CONFIRMED'].includes(appointment.status)"
                  location="bottom end"
                >
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon="mdi-dots-vertical"
                      variant="text"
                      size="small"
                      class="appointment-menu-button"
                      aria-label="Mais ações"
                    />
                  </template>
                  <v-list density="compact" min-width="210">
                    <v-list-item
                      v-if="appointment.possible_no_show"
                      prepend-icon="mdi-account-off-outline"
                      title="Não compareceu"
                      @click="markNoShow(appointment)"
                    />
                    <v-list-item
                      v-if="appointment.status === 'CONFIRMED'"
                      prepend-icon="mdi-check-circle-outline"
                      title="Concluir atendimento"
                      @click="completeAppointment(appointment)"
                    />
                    <v-list-item
                      prepend-icon="mdi-close-circle-outline"
                      title="Cancelar agendamento"
                      @click="cancelAdminAppointment(appointment)"
                    />
                  </v-list>
                </v-menu>
              </div>
            </div>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'appointments'" cols="12" lg="4">
          <section ref="manualPanelRef" class="form-panel manual-panel">
            <p class="section-kicker">Operação</p>
            <div class="manual-panel-heading">
              <span class="manual-panel-icon"
                ><v-icon icon="mdi-calendar-plus-outline"
              /></span>
              <div>
                <p class="section-kicker">OPERAÇÃO</p>
                <h2>Agendar cliente</h2>
              </div>
            </div>
            <v-select
              v-model="manualCustomerId"
              label="Cliente"
              :items="customers"
              item-title="full_name"
              item-value="id"
              variant="outlined"
              :rules="[requiredRule]"
            />
            <v-select
              v-model="manualServiceIds"
              label="Serviços"
              :items="activeServices()"
              :item-title="serviceOptionTitle"
              item-value="id"
              multiple
              chips
              variant="outlined"
              :rules="[requiredRule]"
              @update:model-value="loadManualSlots"
            />
            <v-text-field
              v-model="manualDate"
              label="Data"
              type="date"
              variant="outlined"
              @change="loadManualSlots"
            />
            <div class="manual-slots">
              <v-btn
                v-for="slot in manualSlots"
                :key="slot"
                class="manual-slot"
                :class="{ 'manual-slot--selected': manualSlot === slot }"
                variant="outlined"
                size="small"
                @click="manualSlot = slot"
                >{{ formatTime(slot) }}</v-btn
              >
              <span v-if="!manualSlots.length" class="empty-slots"
                >Selecione serviços e data.</span
              >
            </div>
            <v-textarea
              v-model="manualNotes"
              label="Observações"
              rows="2"
              variant="outlined"
            />
            <v-btn
              class="save-button"
              block
              :loading="creatingAppointment"
              :disabled="
                !manualCustomerId || !manualServiceIds.length || !manualSlot
              "
              @click="createManualAppointment"
              >Confirmar agendamento</v-btn
            >
          </section>
        </v-col>

        <v-col
          v-if="adminSection === 'services' || adminSection === 'hours'"
          cols="12"
          lg="7"
        >
          <section v-if="adminSection === 'services'" class="admin-section">
            <div class="section-heading">
              <div>
                <p class="section-kicker">Catálogo</p>
                <h2>Serviços</h2>
              </div>
              <v-btn variant="outlined" color="slate" @click="resetForm"
                >Novo serviço</v-btn
              >
            </div>
            <div v-if="!services.length" class="empty-state">
              Nenhum serviço cadastrado.
            </div>
            <div
              v-for="service in services"
              :key="service.id"
              class="service-row"
              :class="{ 'service-row--inactive': !service.is_active }"
            >
              <div>
                <strong>{{ service.name }}</strong>
                <span
                  >{{ service.duration_minutes }} min ·
                  {{ formatMoney(service.price_cents) }}</span
                >
              </div>
              <div class="row-actions">
                <v-chip size="small" variant="outlined">{{
                  service.is_active ? "Ativo" : "Inativo"
                }}</v-chip>
                <v-btn variant="text" size="small" @click="editService(service)"
                  >Editar</v-btn
                >
                <v-btn
                  v-if="service.is_active"
                  variant="text"
                  size="small"
                  @click="deactivateService(service)"
                  >Desativar</v-btn
                >
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
                <v-checkbox
                  v-model="day.morningEnabled"
                  label="Manhã"
                  hide-details
                  color="steel-blue"
                />
                <v-text-field
                  v-model="day.morningStart"
                  type="time"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!day.morningEnabled"
                />
                <span class="day-separator">até</span>
                <v-text-field
                  v-model="day.morningEnd"
                  type="time"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!day.morningEnabled"
                />
              </div>
              <div class="day-period">
                <v-checkbox
                  v-model="day.afternoonEnabled"
                  label="Tarde"
                  hide-details
                  color="steel-blue"
                />
                <v-text-field
                  v-model="day.afternoonStart"
                  type="time"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!day.afternoonEnabled"
                />
                <span class="day-separator">até</span>
                <v-text-field
                  v-model="day.afternoonEnd"
                  type="time"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!day.afternoonEnabled"
                />
              </div>
            </div>
            <v-btn
              class="save-button"
              :loading="savingHours"
              @click="saveBusinessHours"
              >Salvar horários</v-btn
            >
          </section>
        </v-col>

        <v-col v-if="adminSection === 'services'" cols="12" lg="5">
          <section class="form-panel">
            <p class="section-kicker">
              {{ editing() ? "Editar serviço" : "Novo serviço" }}
            </p>
            <h2>{{ editing() ? "Atualizar serviço" : "Cadastrar serviço" }}</h2>
            <v-text-field
              v-model="form.name"
              label="Nome do serviço"
              variant="outlined"
              :rules="[requiredRule]"
            />
            <v-textarea
              v-model="form.description"
              label="Descrição"
              rows="3"
              variant="outlined"
            />
            <v-row>
              <v-col cols="7"
                ><v-text-field
                  v-model="form.price"
                  label="Preço (R$)"
                  placeholder="35,00"
                  variant="outlined"
                  :rules="[positiveNumberRule]"
              /></v-col>
              <v-col cols="5"
                ><v-text-field
                  v-model="form.duration"
                  label="Minutos"
                  type="number"
                  variant="outlined"
                  :rules="[positiveNumberRule]"
              /></v-col>
            </v-row>
            <v-btn
              class="save-button"
              block
              :loading="saving"
              @click="saveService"
            >
              {{ editing() ? "Salvar alterações" : "Cadastrar serviço" }}
            </v-btn>
          </section>
        </v-col>

        <v-col v-if="adminSection === 'customers'" cols="12">
          <v-row>
            <v-col cols="12" lg="7">
              <section class="admin-section">
                <div class="section-heading">
                  <div>
                    <p class="section-kicker">Relacionamento</p>
                    <h2>Clientes</h2>
                  </div>
                  <v-btn
                    variant="outlined"
                    color="slate"
                    @click="resetCustomerForm"
                    >Novo cliente</v-btn
                  >
                </div>
                <v-text-field
                  v-model="customerSearch"
                  label="Buscar por nome, e-mail ou telefone"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="customer-search"
                />
                <div v-if="!filteredCustomers.length" class="empty-state">
                  Nenhum cliente encontrado.
                </div>
                <div
                  v-for="customer in filteredCustomers"
                  :key="customer.id"
                  class="customer-row"
                  :class="{ 'customer-row--inactive': !customer.is_active }"
                >
                  <div>
                    <strong>{{ customer.full_name }}</strong
                    ><span>{{
                      customer.email ||
                      customer.phone ||
                      "Sem contato cadastrado"
                    }}</span>
                  </div>
                  <div class="row-actions">
                    <v-chip size="small" variant="outlined">{{
                      customer.is_active ? "Ativo" : "Inativo"
                    }}</v-chip
                    ><v-btn
                      variant="text"
                      size="small"
                      @click="editCustomer(customer)"
                      >Editar</v-btn
                    ><v-btn
                      v-if="customer.is_active"
                      variant="text"
                      size="small"
                      @click="deactivateCustomer(customer)"
                      >Desativar</v-btn
                    >
                  </div>
                </div>
              </section>
            </v-col>
            <v-col cols="12" lg="5">
              <section class="form-panel">
                <p class="section-kicker">
                  {{ customerForm.id ? "Editar cliente" : "Novo cliente" }}
                </p>
                <h2>
                  {{
                    customerForm.id ? "Atualizar cadastro" : "Cadastrar cliente"
                  }}
                </h2>
                <v-text-field
                  v-model="customerForm.full_name"
                  label="Nome completo"
                  variant="outlined"
                  :rules="[requiredRule]"
                />
                <v-text-field
                  v-model="customerForm.email"
                  label="E-mail"
                  type="email"
                  variant="outlined"
                />
                <v-text-field
                  v-model="customerForm.phone"
                  label="Telefone"
                  variant="outlined"
                />
                <v-text-field
                  v-model="customerForm.password"
                  :label="
                    customerForm.id
                      ? 'Nova senha (opcional)'
                      : 'Senha temporária'
                  "
                  type="password"
                  variant="outlined"
                  :hint="
                    customerForm.id
                      ? 'Deixe em branco para manter a senha atual.'
                      : 'Mínimo de 8 caracteres.'
                  "
                  persistent-hint
                />
                <v-btn
                  class="save-button"
                  block
                  :loading="savingCustomer"
                  @click="saveCustomer"
                  >{{
                    customerForm.id ? "Salvar alterações" : "Cadastrar cliente"
                  }}</v-btn
                >
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
                <v-text-field
                  v-model="profileForm.full_name"
                  label="Nome completo"
                  variant="outlined"
                />
                <v-text-field
                  v-model="profileForm.email"
                  label="E-mail"
                  type="email"
                  variant="outlined"
                />
                <v-text-field
                  v-model="profileForm.phone"
                  label="Telefone"
                  variant="outlined"
                />
                <v-text-field
                  v-model="profileForm.password"
                  label="Nova senha (opcional)"
                  type="password"
                  hint="Deixe em branco para manter a senha atual."
                  persistent-hint
                  variant="outlined"
                />
                <v-btn
                  class="save-button"
                  :loading="savingProfile"
                  @click="saveProfile"
                  >Salvar meu perfil</v-btn
                >
              </section>
            </v-col>
            <v-col cols="12" md="6">
              <section class="settings-panel settings-panel--dark">
                <p class="section-kicker">Dados da barbearia</p>
                <h2>Informações gerais</h2>
                <v-text-field
                  v-model="settingsForm.name"
                  label="Nome da barbearia"
                  variant="outlined"
                />
                <v-text-field
                  v-model="settingsForm.timezone"
                  label="Fuso horário"
                  variant="outlined"
                />
                <v-row>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="settingsForm.capacity"
                      label="Atendimentos simultâneos"
                      type="number"
                      variant="outlined"
                  /></v-col>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="settingsForm.booking_window_days"
                      label="Dias para agendar"
                      type="number"
                      variant="outlined"
                  /></v-col>
                </v-row>
                <v-row>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="settingsForm.min_cancellation_notice_minutes"
                      label="Aviso para cancelar (min)"
                      type="number"
                      variant="outlined"
                  /></v-col>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="settingsForm.slot_granularity_minutes"
                      label="Intervalo (min)"
                      type="number"
                      variant="outlined"
                  /></v-col>
                </v-row>
                <v-btn
                  class="save-button"
                  :loading="savingSettings"
                  @click="saveShopSettings"
                  >Salvar dados da barbearia</v-btn
                >
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
                <v-text-field
                  v-model="specialDateForm.date"
                  label="Data"
                  type="date"
                  variant="outlined"
                />
                <v-text-field
                  v-model="specialDateForm.label"
                  label="Descrição"
                  placeholder="Feriado, evento ou horário especial"
                  variant="outlined"
                />
                <v-checkbox
                  v-model="specialDateForm.is_closed"
                  label="Barbearia fechada nesta data"
                  color="steel-blue"
                  hide-details
                />
                <v-row v-if="!specialDateForm.is_closed">
                  <v-col cols="6"
                    ><v-text-field
                      v-model="specialDateForm.custom_open_time"
                      label="Abertura"
                      type="time"
                      variant="outlined"
                  /></v-col>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="specialDateForm.custom_close_time"
                      label="Fechamento"
                      type="time"
                      variant="outlined"
                  /></v-col>
                </v-row>
                <v-btn
                  class="save-button"
                  :loading="savingException"
                  @click="createSpecialDate"
                  >Adicionar exceção</v-btn
                >
                <div v-if="!specialDates.length" class="empty-state">
                  Nenhuma data especial cadastrada.
                </div>
                <div
                  v-for="item in specialDates"
                  :key="item.id"
                  class="exception-row"
                >
                  <div>
                    <strong>{{ formatDateLabel(item.date) }}</strong
                    ><span>{{
                      item.label ||
                      (item.is_closed
                        ? "Fechado"
                        : `${item.custom_open_time?.slice(0, 5)} às ${item.custom_close_time?.slice(0, 5)}`)
                    }}</span>
                  </div>
                  <v-btn
                    variant="text"
                    size="small"
                    @click="removeSpecialDate(item)"
                    >Remover</v-btn
                  >
                </div>
              </section>
            </v-col>
            <v-col cols="12" md="6">
              <section class="settings-panel settings-panel--dark">
                <p class="section-kicker">Indisponibilidade pontual</p>
                <h2>Bloquear horário</h2>
                <v-text-field
                  v-model="blockedSlotForm.date"
                  label="Data"
                  type="date"
                  variant="outlined"
                />
                <v-row>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="blockedSlotForm.start_time"
                      label="Início"
                      type="time"
                      variant="outlined"
                  /></v-col>
                  <v-col cols="6"
                    ><v-text-field
                      v-model="blockedSlotForm.end_time"
                      label="Fim"
                      type="time"
                      variant="outlined"
                  /></v-col>
                </v-row>
                <v-text-field
                  v-model="blockedSlotForm.reason"
                  label="Motivo (opcional)"
                  variant="outlined"
                />
                <v-btn
                  class="save-button"
                  :loading="savingException"
                  @click="createBlockedSlot"
                  >Bloquear horário</v-btn
                >
                <div v-if="!blockedSlots.length" class="empty-state">
                  Nenhum horário bloqueado.
                </div>
                <div
                  v-for="item in blockedSlots"
                  :key="item.id"
                  class="exception-row"
                >
                  <div>
                    <strong
                      >{{ formatDateLabel(item.date) }} ·
                      {{ formatTime(item.start_time) }}–{{
                        formatTime(item.end_time)
                      }}</strong
                    ><span>{{
                      item.reason || "Indisponibilidade manual"
                    }}</span>
                  </div>
                  <v-btn
                    variant="text"
                    size="small"
                    @click="removeBlockedSlot(item)"
                    >Remover</v-btn
                  >
                </div>
              </section>
            </v-col>
          </v-row>
        </v-col>
      </v-row>

      <v-dialog
        :model-value="Boolean(pendingAction)"
        max-width="440"
        @update:model-value="(value) => !value && (pendingAction = null)"
      >
        <v-card class="confirmation-dialog">
          <v-card-title class="dialog-title-row"
            ><span>{{
              pendingAction?.type === "cancel"
                ? "Cancelar agendamento?"
                : "Concluir atendimento?"
            }}</span
            ><v-btn
              icon="mdi-close"
              variant="text"
              aria-label="Fechar"
              @click="pendingAction = null"
          /></v-card-title>
          <v-card-text>
            {{
              pendingAction?.type === "cancel"
                ? `Deseja cancelar o agendamento de ${pendingAction.appointment.customer_name}?`
                : `Deseja marcar o atendimento de ${pendingAction?.appointment.customer_name} como concluído?`
            }}
          </v-card-text>
          <v-card-actions>
            <v-btn
              variant="text"
              :disabled="processingAction"
              @click="pendingAction = null"
              >Não, voltar</v-btn
            >
            <v-btn
              class="save-button"
              :loading="processingAction"
              @click="confirmPendingAction"
              >Sim, confirmar</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-dialog
        :model-value="Boolean(reorderPreview)"
        max-width="560"
        @update:model-value="(value) => !value && (reorderPreview = null)"
      >
        <v-card class="confirmation-dialog reorder-dialog">
          <v-card-title class="dialog-title-row"
            ><span>Confirmar alteração da ordem?</span
            ><v-btn
              icon="mdi-close"
              variant="text"
              aria-label="Fechar"
              @click="reorderPreview = null"
          /></v-card-title>
          <v-card-text v-if="reorderPreview">
            <p>
              <strong>{{ reorderPreview.moved.customer_name }}</strong> será
              movido de
              <strong>{{ reorderPreview.fromTime.slice(0, 5) }}</strong> para
              <strong>{{ reorderPreview.toTime.slice(0, 5) }}</strong
              >.
            </p>
            <p v-if="reorderPreview.affected.length">
              Os seguintes clientes também terão seus horários ajustados:
            </p>
            <ul
              v-if="reorderPreview.affected.length"
              class="reorder-affected-list"
            >
              <li
                v-for="item in reorderPreview.affected"
                :key="item.appointment.id"
              >
                <strong>{{ item.appointment.customer_name }}</strong
                >: {{ item.fromTime.slice(0, 5) }} →
                {{ item.toTime.slice(0, 5) }}
              </li>
            </ul>
            <p>
              Os serviços, valores e demais dados serão preservados. A alteração
              será validada e aplicada de forma atômica.
            </p>
          </v-card-text>
          <v-card-actions
            ><v-btn
              variant="text"
              :disabled="savingReorder"
              @click="reorderPreview = null"
              >Cancelar</v-btn
            ><v-btn
              class="save-button"
              :loading="savingReorder"
              @click="confirmReorder"
              >Confirmar alteração</v-btn
            ></v-card-actions
          >
        </v-card>
      </v-dialog>
      <v-dialog
        v-model="appointmentDialogOpen"
        max-width="680"
        width="calc(100% - 32px)"
        @click:outside="
          appointmentDialogOpen = false;
          appointmentDialogEditMode = false;
        "
      >
        <v-card v-if="appointmentDialog" class="appointment-details-dialog">
          <v-card-title class="dialog-title-row"
            ><span>{{
              appointmentDialogEditMode
                ? "Editar agendamento"
                : "Detalhes do agendamento"
            }}</span
            ><v-btn
              icon="mdi-close"
              variant="text"
              aria-label="Fechar"
              @click="
                appointmentDialogOpen = false;
                appointmentDialogEditMode = false;
              "
          /></v-card-title>
          <v-card-text
            v-if="appointmentDialogEditMode"
            class="appointment-edit-form"
            ><p class="dialog-helper">
              Altere os dados e salve a edição neste mesmo modal.
            </p>
            <v-select
              v-model="manualCustomerId"
              label="Cliente"
              :items="customers"
              item-title="full_name"
              item-value="id"
              variant="outlined" /><v-select
              v-model="manualServiceIds"
              label="Serviços"
              :items="activeServices()"
              :item-title="serviceOptionTitle"
              item-value="id"
              multiple
              chips
              variant="outlined"
              @update:model-value="loadManualSlots" />
            <div class="appointment-edit-grid">
              <v-text-field
                v-model="manualDate"
                label="Data"
                type="date"
                variant="outlined"
                @update:model-value="loadManualSlots"
              /><v-select
                v-model="manualSlot"
                label="Horário"
                :items="manualSlots.length ? manualSlots : calendarTimes"
                variant="outlined"
              />
            </div>
            <v-textarea
              v-model="manualNotes"
              label="Observações"
              rows="3"
              variant="outlined"
          /></v-card-text>
          <v-card-text v-else>
            <div class="appointment-detail-person">
              <span class="detail-avatar">{{
                appointmentDialog.customer_name.trim().charAt(0).toUpperCase()
              }}</span>
              <div>
                <h3>{{ appointmentDialog.customer_name }}</h3>
                <span>Cliente da barbearia</span>
              </div>
            </div>
            <div class="appointment-detail-grid">
              <div>
                <small>Serviço</small
                ><strong>{{
                  appointmentDialog.service_names.join(" · ")
                }}</strong>
              </div>
              <div>
                <small>Preço</small
                ><strong>{{
                  formatMoney(appointmentDialog.total_price_cents)
                }}</strong>
              </div>
              <div>
                <small>Horário</small
                ><strong
                  >{{ formatTime(appointmentDialog.start_time) }}–{{
                    formatTime(appointmentDialog.end_time)
                  }}</strong
                >
              </div>
              <div>
                <small>Status</small
                ><strong>{{ statusLabel(appointmentDialog.status) }}</strong>
              </div>
            </div>
            <p v-if="appointmentDialog.notes" class="detail-notes">
              <small>Observações</small>{{ appointmentDialog.notes }}
            </p>
          </v-card-text>
          <v-card-actions
            v-if="appointmentDialogEditMode"
            class="detail-actions appointment-edit-actions"
            ><v-btn
              variant="outlined"
              prepend-icon="mdi-close"
              @click="cancelAppointmentDialogEdit"
              >Cancelar edição</v-btn
            ><v-spacer /><v-btn
              class="save-button"
              prepend-icon="mdi-content-save-outline"
              :loading="creatingAppointment"
              :disabled="
                !manualCustomerId || !manualServiceIds.length || !manualSlot
              "
              @click="submitAppointmentDialog"
              >Salvar edição</v-btn
            ></v-card-actions
          >
          <v-card-actions v-else class="detail-actions"
            ><v-btn
              variant="outlined"
              color="primary"
              prepend-icon="mdi-pencil-outline"
              @click="editAppointmentFromDialog"
              >Editar agendamento</v-btn
            ><v-spacer /><v-btn
              v-if="['PENDING', 'CONFIRMED'].includes(appointmentDialog.status)"
              variant="outlined"
              color="error"
              prepend-icon="mdi-calendar-remove-outline"
              @click="
                cancelAdminAppointment(appointmentDialog);
                appointmentDialogOpen = false;
              "
              >Cancelar agendamento</v-btn
            ><v-btn
              v-if="appointmentDialog.status === 'CONFIRMED'"
              class="complete-button"
              prepend-icon="mdi-check-circle-outline"
              :loading="processingAction"
              @click="
                completeAppointment(appointmentDialog);
                appointmentDialogOpen = false;
              "
              >Concluir atendimento</v-btn
            ></v-card-actions
          >
        </v-card>
        <v-card v-else class="appointment-booking-dialog">
          <v-card-title class="dialog-title-row"
            ><span>Agendar cliente</span
            ><v-btn
              icon="mdi-close"
              variant="text"
              aria-label="Fechar"
              @click="appointmentDialogOpen = false"
          /></v-card-title>
          <v-card-text
            ><p class="dialog-helper">
              Selecione o cliente e os serviços para o horário escolhido.
            </p>
            <v-select
              v-model="manualCustomerId"
              label="Cliente"
              :items="customers"
              item-title="full_name"
              item-value="id"
              variant="outlined" /><v-select
              v-model="manualServiceIds"
              label="Serviços"
              :items="activeServices()"
              :item-title="serviceOptionTitle"
              item-value="id"
              multiple
              chips
              variant="outlined"
              @update:model-value="loadManualSlots" /><v-text-field
              :model-value="manualSlot ? `${manualDate} · ${formatTime(manualSlot)}` : 'Selecione um horário no calendário'"
              label="Horário selecionado"
              prepend-inner-icon="mdi-clock-outline"
              variant="outlined"
              readonly /><v-textarea
              v-model="manualNotes"
              label="Observações"
              rows="3"
              variant="outlined" /></v-card-text
          ><v-card-actions
            ><v-btn variant="text" @click="appointmentDialogOpen = false"
              >Cancelar</v-btn
            ><v-btn
              class="save-button"
              :loading="creatingAppointment"
              :disabled="
                !manualCustomerId || !manualServiceIds.length || !manualSlot
              "
              @click="submitAppointmentDialog"
              >Confirmar agendamento</v-btn
            ></v-card-actions
          >
        </v-card>
      </v-dialog>
      <v-dialog
        :model-value="Boolean(reschedulePreview)"
        max-width="460"
        @update:model-value="(value) => !value && (reschedulePreview = null)"
      >
        <v-card class="confirmation-dialog">
          <v-card-title class="dialog-title-row"
            ><span>Realocar agendamento?</span
            ><v-btn
              icon="mdi-close"
              variant="text"
              aria-label="Fechar"
              @click="reschedulePreview = null"
          /></v-card-title>
          <v-card-text v-if="reschedulePreview"
            >Deseja mover
            <strong>{{ reschedulePreview.appointment.customer_name }}</strong>
            de
            <strong>{{
              formatTime(reschedulePreview.appointment.start_time)
            }}</strong>
            para <strong>{{ reschedulePreview.time }}</strong
            >? O sistema validará disponibilidade, duração e conflitos antes de
            salvar.</v-card-text
          >
          <v-card-actions
            ><v-btn
              variant="text"
              :disabled="savingReorder"
              @click="reschedulePreview = null"
              >Cancelar</v-btn
            ><v-btn
              class="save-button"
              :loading="savingReorder"
              @click="confirmReschedule"
              >Confirmar</v-btn
            ></v-card-actions
          >
        </v-card>
      </v-dialog>
      <v-bottom-sheet v-model="moreMenuOpen">
        <v-card class="more-sheet">
          <v-card-title>Mais opções</v-card-title>
          <v-list bg-color="transparent" density="comfortable">
            <v-list-item
              v-for="item in moreNavItems"
              :key="item.key"
              :active="adminSection === item.key"
              :prepend-icon="item.icon"
              :title="item.label"
              @click="selectAdminSection(item.key)"
            />
          </v-list>
        </v-card>
      </v-bottom-sheet>
    </v-container>
  </main>
</template>

<style scoped>
.admin-content {
  min-height: calc(100dvh - 64px);
  background: var(--paper);
  padding: 40px 20px 72px;
}
.admin-container {
  max-width: 1180px;
}
.admin-intro,
.section-heading,
.service-row,
.day-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.admin-intro {
  align-items: flex-start;
  margin-bottom: 32px;
}
.admin-intro h1,
.section-heading h2,
.form-panel h2 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-ui);
  font-weight: 700;
}
.admin-intro h1 {
  font-size: clamp(2.3rem, 5vw, 3.5rem);
  line-height: 1;
}
.admin-intro p:not(.section-kicker) {
  margin: 12px 0 0;
  color: var(--slate);
}
.admin-navigation {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
  margin-bottom: 28px;
  padding: 8px;
  border: 1px solid var(--hairline);
  background: var(--surface-white-medium);
  backdrop-filter: blur(8px);
}
.admin-nav-item {
  display: flex;
  min-height: 52px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--navy);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 0.84rem;
  font-weight: 600;
  transition:
    border-color var(--motion-fast),
    background-color var(--motion-fast),
    color var(--motion-fast),
    transform var(--motion-fast);
}
.admin-nav-item:active {
  transform: scale(0.98);
}
.admin-nav-item:hover,
.admin-nav-item--active {
  border-color: var(--surface-steel-blue-border);
  background: var(--surface-steel-blue-subtle);
  color: var(--navy);
}
.admin-nav-item--active {
  box-shadow: inset 0 -2px 0 var(--steel-blue);
}
.section-kicker {
  margin: 0 0 8px;
  color: var(--steel-blue);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.section-heading h2,
.form-panel h2 {
  font-size: 2rem;
  line-height: 1.05;
}
.section-heading {
  margin-bottom: 4px;
}
.admin-section,
.form-panel {
  border: 1px solid var(--hairline);
  padding: 24px;
  background: var(--surface-white-soft);
  transition: border-color var(--motion-fast);
}
.admin-section:hover {
  border-color: var(--hairline-strong);
}
.form-panel {
  position: sticky;
  top: 88px;
  background: var(--navy-deep);
}
.form-panel h2 {
  margin-bottom: 24px;
  color: var(--paper);
}
.form-panel :deep(.v-label),
.form-panel :deep(input),
.form-panel :deep(textarea) {
  color: var(--paper);
}
.form-panel :deep(.v-field__outline) {
  color: var(--surface-paper-outline-strong);
}
.settings-panel {
  height: 100%;
  border: 1px solid var(--hairline);
  padding: 24px;
  background: var(--surface-white-soft);
}
.settings-panel h2 {
  margin: 0 0 24px;
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: 2rem;
  font-weight: 700;
}
.settings-panel--dark {
  background: var(--navy-deep);
}
.settings-panel--dark h2 {
  color: var(--paper);
}
.settings-panel--dark :deep(.v-label),
.settings-panel--dark :deep(input) {
  color: var(--paper);
}
.settings-panel--dark :deep(.v-field__outline) {
  color: var(--surface-paper-outline-strong);
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.metric-card {
  min-height: 132px;
  padding: 20px;
  border: 1px solid var(--hairline);
  background: var(--surface-white-soft);
  transition:
    border-color var(--motion-fast),
    transform var(--motion-fast);
}
.metric-card:hover {
  border-color: var(--hairline-strong);
  transform: translateY(-2px);
}
.metric-card--accent {
  border-color: var(--surface-navy-strong-border);
  background: var(--surface-steel-blue-soft);
}
.metric-card--cancelled {
  border-color: var(--surface-slate-border);
  background: var(--surface-slate-soft);
}
.metric-card span,
.metric-card small {
  display: block;
  color: var(--slate);
  font-size: 0.78rem;
}
.metric-card strong {
  display: block;
  overflow: hidden;
  margin: 10px 0 8px;
  color: var(--ink);
  font-size: clamp(1.3rem, 2vw, 1.8rem);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dashboard-insights {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.insight-panel {
  min-height: 220px;
  padding: 20px;
  border: 1px solid var(--hairline);
  background: var(--surface-white-soft);
}
.insight-panel--heatmap {
  grid-column: 1 / -1;
  min-height: 240px;
}
.insight-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 24px;
}
.insight-heading h2 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 400;
  line-height: 1.05;
}
.insight-heading > .v-icon {
  color: var(--steel-blue);
}
.insight-bar-row + .insight-bar-row {
  margin-top: 16px;
}
.insight-bar-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--ink);
  font-size: 0.8rem;
}
.insight-bar-label strong {
  color: var(--slate);
  font-weight: 600;
}
.insight-bar-track {
  height: 6px;
  margin-top: 7px;
  overflow: hidden;
  background: rgba(var(--color-slate-rgb), 0.18);
}
.insight-bar-fill {
  display: block;
  height: 100%;
  background: var(--steel-blue);
  transition: width var(--motion-normal);
}
.insight-bar-fill--1 {
  background: var(--navy);
}
.insight-bar-fill--2 {
  background: var(--slate);
}
.status-summary {
  display: grid;
  gap: 14px;
}
.status-summary > div {
  display: grid;
  grid-template-columns: 9px 1fr auto;
  align-items: center;
  gap: 9px;
  color: var(--slate);
  font-size: 0.82rem;
}
.status-summary strong {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 600;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--slate);
}
.status-dot--confirmed {
  background: var(--steel-blue);
}
.status-dot--completed {
  background: var(--navy);
}
.status-dot--cancelled {
  background: var(--slate);
}
.agenda-section {
  height: 100%;
}
.filter-bar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 24px 0 12px;
}
.appointment-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--hairline);
  touch-action: pan-y;
  user-select: none;
  transform: translateX(0);
  transition:
    transform 180ms ease,
    background-color 180ms ease;
}
.appointment-row--dragging {
  z-index: 1;
  cursor: grabbing;
  background: var(--surface-steel-blue-soft);
  box-shadow: var(--shadow-drag);
  transition: none;
}
.appointment-row:last-child {
  border-bottom: 0;
}
.appointment-row strong,
.appointment-row span {
  display: block;
}
.appointment-row span {
  margin-top: 5px;
  color: var(--slate);
  font-size: 0.8rem;
}
.appointment-row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.appointment-row-actions :deep(.v-chip) {
  border-radius: 4px;
}
.appointment-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--slate);
  font-size: 0.76rem;
  white-space: nowrap;
}
.appointment-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--slate);
}
.appointment-status--confirmed i {
  background: var(--color-confirmed);
}
.appointment-status--completed i {
  background: var(--color-completed);
}
.appointment-status--cancelled i {
  background: var(--color-cancelled);
}
.appointment-status--no_show i {
  background: var(--color-no-show);
}
.appointment-menu-button {
  min-width: 40px;
  color: var(--slate);
}
.admin-nav-more {
  display: none;
  min-height: 52px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-paper);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 0.84rem;
  font-weight: 600;
}
.admin-logout-nav {
  display: flex;
  min-height: 48px;
  align-items: center;
  gap: 9px;
  margin-top: auto;
  padding: 0 18px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-paper);
  cursor: pointer;
  font-family: var(--font-ui);
  font-size: 0.86rem;
  text-align: left;
}
.admin-logout-nav:hover {
  border-color: rgba(139, 92, 246, 0.35);
  background: rgba(139, 92, 246, 0.12);
  color: #fff;
}
.more-sheet {
  padding: 8px 8px max(8px, env(safe-area-inset-bottom));
  background: var(--color-navy-deep) !important;
  color: var(--color-paper);
}
.more-sheet .v-card-title {
  padding: 16px 16px 8px;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 400;
}
.more-sheet :deep(.v-list-item) {
  min-height: 52px;
  border-radius: var(--radius-btn);
  color: var(--color-paper);
}
.more-sheet :deep(.v-list-item--active) {
  background: rgba(var(--color-steel-blue-rgb), 0.18);
  color: var(--color-paper);
}
.no-show-button,
.cancel-appointment-button {
  display: none !important;
}
.swipe-hint {
  display: block;
  margin-top: 8px;
  color: var(--slate);
  font-size: 0.72rem;
  font-weight: 400;
}
@media (min-width: 601px) {
  .swipe-hint {
    display: none;
  }
}
.cancel-appointment-button {
  border-color: var(--surface-slate-border) !important;
  border-radius: 4px !important;
  color: var(--slate) !important;
  text-transform: none;
}
.no-show-button {
  border-color: var(--surface-steel-blue-border-strong) !important;
  border-radius: 4px !important;
  color: var(--navy) !important;
  text-transform: none;
}
.complete-button {
  border-color: var(--surface-navy-strong-border) !important;
  border-radius: 4px !important;
  color: var(--navy) !important;
  text-transform: none;
}
.manual-panel {
  height: 100%;
}
.manual-panel-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.manual-panel-heading h2 {
  margin: 0;
  color: var(--color-paper);
  font-size: 1.55rem;
}
.manual-panel-heading .section-kicker {
  margin: 0 0 3px;
}
.manual-panel-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #5932c4, #2563eb);
  color: #fff;
}
.manual-panel .section-kicker {
  color: var(--steel-blue);
}
.manual-panel :deep(.v-field--error:not(.v-field--disabled) .v-field__outline) {
  color: var(--surface-paper-outline-strong) !important;
}
.manual-panel :deep(.v-field--error .v-label),
.manual-panel :deep(.v-field--error .v-icon) {
  color: var(--color-slate) !important;
}
.manual-panel :deep(.v-messages__message) {
  display: none;
}
.manual-slots {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: -4px 0 20px;
}
.manual-slot {
  border-color: var(--surface-paper-outline) !important;
  border-radius: 4px !important;
  color: var(--paper) !important;
}
.manual-slot--selected {
  border-color: var(--steel-blue) !important;
  background: var(--steel-blue) !important;
}
.manual-slots .empty-slots {
  grid-column: 1 / -1;
  min-height: 48px;
  font-size: 0.78rem;
}
.admin-section + .admin-section {
  margin-top: 24px;
}
.loading-line {
  margin: 24px 0;
}
.service-row,
.day-row {
  padding: 16px 0;
  border-bottom: 1px solid var(--hairline);
  transition: background-color var(--motion-fast);
}
.service-row:hover,
.day-row:hover {
  background: var(--surface-steel-blue-soft);
}
.service-row:last-child {
  border-bottom: 0;
}
.service-row strong,
.service-row span {
  display: block;
}
.service-row span {
  margin-top: 5px;
  color: var(--slate);
  font-size: 0.82rem;
}
.service-row--inactive {
  opacity: 0.58;
}
.customer-search {
  margin: 24px 0 8px;
}
.customer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--hairline);
  transition: background-color var(--motion-fast);
}
.customer-row:hover {
  background: var(--surface-steel-blue-soft);
}
.customer-row:last-child {
  border-bottom: 0;
}
.customer-row strong,
.customer-row span {
  display: block;
}
.customer-row span {
  margin-top: 5px;
  color: var(--slate);
  font-size: 0.82rem;
}
.customer-row--inactive {
  opacity: 0.58;
}
.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.row-actions :deep(.v-chip) {
  border-radius: 4px;
}
.day-row {
  align-items: flex-start;
  flex-wrap: wrap;
}
.day-label {
  min-width: 130px;
  padding-top: 12px;
}
.day-period {
  display: flex;
  flex: 1 1 330px;
  align-items: center;
  gap: 8px;
}
.day-period :deep(.v-checkbox) {
  min-width: 92px;
}
.day-period :deep(.v-input) {
  max-width: 120px;
}
.day-separator {
  color: var(--slate);
  font-size: 0.8rem;
}
.save-button {
  min-height: 46px;
  margin-top: 20px;
  border-radius: var(--radius-sm) !important;
  background: var(--steel-blue) !important;
  color: var(--paper) !important;
  text-transform: none;
  transition:
    transform var(--motion-fast),
    background-color var(--motion-fast);
}
.save-button:hover {
  background: var(--color-steel-blue-hover) !important;
}
.save-button:active {
  transform: scale(0.98);
}
.logout-button {
  color: var(--steel-blue);
  text-transform: none;
}
.empty-state {
  padding: 32px 0;
  color: var(--slate);
}
.exception-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--hairline);
}
.exception-row:last-child {
  border-bottom: 0;
}
.exception-row strong,
.exception-row span {
  display: block;
}
.exception-row span {
  margin-top: 4px;
  color: var(--slate);
  font-size: 0.8rem;
}
.settings-panel--dark .exception-row {
  border-color: var(--hairline-dark);
}
.settings-panel--dark .exception-row strong {
  color: var(--paper);
}
.confirmation-dialog {
  border: 1px solid var(--hairline) !important;
  border-radius: 8px !important;
  background: var(--paper) !important;
}
.confirmation-dialog .v-card-title {
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: 1.7rem;
  font-weight: 700;
}
.confirmation-dialog .v-card-text {
  color: var(--slate);
}

/* Painel premium: navegação lateral no desktop e superfície escura consistente. */
.admin-content {
  min-height: calc(100dvh - 64px);
  background: var(--color-ink);
  color: var(--color-paper);
}
.admin-container {
  max-width: 1440px;
}
.admin-intro h1,
.section-heading h2,
.form-panel h2,
.settings-panel h2 {
  color: var(--color-paper);
}
.admin-intro p:not(.section-kicker),
.metric-card span,
.metric-card small {
  color: var(--color-slate);
}
.admin-navigation {
  background: var(--color-navy-deep);
  border-color: rgba(var(--color-slate-rgb), 0.22);
}
.admin-navigation::before {
  content: "Sistema Barbearia";
  display: none;
  color: var(--color-paper);
  font-family: var(--font-display);
  font-size: 1.25rem;
}
.admin-nav-item {
  color: var(--color-paper);
}
.admin-nav-item:hover,
.admin-nav-item--active {
  color: var(--color-paper);
  background: rgba(var(--color-steel-blue-rgb), 0.16);
}
.admin-section,
.metric-card,
.insight-panel,
.settings-panel {
  background: var(--color-navy-deep);
  border-color: rgba(var(--color-slate-rgb), 0.24);
}
.admin-section:hover,
.metric-card:hover {
  border-color: rgba(var(--color-steel-blue-rgb), 0.6);
}
.dashboard-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}
.dashboard-toolbar h2 {
  margin: 0;
  color: var(--color-paper);
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 400;
  line-height: 1;
}
.period-toggle {
  border: 1px solid rgba(var(--color-slate-rgb), 0.28);
  background: var(--color-navy-deep);
}
.period-toggle :deep(.v-btn) {
  min-height: 40px;
  color: var(--color-slate);
  text-transform: none;
}
.period-toggle :deep(.v-btn--active) {
  background: var(--color-steel-blue);
  color: var(--color-paper);
}
.metric-card strong,
.insight-heading h2,
.insight-bar-label,
.status-summary strong {
  color: var(--color-paper);
}
.metric-card--accent {
  background: rgba(var(--color-steel-blue-rgb), 0.16);
}
.metric-card--cancelled {
  background: rgba(var(--color-slate-rgb), 0.12);
}
.service-row:hover,
.customer-row:hover,
.day-row:hover {
  background: rgba(var(--color-steel-blue-rgb), 0.1);
}
.service-row strong,
.customer-row strong,
.day-row strong,
.appointment-row strong,
.exception-row strong {
  color: var(--color-paper);
}
.appointment-row {
  border-color: rgba(var(--color-paper-rgb), 0.14);
}
.appointment-row span,
.service-row span,
.customer-row span,
.exception-row span {
  color: var(--color-slate);
}
.filter-bar :deep(.v-field),
.manual-panel :deep(.v-field),
.settings-panel--dark :deep(.v-field) {
  background: rgba(var(--color-ink-rgb), 0.34);
}
.filter-bar :deep(input),
.filter-bar :deep(.v-label),
.manual-panel :deep(input),
.manual-panel :deep(.v-label),
.settings-panel--dark :deep(input),
.settings-panel--dark :deep(.v-label) {
  color: var(--color-paper);
}
.insight-panel--heatmap {
  background: var(--color-navy-deep);
}
.upcoming-panel {
  margin-top: 12px;
  padding: 20px;
  border: 1px solid rgba(var(--color-slate-rgb), 0.24);
  background: var(--color-navy-deep);
}
.upcoming-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid rgba(var(--color-paper-rgb), 0.12);
}
.upcoming-time {
  color: var(--color-steel-blue);
  font-size: 1.15rem;
  font-weight: 600;
}
.upcoming-main strong,
.upcoming-main span {
  display: block;
}
.upcoming-main strong {
  color: var(--color-paper);
  font-size: 0.9rem;
}
.upcoming-main span {
  margin-top: 4px;
  overflow: hidden;
  color: var(--color-slate);
  font-size: 0.78rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upcoming-price {
  color: var(--color-paper);
  font-size: 0.85rem;
}

@media (min-width: 961px) {
  .admin-container {
    padding-left: 248px;
  }
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
  .admin-navigation::before {
    content: "BarberShop";
    display: block;
    margin: 2px 14px 22px;
    color: #f8fafc;
    font-family: var(--font-ui);
    font-size: 1.2rem;
    font-weight: 700;
  }
  .admin-nav-item {
    justify-content: flex-start;
    min-height: 46px;
    padding: 0 14px;
    border-radius: var(--radius-sm);
  }
  .admin-nav-item--active {
    box-shadow: inset 3px 0 0 var(--color-steel-blue);
  }
}

@media (max-width: 960px) {
  .admin-content {
    background: var(--color-ink);
  }
  .admin-navigation {
    background: var(--color-navy-deep);
  }
  .admin-section,
  .form-panel,
  .metric-card,
  .insight-panel,
  .settings-panel {
    background: var(--color-navy-deep);
  }
  .admin-navigation::before {
    display: none;
  }
}
@media (max-width: 960px) {
  .form-panel {
    position: static;
  }
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .admin-content {
    padding: 28px 12px 100px;
  }
  .admin-intro {
    margin-bottom: 24px;
  }
  .admin-intro h1 {
    font-size: 2.25rem;
  }
  .admin-section,
  .form-panel,
  .insight-panel,
  .upcoming-panel {
    padding: 18px;
  }
  .dashboard-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .dashboard-toolbar h2 {
    font-size: 1.75rem;
  }
  .period-toggle {
    width: 100%;
  }
  .period-toggle :deep(.v-btn) {
    flex: 1;
    min-width: 0;
    padding-inline: 6px;
    font-size: 0.74rem;
  }
  .admin-navigation {
    position: fixed;
    z-index: 10;
    right: 0;
    bottom: 0;
    left: 0;
    display: flex;
    width: auto;
    grid-template-columns: none;
    gap: 2px;
    margin: 0;
    padding: 6px max(6px, env(safe-area-inset-left))
      max(6px, env(safe-area-inset-bottom));
    overflow-x: auto;
    border-width: 1px 0 0;
  }
  .admin-nav-item {
    min-width: 88px;
    min-height: 56px;
    flex: 0 0 88px;
    flex-direction: column;
    gap: 2px;
    padding-inline: 4px;
    font-size: 0.66rem;
  }
  .admin-nav-item .v-icon {
    display: block;
  }
  .admin-nav-item--active {
    box-shadow: inset 0 3px 0 var(--color-steel-blue);
  }
  .service-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .row-actions {
    width: 100%;
    justify-content: flex-end;
  }
  .day-label {
    min-width: 100%;
  }
  .day-period {
    flex-basis: 100%;
  }
  .day-period :deep(.v-input) {
    flex: 1;
  }
  .metrics-grid,
  .filter-bar,
  .dashboard-insights {
    grid-template-columns: 1fr;
  }
  .insight-panel--heatmap {
    grid-column: auto;
  }
  .upcoming-row {
    grid-template-columns: 56px minmax(0, 1fr) auto;
    gap: 10px;
  }
  .upcoming-row .appointment-status {
    grid-column: 2;
  }
  .upcoming-price {
    grid-column: 3;
    grid-row: 1 / span 2;
  }
  .appointment-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .appointment-row-actions {
    width: 100%;
    justify-content: space-between;
  }
  .manual-slots {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .admin-navigation {
    display: flex;
  }
  .admin-nav-item--desktop-only {
    display: none;
  }
  .admin-nav-more {
    display: flex;
    min-width: 88px;
    min-height: 56px;
    flex: 0 0 88px;
    flex-direction: column;
    gap: 2px;
    padding-inline: 4px;
    font-size: 0.66rem;
  }
  .admin-nav-more[aria-expanded="true"] {
    box-shadow: inset 0 3px 0 var(--color-steel-blue);
    background: rgba(var(--color-steel-blue-rgb), 0.16);
  }
}

/* Refinamento dos blocos de gestão: leitura rápida, estados claros e toque confortável. */
.service-row,
.customer-row,
.day-row,
.exception-row {
  margin: 8px 0;
  padding: 16px;
  border: 1px solid rgba(var(--color-slate-rgb), 0.18);
  border-radius: var(--radius-sm);
  background: rgba(var(--color-ink-rgb), 0.2);
}
.service-row:last-child,
.customer-row:last-child,
.day-row:last-child,
.exception-row:last-child {
  border-bottom: 1px solid rgba(var(--color-slate-rgb), 0.18);
}
.service-row:hover,
.customer-row:hover,
.day-row:hover,
.exception-row:hover {
  border-color: rgba(var(--color-steel-blue-rgb), 0.55);
  background: rgba(var(--color-steel-blue-rgb), 0.1);
}
.service-row--inactive,
.customer-row--inactive {
  opacity: 0.58;
}
.service-row strong,
.customer-row strong {
  font-size: 0.96rem;
  letter-spacing: 0.01em;
}
.service-row span,
.customer-row span {
  color: var(--color-slate);
}
.row-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}
.row-actions :deep(.v-btn) {
  min-height: 40px;
  border-radius: var(--radius-sm);
  color: var(--color-paper);
  text-transform: none;
}
.row-actions :deep(.v-chip) {
  border-color: rgba(var(--color-steel-blue-rgb), 0.58);
  color: var(--color-steel-blue);
}
.day-row {
  gap: 12px;
}
.day-label {
  color: var(--color-paper);
  font-size: 0.9rem;
}
.day-period {
  padding: 8px;
  border: 1px solid rgba(var(--color-slate-rgb), 0.16);
  border-radius: var(--radius-sm);
  background: rgba(var(--color-navy-deep-rgb), 0.5);
}
.settings-panel,
.form-panel {
  box-shadow: 0 12px 30px rgba(var(--color-ink-rgb), 0.18);
}
.settings-panel .v-btn,
.form-panel .v-btn {
  min-height: 44px;
}
.settings-panel {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: 28px;
}
.settings-panel h2 {
  margin-bottom: 28px;
}
.settings-panel > .v-text-field {
  margin-bottom: 8px;
}
.settings-panel > .v-row {
  margin: 0 -6px;
}
.settings-panel > .v-row > .v-col {
  padding: 0 6px;
}
.settings-panel > .v-btn {
  align-self: flex-start;
  min-width: 210px;
  margin-top: auto;
}
.settings-panel :deep(.v-field) {
  min-height: 54px;
  border-radius: var(--radius-btn);
}
.settings-panel :deep(.v-field__input) {
  min-height: 52px;
}
.settings-panel :deep(.v-label) {
  font-size: 0.82rem;
}
.settings-panel :deep(.v-messages) {
  min-height: 18px;
}
.settings-panel--dark :deep(.v-field) {
  background: rgba(var(--color-ink-rgb), 0.28);
}
.exception-row {
  align-items: flex-start;
}
.exception-row .v-btn {
  flex: 0 0 auto;
  min-height: 40px;
  color: var(--color-slate);
  text-transform: none;
}
@media (max-width: 600px) {
  .service-row,
  .customer-row,
  .day-row,
  .exception-row {
    margin: 8px 0;
    padding: 14px;
  }
  .row-actions {
    justify-content: flex-start;
  }
  .day-period {
    flex-wrap: wrap;
  }
  .day-period :deep(.v-checkbox) {
    flex: 1 0 100%;
  }
  .exception-row {
    flex-direction: column;
  }
  .exception-row .v-btn {
    align-self: flex-start;
  }
}
/* Calendário operacional inspirado na referência visual. */
.calendar-column {
  position: relative;
}
.legacy-appointments {
  display: none !important;
}
.calendar-shell,
.appointments-list-shell {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(var(--color-slate-rgb), 0.24);
  border-radius: 12px;
  padding: 24px;
  background: linear-gradient(145deg, #111a2b, #0d1524);
}
.view-toggle {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid rgba(91, 115, 187, 0.62);
  border-radius: 9px;
  background: rgba(16, 25, 46, 0.9);
}
.view-toggle .v-btn {
  min-height: 42px;
  border-radius: 0;
  color: #aab8db;
  text-transform: none;
}
.view-toggle .view-toggle-active {
  background: linear-gradient(135deg, #8b5cf6, #2563eb);
  color: #fff;
}
.list-view-button {
  border-color: rgba(142, 103, 255, 0.72) !important;
  color: #d8ccff !important;
  text-transform: none;
}
.list-toolbar {
  margin-bottom: 20px;
}
.list-filter-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 10px;
  margin-bottom: 18px;
}
.list-filter-row :deep(.v-field) {
  background: rgba(var(--color-ink-rgb), 0.34);
}
.appointments-list {
  display: grid;
  gap: 10px;
}
.appointment-list-card {
  display: grid;
  grid-template-columns: 42px minmax(150px, 1.2fr) minmax(
      130px,
      1fr
    ) 110px 90px auto auto;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  padding: 12px 14px;
  border: 1px solid rgba(var(--color-slate-rgb), 0.24);
  border-radius: 9px;
  background: rgba(24, 34, 53, 0.92);
  transition:
    transform var(--motion-fast),
    border-color var(--motion-fast),
    background var(--motion-fast);
}
.appointment-list-card:hover {
  border-color: rgba(121, 102, 255, 0.72);
  background: rgba(31, 43, 68, 0.98);
  transform: translateY(-1px);
}
.appointment-list-avatar {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 2px solid rgba(112, 132, 255, 0.8);
  border-radius: 50%;
  background: linear-gradient(135deg, #7652d6, #3d8dbd);
  color: white;
  font-weight: 700;
}
.appointment-list-person strong,
.appointment-list-person small,
.appointment-list-field span,
.appointment-list-field strong,
.appointment-list-field small {
  display: block;
}
.appointment-list-person strong,
.appointment-list-field strong {
  color: var(--color-paper);
  font-size: 0.82rem;
}
.appointment-list-person small,
.appointment-list-field span,
.appointment-list-field small {
  margin-top: 4px;
  color: var(--color-slate);
  font-size: 0.68rem;
}
.appointment-list-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}
.appointment-list-actions > button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid rgba(120, 105, 245, 0.42);
  border-radius: 5px;
  background: rgba(83, 66, 153, 0.22);
  color: #d9ceff;
  cursor: pointer;
}
.appointment-list-actions > button:hover {
  background: #7652d6;
}
.appointment-list-card .appointment-status {
  white-space: nowrap;
}
.calendar-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.calendar-toolbar h2 {
  margin: 0;
  color: var(--color-paper);
  font-size: clamp(1.45rem, 3vw, 2rem);
  font-weight: 700;
}
.calendar-toolbar span {
  color: var(--color-slate);
  font-size: 0.82rem;
}
.calendar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.calendar-actions strong {
  color: var(--color-paper);
  min-width: 130px;
  text-align: center;
}
.calendar-actions .v-btn {
  text-transform: none;
  border-radius: 8px;
}
.new-appointment-button {
  background: linear-gradient(135deg, #8a4dff, #b458f5) !important;
  color: white !important;
}
.clients-toggle-button {
  border-color: #647dfd !important;
  color: #dce2ff !important;
  box-shadow: 0 0 0 2px rgba(100, 125, 253, 0.16);
}
.calendar-legend {
  display: flex;
  gap: 20px;
  margin: 10px 0 16px 84px;
  color: var(--color-slate);
  font-size: 0.76rem;
}
.calendar-legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.legend-dot--confirmed {
  background: #ec5d72;
}
.legend-dot--available {
  background: #43bd94;
}
.legend-dot--pending {
  background: #e7a34f;
}
.calendar-board {
  display: grid;
  grid-template-columns: 68px repeat(7, minmax(110px, 1fr));
  min-width: 880px;
  border: 1px solid rgba(var(--color-slate-rgb), 0.22);
  border-radius: 10px;
  overflow: auto;
}
.calendar-corner,
.calendar-day-header,
.calendar-time,
.calendar-cell {
  border-right: 1px solid rgba(var(--color-slate-rgb), 0.16);
  border-bottom: 1px solid rgba(var(--color-slate-rgb), 0.16);
}
.calendar-corner,
.calendar-day-header {
  min-height: 52px;
  padding: 10px;
  background: rgba(25, 37, 59, 0.9);
  color: var(--color-slate);
  font-size: 0.72rem;
}
.calendar-day-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-transform: uppercase;
}
.calendar-day-header strong {
  color: var(--color-paper);
  font-size: 1rem;
}
.calendar-day-header--today {
  background: rgba(93, 138, 196, 0.2);
  box-shadow: inset 0 -2px var(--color-steel-blue);
}
.calendar-time {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12px;
  color: var(--color-slate);
  font-size: 0.7rem;
  background: rgba(12, 20, 34, 0.82);
}
.calendar-cell {
  position: relative;
  min-height: 74px;
  padding: 4px;
  background: rgba(13, 21, 36, 0.78);
}
.calendar-cell:hover {
  background: rgba(93, 138, 196, 0.08);
}
.calendar-add {
  width: 100%;
  height: 100%;
  min-height: 64px;
  border: 0;
  background: transparent;
  color: rgba(148, 111, 255, 0.8);
  font-size: 1.2rem;
  opacity: 0;
  cursor: pointer;
}
.calendar-cell:hover .calendar-add {
  opacity: 1;
}
.calendar-appointment {
  display: flex;
  min-height: 62px;
  width: 100%;
  flex-direction: column;
  align-items: flex-start;
  padding: 7px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: var(--color-paper);
  text-align: left;
  cursor: pointer;
}
.calendar-appointment strong {
  overflow: hidden;
  max-width: 100%;
  font-size: 0.72rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.calendar-appointment span,
.calendar-appointment small {
  color: rgba(255, 255, 255, 0.68);
  font-size: 0.62rem;
}
.calendar-appointment small {
  overflow: hidden;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.calendar-appointment--confirmed {
  border-color: rgba(236, 93, 114, 0.75);
  background: rgba(151, 44, 69, 0.28);
}
.calendar-appointment--pending {
  border-color: rgba(231, 163, 79, 0.75);
  background: rgba(130, 84, 28, 0.28);
}
.calendar-appointment--completed {
  border-color: rgba(67, 189, 148, 0.75);
  background: rgba(25, 108, 82, 0.28);
}
.calendar-appointment--cancelled {
  opacity: 0.55;
  border-color: rgba(139, 150, 168, 0.55);
  background: rgba(139, 150, 168, 0.12);
}
.clients-panel {
  position: absolute;
  z-index: 2;
  top: 94px;
  right: 24px;
  width: min(360px, calc(100% - 48px));
  max-height: calc(100% - 118px);
  overflow: auto;
  padding: 20px;
  border: 1px solid rgba(111, 128, 255, 0.62);
  border-radius: 12px;
  background: #171f31;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.42);
}
.clients-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.clients-panel h3 {
  margin: 0;
  color: var(--color-paper);
  font-size: 1.2rem;
}
.clients-panel-header span {
  color: var(--color-slate);
  font-size: 0.75rem;
}
.client-list {
  margin-top: 12px;
}
.client-list-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(var(--color-slate-rgb), 0.15);
}
.client-list-row strong,
.client-list-row small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.client-list-row strong {
  color: var(--color-paper);
  font-size: 0.82rem;
}
.client-list-row small {
  margin-top: 3px;
  color: var(--color-slate);
  font-size: 0.68rem;
}
.client-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #7f57d6, #3d8dbd);
  color: white;
  font-weight: 700;
}
.client-list-row .v-btn {
  min-height: 32px;
  padding-inline: 10px;
  color: #c5d1ff;
  border-color: rgba(111, 128, 255, 0.65);
  font-size: 0.7rem;
  text-transform: none;
}
@media (max-width: 900px) {
  .calendar-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .calendar-actions {
    justify-content: flex-start;
  }
  .calendar-legend {
    margin-left: 0;
  }
}
@media (max-width: 900px) {
  .list-filter-row {
    grid-template-columns: 1fr 1fr;
  }
  .list-filter-row .v-btn {
    grid-column: 1 / -1;
  }
  .appointment-list-card {
    grid-template-columns: 42px minmax(0, 1fr) auto;
  }
  .appointment-list-field {
    display: none;
  }
  .appointment-list-card .appointment-status {
    grid-column: 2;
  }
  .appointment-list-actions {
    grid-column: 3;
    grid-row: 1 / span 2;
  }
}
@media (max-width: 600px) {
  .calendar-shell,
  .appointments-list-shell {
    padding: 16px 10px;
  }
  .calendar-actions {
    width: 100%;
  }
  .calendar-actions strong {
    order: -1;
    width: 100%;
    text-align: left;
  }
  .calendar-actions .v-btn {
    flex: 1;
  }
  .clients-panel {
    top: 130px;
    right: 10px;
    width: calc(100% - 20px);
  }
  .list-filter-row {
    grid-template-columns: 1fr;
  }
  .list-filter-row .v-btn {
    grid-column: auto;
  }
  .appointment-list-card {
    grid-template-columns: 38px minmax(0, 1fr) auto;
    padding: 10px;
  }
  .appointment-list-avatar {
    width: 38px;
    height: 38px;
  }
  .appointment-list-person strong {
    font-size: 0.76rem;
  }
}
.calendar-appointment-wrap {
  position: relative;
  height: 100%;
}
.calendar-appointment-wrap--dragging {
  opacity: 0.45;
  transform: scale(0.98);
}
.calendar-appointment-wrap--target {
  border-top: 3px solid #9d78ff;
  padding-top: 2px;
}
.calendar-appointment[draggable="true"] {
  cursor: grab;
}
.calendar-appointment[draggable="true"]:active {
  cursor: grabbing;
}
.reorder-controls {
  position: absolute;
  top: 3px;
  right: 3px;
  display: flex;
  opacity: 0;
  transition: opacity var(--motion-fast);
}
.calendar-appointment-wrap:hover .reorder-controls,
.calendar-appointment-wrap:focus-within .reorder-controls {
  opacity: 1;
}
.reorder-controls button {
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  border: 0;
  border-radius: 4px;
  background: rgba(8, 12, 22, 0.72);
  color: var(--color-paper);
  cursor: pointer;
}
.reorder-controls button:hover {
  background: #8057e8;
}
.reorder-dialog p {
  margin: 0 0 12px;
  color: var(--color-slate);
}
.reorder-dialog p strong,
.reorder-dialog li strong {
  color: var(--color-paper);
}
.reorder-affected-list {
  margin: 0 0 14px;
  padding-left: 20px;
  color: var(--color-slate);
  font-size: 0.86rem;
}
.reorder-affected-list li {
  margin: 5px 0;
}
.dialog-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.dialog-title-row .v-btn {
  color: var(--color-slate);
}
.appointment-details-dialog,
.appointment-booking-dialog {
  border: 1px solid rgba(96, 125, 255, 0.7) !important;
  border-radius: 12px !important;
  background: #111d39 !important;
  color: var(--color-paper);
}
.appointment-detail-person {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}
.detail-avatar {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6, #2563eb);
  color: #fff;
  font-size: 1.25rem;
  font-weight: 700;
}
.appointment-detail-person h3 {
  margin: 0;
  color: var(--color-paper);
}
.appointment-detail-person span,
.dialog-helper {
  color: var(--color-slate);
  font-size: 0.8rem;
}
.appointment-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.appointment-detail-grid div {
  padding: 12px;
  border: 1px solid rgba(139, 150, 168, 0.2);
  border-radius: 8px;
  background: rgba(5, 12, 29, 0.35);
}
.appointment-detail-grid small,
.detail-notes small {
  display: block;
  margin-bottom: 5px;
  color: var(--color-slate);
  font-size: 0.7rem;
}
.appointment-detail-grid strong {
  color: var(--color-paper);
  font-size: 0.84rem;
}
.detail-notes {
  margin: 16px 0 0;
  color: var(--color-paper);
}
.detail-actions {
  padding-top: 4px;
}
.appointment-booking-dialog :deep(.v-field) {
  background: rgba(5, 12, 29, 0.35);
}
.appointment-booking-dialog :deep(.v-label),
.appointment-booking-dialog :deep(input),
.appointment-booking-dialog :deep(textarea) {
  color: var(--color-paper);
}
@media (min-width: 961px) {
  .admin-content {
    padding: 36px 32px 72px 256px;
    background: #060b1c;
  }
  .admin-container {
    width: 100%;
    max-width: none;
    margin: 0;
    padding: 0;
  }
  .admin-intro {
    margin-bottom: 28px;
  }
  .admin-intro .section-kicker,
  .admin-intro .logout-button {
    display: none;
  }
  .admin-intro h1 {
    font-family: var(--font-ui);
    font-size: 2rem;
    font-weight: 700;
  }
  .admin-navigation {
    width: 224px;
    background: #0c0b1d;
    border-color: rgba(139, 92, 246, 0.12);
  }
  .admin-nav-item--active {
    background: linear-gradient(90deg, #7139ed, #4c43d9);
    border-color: rgba(167, 139, 250, 0.45);
    box-shadow: 0 8px 20px rgba(109, 67, 235, 0.24);
  }
  .calendar-shell,
  .appointments-list-shell {
    padding: 18px;
    border-color: #203867;
    background: linear-gradient(145deg, #0b1734, #071126);
  }
  .calendar-toolbar {
    align-items: center;
  }
  .calendar-toolbar h2 {
    font-size: 1.75rem;
  }
  .calendar-actions {
    max-width: 690px;
  }
  .calendar-board {
    min-width: 760px;
  }
  .form-panel.manual-panel {
    border: 1px solid #2563eb;
    border-radius: 12px;
    background: linear-gradient(160deg, #101d3c, #0a142c);
    box-shadow: -8px 0 28px rgba(37, 99, 235, 0.12);
  }
  .manual-panel-heading {
    margin-bottom: 20px;
  }
  .manual-panel .save-button {
    background: linear-gradient(90deg, #a84af1, #2563eb) !important;
    border-radius: 10px !important;
  }
  .calendar-column + .legacy-appointments + .v-col {
    min-width: 0;
  }
}
@media (min-width: 961px) {
  .admin-content {
    min-height: calc(100dvh - 78px);
    padding: 36px 24px 72px 318px;
  }
  .admin-navigation {
    top: 0;
    width: 280px;
    padding: 24px 15px;
    background: linear-gradient(180deg, #0b0a1b 0%, #09091a 100%);
  }
  .admin-navigation::before {
    content: "BarberShop";
    margin: 8px 48px 2px;
    font-size: 1.18rem;
    white-space: nowrap;
  }
  .admin-navigation::after {
    content: "Sistema de Gestão";
    display: block;
    margin: 0 48px 30px;
    color: #7482ae;
    font-size: 0.68rem;
    white-space: nowrap;
  }
  .admin-nav-item {
    min-height: 52px;
    padding: 0 18px;
    border-radius: 9px;
    font-size: 0.86rem;
  }
  .admin-nav-item--active {
    background: linear-gradient(100deg, #7540f0, #4c42d7);
  }
  .admin-intro {
    margin-bottom: 28px;
  }
  .admin-intro h1 {
    font-size: 2rem;
  }
  .calendar-column {
    min-width: 0;
  }
  .appointments-list-shell {
    min-height: 680px;
  }
  .appointment-list-card {
    min-height: 78px;
  }
  .form-panel.manual-panel {
    min-height: 680px;
  }
  .calendar-column + .legacy-appointments + .v-col {
    min-width: 0;
  }
}
.appointment-list-card {
  touch-action: pan-y;
  user-select: none;
}
.appointment-edit-form {
  display: grid;
  gap: 14px;
}
.appointment-edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.appointment-edit-actions {
  border-top: 1px solid rgba(139, 150, 168, 0.18);
}
.appointment-details-dialog {
  overflow: hidden;
}
.appointment-details-dialog .v-card-title {
  padding: 22px 24px 14px;
  font-size: 1.2rem;
  font-weight: 700;
}
.appointment-details-dialog .v-card-text {
  padding: 14px 24px 20px;
}
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 24px 22px;
}
.detail-actions .v-spacer {
  display: none;
}
.detail-actions .v-btn {
  min-height: 42px;
  flex: 1 1 auto;
  white-space: nowrap;
}
.appointment-edit-actions .v-btn {
  min-width: 170px;
}
.complete-button {
  background: linear-gradient(135deg, #159a68, #087f58) !important;
  color: #fff !important;
}
.appointment-list-card--completed {
  border-color: rgba(34, 197, 94, 0.68);
  background: rgba(20, 83, 45, 0.3);
}
.appointment-list-card--completed:hover {
  border-color: rgba(74, 222, 128, 0.85);
  background: rgba(20, 98, 53, 0.38);
}
</style>
