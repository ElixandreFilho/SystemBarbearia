# BARBEARIA_SYSTEM_SPEC.md

**Versão:** 1.0
**Status:** Especificação de arquitetura — fonte de verdade para implementação
**Stack-alvo:** Vue 3 + TypeScript + Vuetify (frontend) · Python/FastAPI + PostgreSQL (backend) · Cloudflare + Resend + Sentry (infra/observabilidade)

> Este documento assume o papel de arquiteto sênior responsável pela decisão técnica final. Onde a regra original era ambígua ou tecnicamente frágil, a ambiguidade é sinalizada explicitamente com **[DECISÃO]** e a solução escolhida é justificada. Nada aqui é implementado ainda — este é o contrato técnico que o Codex vai seguir, fase a fase.

---

## Sumário

1. Visão geral do sistema
2. Requisitos funcionais
3. Requisitos não funcionais
4. Regras de negócio (com decisões sobre ambiguidades)
5. Arquitetura
6. Stack final recomendada
7. Estrutura de pastas
8. Modelo de dados
9. Diagrama textual das entidades
10. Endpoints REST
11. Fluxos principais
12. Estratégia de autenticação
13. Estratégia de agendamento
14. Estratégia anti-overbooking
15. Estratégia de notificações
16. Estratégia de segurança
17. Estratégia de testes
18. Estratégia de observabilidade
19. Estratégia de deploy
20. Configuração Cloudflare
21. Configuração Resend
22. Configuração Sentry
23. Variáveis de ambiente
24. Checklist de produção
25. Roadmap de implementação por fases
26. Plano executável para o Codex (tarefas verificáveis)

---

## 1. Visão geral do sistema

Sistema web de agendamento para **uma barbearia** (single-tenant, não é um SaaS multi-barbearia nesta fase — ver decisão abaixo), com dois perfis de acesso: **ADMIN** (dono/barbeiro) e **CLIENTE**.

O núcleo do produto é o motor de disponibilidade: transformar duração de serviços + horário de funcionamento + capacidade simultânea + exceções (folgas, feriados, bloqueios) em uma lista confiável de horários agendáveis, sem jamais permitir overbooking — mesmo sob concorrência real.

**[DECISÃO] Single-tenant vs. multi-tenant.** A especificação fala sempre de "a barbearia" no singular. Modelar como multi-tenant desde já adicionaria uma coluna `barbershop_id` em quase toda tabela sem necessidade real hoje. Decisão: construir single-tenant (uma linha de configurações `BarbershopSettings`), mas isolar toda a lógica de disponibilidade/configuração atrás de um módulo `schedule` de forma que, se um dia for necessário suportar múltiplas unidades, a migração seja "adicionar uma FK", não "reescrever o motor de agendamento".

**Fora de escopo nesta fase (roadmap futuro):** pagamento online, múltiplos barbeiros/profissionais com agendas independentes, app nativo, integração WhatsApp/SMS real (a arquitetura já deixa o gancho pronto), **lembrete automático antes do atendimento** (removido a pedido — ver [DECISÃO] na seção 15: exigiria um processo rodando continuamente, e portanto hospedagem *always-on* paga).

---

## 2. Requisitos funcionais

### RF — Autenticação (ambos os perfis)
- RF01: Cadastro de cliente com nome + (e-mail e/ou telefone) + senha.
- RF02: Login por e-mail ou telefone + senha.
- RF03: Logout com revogação de sessão.
- RF04: Recuperação de senha por e-mail (token com expiração).
- RF05: Edição dos próprios dados (nome, e-mail, telefone, senha).

### RF — Admin
- RF10: Login administrativo (mesma tabela de usuários, role `ADMIN`).
- RF11: CRUD de clientes (criar manualmente, listar, editar, desativar).
- RF12: CRUD de serviços (nome, descrição, preço, duração).
- RF13: Visualizar agenda (dia/semana) com todos os agendamentos.
- RF14: Criar agendamento manual para qualquer data/cliente (ignora janela de 2 dias).
- RF15: Editar/reagendar agendamento existente.
- RF16: Cancelar qualquer agendamento, com motivo.
- RF17: Marcar agendamento como concluído ou no-show.
- RF18: Consultar histórico de agendamentos (filtros por cliente/data/status).
- RF19: Configurar horário de funcionamento por dia da semana, incluindo múltiplos intervalos (ex.: manhã/tarde com pausa de almoço).
- RF20: Configurar capacidade simultânea da barbearia.
- RF21: Cadastrar/editar/remover feriados e datas especiais (com horário customizado ou fechamento total).
- RF22: Bloquear/desbloquear horários pontuais (ex.: manutenção, compromisso pessoal).
- RF23: Visualizar dashboard com indicadores do dia/semana.

### RF — Cliente
- RF30: Consultar catálogo de serviços com preço e duração.
- RF31: Selecionar um ou mais serviços e ver a duração/preço total somados.
- RF32: Consultar horários disponíveis para uma data dentro da janela permitida (hoje, +1, +2 dias).
- RF33: Criar agendamento em um horário disponível.
- RF34: Visualizar seus próprios agendamentos (futuros e histórico).
- RF35: Cancelar o próprio agendamento futuro.
- RF36: Receber confirmação de agendamento e de cancelamento por e-mail.

---

## 3. Requisitos não funcionais

- **RNF01 — Confiabilidade de agenda:** zero overbooking sob concorrência, garantido por mecanismo transacional no banco (não apenas validação de aplicação).
- **RNF02 — Mobile-first:** uso majoritário em celular; interface Vuetify responsiva, testada em Android/iOS/tablet/desktop.
- **RNF03 — Performance:** TTI < 3s em 4G médio; consultas de disponibilidade < 300ms p95; paginação em todas as listagens administrativas.
- **RNF04 — Segurança:** conformidade com OWASP Top 10; nenhuma regra de negócio confiável apenas no frontend.
- **RNF05 — Privacidade (LGPD):** dados pessoais (nome, e-mail, telefone) tratados como dado pessoal; minimização de dados enviados a serviços terceiros (Sentry não recebe PII); cliente pode solicitar exclusão de conta.
- **RNF06 — Disponibilidade:** backend 100% stateless, apto a rodar com múltiplas réplicas ou até "dormir" em inatividade (free tier) sem quebrar nenhuma funcionalidade — não há processo de background contínuo no sistema (ver decisão na seção 15).
- **RNF07 — Observabilidade:** todo erro não tratado chega ao Sentry com contexto suficiente para debugar sem reproduzir localmente.
- **RNF08 — Baixo custo operacional:** arquitetura deve caber em provedores gratuitos/baixo custo adequados a uma pequena barbearia (seção 19).
- **RNF09 — Extensibilidade de notificação:** adicionar um canal novo (WhatsApp/SMS) não deve exigir alterar código de negócio, apenas implementar uma nova classe de canal.
- **RNF10 — Auditabilidade:** ações administrativas sensíveis (cancelar agendamento de terceiro, alterar preço, alterar horário de funcionamento) ficam registradas em log de auditoria.

---

## 4. Regras de negócio (com decisões sobre ambiguidades)

### 4.1 Duração e soma de serviços
- Cada serviço tem `duration_minutes` fixo, definido pelo admin.
- Ao escolher múltiplos serviços, a duração total do agendamento é a **soma** das durações individuais. Preço total também é a soma.
- O agendamento reserva um único bloco contínuo de tempo igual à soma (ex.: corte 30min + barba 45min → bloco de 75min), nunca dois blocos separados.

### 4.2 Capacidade e granularidade dos horários
**[DECISÃO] Granularidade dos slots.** A especificação não define de quanto em quanto tempo os horários "começam" (a cada 30min? a cada serviço?). Se os horários de início forem sempre múltiplos fixos da duração de UM serviço, um serviço de 45min mal se encaixa em uma grade de 30min. Decisão: usar uma **grade de granularidade configurável** (padrão: 15 minutos) para os horários de início candidatos. Isso permite que um corte de 30min comece às 08:00, 08:15, 08:30 etc., e que a soma de dois serviços (ex.: 75min) também respeite a grade sem desperdiçar encaixes possíveis. A duração real de cada serviço continua sendo exatamente a cadastrada — só o *início* é quantizado.

- A disponibilidade nunca é "N clientes por horário fixo": é calculada por **sobreposição de intervalos**. Um horário `[start, start+duration)` só é oferecido se, em **todo instante** desse intervalo, o número de agendamentos ativos (`PENDING` ou `CONFIRMED`) sobrepostos for menor que a capacidade configurada (`BarbershopSettings.capacity`).
- Exemplo do enunciado (capacidade 2): Cliente A 08:00–08:30 e Cliente B 08:00–08:30 → 08:00 fica cheio para qualquer serviço que sobreponha esse intervalo; 08:30 continua livre normalmente.

### 4.3 Janela de agendamento do cliente
**[DECISÃO] Interpretação de "no próprio dia até dois dias antes".** Interpretado como: o cliente pode agendar para **hoje (D+0), amanhã (D+1) ou depois de amanhã (D+2)** — uma janela corrida de 3 dias incluindo hoje. Essa regra é validada **no backend**, no endpoint de criação de agendamento e no de disponibilidade, comparando com a data/hora atual do servidor (timezone da barbearia, não do cliente). O ADMIN não tem esse limite ao criar/editar manualmente.

### 4.4 Horário de funcionamento e intervalos
**[DECISÃO] Modelagem de intervalos (pausa/almoço).** Em vez de um único par `open_time`/`close_time` por dia da semana (que não suporta pausa no meio do dia sem gambiarra), `BusinessHours` permite **múltiplas linhas por dia da semana**, cada uma um intervalo de funcionamento. Ex.: terça-feira = duas linhas (08:00–12:00) e (13:00–19:00) → o "buraco" das 12:00–13:00 é automaticamente não-agendável, sem precisar de um campo `break_start/break_end` separado. Um dia totalmente fechado (ex.: segunda) simplesmente não tem nenhuma linha.

### 4.5 Feriados e datas especiais
- `SpecialDate` sobrepõe `BusinessHours` para uma data específica: pode marcar fechamento total (`is_closed=true`) ou horário especial (`custom_open_time/custom_close_time`).
- Cadastro/edição/remoção livre pelo admin — nunca hardcoded.

### 4.6 Bloqueios pontuais
- `BlockedSlot` bloqueia um intervalo específico numa data específica (ex.: 14:00–15:00 de um dia normal), sem afetar o resto do dia. Reversível (admin pode remover o bloqueio).

### 4.7 Cancelamento e ciclo de vida do agendamento
- Estados: `PENDING → CONFIRMED → COMPLETED`, com desvios possíveis para `CANCELLED` (a partir de `PENDING`/`CONFIRMED`) e `NO_SHOW` (a partir de `CONFIRMED`, após o horário passar sem check-in).
- **[DECISÃO] PENDING vs. CONFIRMED.** A especificação não detalha um fluxo de confirmação separado do admin. Decisão pragmática: agendamento criado pelo cliente nasce já como `CONFIRMED` (não há pagamento/aprovação manual nesta fase — exigir aprovação manual do admin para cada reserva feita pelo celular seria fricção desnecessária para uma barbearia pequena). O estado `PENDING` fica reservado para casos futuros (ex.: agendamento que depende de pagamento antecipado). Isso é uma convenção de aplicação, não uma restrição de banco — pode mudar sem migração.
- Cancelamento nunca apaga a linha (soft state change), preservando histórico e permitindo métricas de cancelamento no dashboard.
- **[DECISÃO] Prazo mínimo de cancelamento.** Não especificado pelo usuário. Recomendação: campo configurável `BarbershopSettings.min_cancellation_notice_minutes` (padrão 60min) — cliente não pode cancelar via app dentro dessa janela (precisa contatar a barbearia); admin sempre pode cancelar. Isso evita cancelamentos de última hora que deixam o horário vago sem chance de realocação, mas fica documentado como *recomendação*, ajustável/desligável (`0` = sem restrição) caso o dono prefira não ter essa fricção.
- **[DECISÃO] Marcação de No-Show — sem job em background.** Não especificado pelo usuário, e decidido **sem depender de nenhum processo agendado** (ver 4.8 abaixo, sobre a remoção do lembrete por custo). Em vez de um job periódico marcando `NO_SHOW` automaticamente, o status é **calculado sob demanda**: sempre que a agenda é consultada (`GET /admin/appointments`), qualquer agendamento `CONFIRMED` cujo horário de término já passou há mais de `no_show_grace_minutes` (configurável, padrão 30min) é exibido na tela com uma sinalização visual "possível no-show" — sem alterar o banco. O admin confirma com um clique (`PATCH .../no-show`), que aí sim persiste o estado. Isso remove por completo a necessidade de um processo contínuo rodando no servidor.

### 4.8 Lembrete antes do atendimento — removido por decisão do cliente
**[DECISÃO] Sem lembrete automático.** O pedido original previa notificar o cliente ~20 minutos antes do horário. Essa funcionalidade foi **removida a pedido explícito**, porque só é possível de forma confiável com um processo rodando continuamente em segundo plano (scheduler verificando o relógio a cada minuto) — o que, por sua vez, exige um plano de hospedagem *always-on* (sem "dormir" por inatividade), gerando custo mensal fixo. Sem essa exigência, o backend inteiro pode rodar em infraestrutura sob demanda/gratuita (seção 19). Se um dia fizer sentido reativar, é um acréscimo isolado — a arquitetura de notificações (seção 15) já foi desenhada para plugar um canal/gatilho novo sem tocar nas regras de agendamento.

---

## 5. Arquitetura

**Estilo:** monólito modular (não microserviços). Para o porte de uma barbearia, microserviços adicionariam custo operacional e complexidade de deploy sem benefício real — o motor de disponibilidade principal já é isolado como módulo interno, então dividir em serviços depois (se um dia crescer para uma rede de unidades) é uma extração, não uma reescrita.

```
┌────────────────────┐        HTTPS         ┌──────────────────────────┐
│  Cliente (Vue 3     │  ───────────────────▶│  Cloudflare (DNS, CDN,   │
│  SPA + PWA)          │◀───────────────────  │  WAF, cache, HTTPS)      │
└────────────────────┘                        └──────────────┬───────────┘
                                                               │
                                       ┌───────────────────────┼───────────────────────┐
                                       ▼                                               ▼
                          ┌─────────────────────────┐                    ┌──────────────────────────┐
                          │ Cloudflare Pages          │                    │ API FastAPI (Render,      │
                          │ (build estático do Vue)   │                    │ Render), atrás de proxy   │
                          └─────────────────────────┘                    │ Cloudflare (api.dominio)  │
                                                                          └───────────┬───────────────┘
                                                                                      │
                                                       ┌──────────────────────────────┐
                                                       ▼                              ▼
                                          ┌─────────────────────┐          ┌─────────────────────┐
                                          │ PostgreSQL gerenciado │          │ Serviços externos    │
                                          │ (Neon, tier gratuito) │          │ Resend (e-mail)       │
                                          │                      │          │ Sentry (erros)        │
                                          └─────────────────────┘          └─────────────────────┘
```

Sem processo de background contínuo: toda notificação (confirmação, cancelamento, reset de senha) é disparada **na hora**, dentro da própria requisição HTTP que originou o evento — não há scheduler para hospedar nem manter no ar.

Camadas do backend (dentro do monólito):
`api` (routers/HTTP) → `services` (regras de negócio) → `repositories` (acesso a dados via SQLAlchemy) → `models` (entidades). O motor de agendamento (`scheduling/availability.py` + `scheduling/booking.py`) é a peça mais crítica e a mais coberta por testes.

---

## 6. Stack final recomendada

**Frontend**
- Vue 3 (Composition API) + TypeScript
- Vuetify 3 (Design System, Material Design)
- Vite
- Pinia (estado global: sessão, carrinho de serviços selecionados)
- Vue Router (com guards de rota por role)
- Axios (ou `ofetch`) com interceptor para refresh de token
- `vite-plugin-pwa` (service worker, manifest, permite notificação web futura)
- Vitest + Vue Testing Library (testes de componente)
- Playwright (E2E)

**Backend**
- Python 3.12 + FastAPI
- Pydantic v2 (validação/serialização)
- SQLAlchemy 2.0 (async) + Alembic (migrations)
- PostgreSQL 15+
- `passlib[argon2]` (hash de senha — Argon2id, mais resistente que bcrypt a ataques com GPU)
- `pyjwt` (JWT) + tokens de refresh opacos gerados com `secrets.token_urlsafe`
- `resend` (SDK oficial) — chamado de forma síncrona/em background task leve do próprio FastAPI (`BackgroundTasks`), nunca por um processo agendado
- `sentry-sdk[fastapi]`
- `slowapi` (rate limiting) ou regra equivalente no Cloudflare
- pytest + pytest-asyncio + httpx (testes)

**Infra**
- Cloudflare: DNS, proxy/WAF, Cloudflare Pages (frontend)
- Render (rota gratuita recomendada) para a API (container Docker); Railway como alternativa paga se um dia quiser mais previsibilidade — ver seção 19
- PostgreSQL gerenciado via Neon (tier gratuito permanente) — evitar o Postgres gratuito do próprio Render, que expira em 30 dias
- GitHub Actions (CI: lint + testes + build + deploy)

---

## 7. Estrutura de pastas

### Backend
```
backend/
├── alembic/
│   └── versions/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py            # settings via pydantic-settings
│   │   ├── security.py          # hash, jwt, rate limit helpers
│   │   ├── logging.py
│   │   └── sentry.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/                  # SQLAlchemy models (1 arquivo por entidade)
│   ├── schemas/                 # Pydantic (request/response) por domínio
│   ├── modules/
│   │   ├── auth/                # router, service, dependências de auth
│   │   ├── users/
│   │   ├── services/            # CRUD de serviços da barbearia
│   │   ├── schedule/            # business hours, special dates, blocked slots
│   │   ├── availability/        # motor de cálculo de horários livres
│   │   ├── appointments/        # criação, cancelamento, transições de estado
│   │   ├── notifications/       # abstração de canais + Resend, disparo síncrono por evento
│   │   └── dashboard/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── concurrency/
├── Dockerfile
├── pyproject.toml
└── .env.example
```

### Frontend
```
frontend/
├── src/
│   ├── main.ts
│   ├── router/
│   ├── stores/                  # pinia: auth, booking, catalog
│   ├── composables/
│   ├── services/api/            # clients axios por domínio
│   ├── views/
│   │   ├── client/               # Catalogo, Agendar, MeusAgendamentos
│   │   └── admin/                 # Dashboard, Agenda, Clientes, Servicos, Configuracoes
│   ├── components/
│   ├── layouts/
│   ├── types/
│   └── assets/
├── public/
├── vite.config.ts
└── .env.example
```

---

## 8. Modelo de dados

**[DECISÃO] Consolidação de entidades.** `User`, `Role` e `Customer/Profile` foram deliberadamente **fundidos em uma única tabela `User`** com um campo `role` (enum) em vez de três tabelas separadas com joins — ADMIN e CLIENTE compartilham 100% dos mesmos campos de identidade (nome, e-mail, telefone, senha). Criar uma tabela `Role` separada só faria sentido se houvesse múltiplos papéis por usuário ou papéis dinâmicos, o que não é o caso.

| Entidade | Campos principais | Observações |
|---|---|---|
| **User** | id (UUID, PK), full_name, email (nullable, unique), phone (nullable, unique), password_hash, role (ADMIN/CUSTOMER), is_active, email_verified_at, phone_verified_at, failed_login_attempts, locked_until, created_at, updated_at | `CHECK (email IS NOT NULL OR phone IS NOT NULL)` |
| **BarbershopSettings** | id (fixo=1), name, timezone, capacity (int), booking_window_days (default 2), min_cancellation_notice_minutes, no_show_grace_minutes, slot_granularity_minutes (default 15), updated_at | Linha única (singleton). `no_show_grace_minutes` só orienta a sinalização visual da agenda (seção 4.7) — nenhum job lê esse campo |
| **Service** | id, name, description, price_cents (int), duration_minutes (int), is_active, created_at, updated_at | Preço em centavos evita erro de ponto flutuante |
| **BusinessHours** | id, weekday (0–6), start_time, end_time | Múltiplas linhas por weekday = múltiplos intervalos |
| **SpecialDate** | id, date (unique), is_closed, custom_open_time, custom_close_time, label | Feriados/exceções |
| **BlockedSlot** | id, date, start_time, end_time, reason, created_by (FK User) | Bloqueio pontual reversível |
| **Appointment** | id, customer_id (FK User), date, start_time, end_time, status (enum), total_price_cents, total_duration_minutes, notes, created_by (FK User), cancelled_at, cancelled_by (FK User), cancellation_reason, created_at, updated_at | Índice composto (date, start_time, status). Sem campo de lembrete — não existe mais essa notificação |
| **AppointmentService** | id, appointment_id (FK), service_id (FK), price_cents_snapshot, duration_minutes_snapshot | Snapshot no momento da reserva — editar preço de um serviço não altera agendamentos passados |
| **Notification** | id, user_id (FK), appointment_id (FK nullable), channel (EMAIL/WEB_PUSH/WHATSAPP), type (enum), status (PENDING/SENT/FAILED), payload (JSONB), sent_at, error_message, created_at | Extensível a novos canais |
| **PasswordResetToken** | id, user_id (FK), token_hash, expires_at, used_at, created_at | Token nunca guardado em texto puro |
| **RefreshToken** | id, user_id (FK), token_hash, expires_at, revoked_at, replaced_by_id (nullable, self-FK), user_agent, ip_address, created_at | Suporta rotação e detecção de reuso |
| **AuditLog** | id, actor_user_id (FK), action, entity_type, entity_id, metadata (JSONB), ip_address, created_at | Ações administrativas sensíveis |

---

## 9. Diagrama textual das entidades

```
User (1) ───────< Appointment >─────── customer_id
User (1) ───────< Appointment >─────── created_by (admin ou o próprio cliente)
User (1) ───────< Appointment >─────── cancelled_by
User (1) ───────< RefreshToken
User (1) ───────< PasswordResetToken
User (1) ───────< Notification
User (1) ───────< AuditLog (actor)
User (1) ───────< BlockedSlot (created_by)

Appointment (1) ───────< AppointmentService >─────── (N) Service
Appointment (1) ───────< Notification (opcional)

BarbershopSettings (singleton, sem FKs de entrada)
BusinessHours (N linhas independentes, por weekday)
SpecialDate (N linhas, por date)
BlockedSlot (N linhas, por date+intervalo)
```

---

## 10. Endpoints REST

```
Auth
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm
GET    /api/v1/auth/me
PATCH  /api/v1/auth/me

Catálogo (público autenticado)
GET    /api/v1/services

Disponibilidade
GET    /api/v1/availability?date=&service_ids=

Agendamentos (cliente)
POST   /api/v1/appointments
GET    /api/v1/appointments/me
DELETE /api/v1/appointments/{id}          # cancelamento próprio

Admin — clientes
GET    /api/v1/admin/customers
POST   /api/v1/admin/customers
GET    /api/v1/admin/customers/{id}
PATCH  /api/v1/admin/customers/{id}
DELETE /api/v1/admin/customers/{id}       # desativa (soft)

Admin — serviços
GET    /api/v1/admin/services
POST   /api/v1/admin/services
PATCH  /api/v1/admin/services/{id}
DELETE /api/v1/admin/services/{id}        # desativa (soft)

Admin — agenda
GET    /api/v1/admin/appointments?date=&status=
POST   /api/v1/admin/appointments         # criação manual (ignora janela D+2)
PATCH  /api/v1/admin/appointments/{id}
PATCH  /api/v1/admin/appointments/{id}/cancel
PATCH  /api/v1/admin/appointments/{id}/complete
PATCH  /api/v1/admin/appointments/{id}/no-show

Admin — horários e exceções
GET    /api/v1/admin/business-hours
PUT    /api/v1/admin/business-hours
GET    /api/v1/admin/special-dates
POST   /api/v1/admin/special-dates
PATCH  /api/v1/admin/special-dates/{id}
DELETE /api/v1/admin/special-dates/{id}
GET    /api/v1/admin/blocked-slots?date=
POST   /api/v1/admin/blocked-slots
DELETE /api/v1/admin/blocked-slots/{id}

Admin — configurações e dashboard
GET    /api/v1/admin/settings
PATCH  /api/v1/admin/settings
GET    /api/v1/admin/dashboard/summary

Infra
GET    /health
```

Todas as rotas `/admin/*` exigem `role=ADMIN` via dependency do FastAPI; todas as demais autenticadas exigem apenas token válido.

---

## 11. Fluxos principais

**Cliente — agendar:**
1. Login/registro → 2. `GET /services` → 3. seleciona 1+ serviços (frontend soma duração/preço) → 4. escolhe data dentro de D0–D2 → 5. `GET /availability` com `service_ids` (duração total) → 6. escolhe horário → 7. `POST /appointments` (backend revalida tudo) → 8. recebe confirmação (resposta + e-mail via Resend) → 9. vê o agendamento em "Meus agendamentos".

**Admin — dia a dia:**
Login → Dashboard (resumo do dia) → Agenda (visão dia/semana) → clique em horário livre para criar manual, ou em agendamento existente para editar/cancelar/concluir → Clientes/Serviços/Configurações conforme necessário.

---

## 12. Estratégia de autenticação

**[DECISÃO] JWT + refresh token em cookie httpOnly, não sessão de servidor pura.** Justificativa: a API é stateless por design (facilita rodar em plataformas como Render sem sticky session, e escalar para múltiplas réplicas depois se necessário), e o frontend é uma SPA separada do backend (subdomínios distintos atrás do Cloudflare) — um JWT de curta duração no `Authorization: Bearer` resolve isso sem exigir armazenamento de sessão compartilhado (Redis) só para autenticação. Sessão de servidor pura exigiria esse armazenamento compartilhado sem trazer benefício adicional aqui.

- **Access token:** JWT (HS256, chave forte em variável de ambiente), TTL 15 minutos, claims mínimas (`sub`, `role`, `exp`).
- **Refresh token:** string opaca aleatória (não JWT), hash armazenado em `RefreshToken`, TTL 30 dias, entregue como cookie `httpOnly; Secure; SameSite=Strict; Domain=api.dominio.com; Path=/api/v1/auth`.
- **Rotação:** cada `refresh` invalida o token anterior e emite um novo (`replaced_by_id`). Reuso de um refresh já trocado é tratado como possível roubo de token → revoga todas as sessões do usuário e registra em `AuditLog`.
- **Logout:** revoga o refresh token atual (`revoked_at`).
- **Reset de senha:** token de uso único, hash salvo, TTL 30 minutos, enviado por Resend; nunca revela se o e-mail/telefone existe (mensagem genérica de sucesso sempre).
- **Brute force:** contador `failed_login_attempts` + `locked_until` progressivo no `User`, mais rate limiting por IP no endpoint de login (ex.: 10 tentativas/15min via `slowapi` ou regra de Cloudflare).
- **CORS:** `allow_origins` restrito ao domínio do frontend; nunca `*` com `allow_credentials=True`.

---

## 13. Estratégia de agendamento

Algoritmo de `GET /availability?date=&service_ids=`:

1. Resolve duração total somando `Service.duration_minutes` dos `service_ids`.
2. Busca janelas de funcionamento do dia: `SpecialDate` (se existir e não for dia fechado, usa horário customizado) → senão `BusinessHours` do weekday correspondente.
3. Subtrai `BlockedSlot` das janelas do dia.
4. Gera candidatos de início a cada `slot_granularity_minutes` (padrão 15min) dentro das janelas restantes, descartando qualquer candidato cujo `[start, start+duração)` ultrapasse o fim de uma janela (não permite "vazar" para o intervalo de pausa).
5. Para cada candidato, conta agendamentos ativos (`CONFIRMED`) cujo intervalo sobrepõe `[start, start+duração)`; descarta o candidato se a contagem já atingir `BarbershopSettings.capacity`.
6. Se a data for hoje, descarta candidatos cujo horário já passou.
7. Retorna a lista de horários válidos ao frontend.

Essa mesma função é reutilizada (não duplicada) na validação de `POST /appointments`, para garantir que o horário escolhido ainda é válido no exato momento da escrita.

---

## 14. Estratégia anti-overbooking

Overlap de intervalos com capacidade > 1 **não** pode ser garantido só por uma constraint simples de banco (uma `EXCLUDE` de range do PostgreSQL resolveria capacidade=1, mas não capacidade=N). A solução adotada combina três camadas:

1. **Lock de aplicação a nível de transação:** antes de inserir, a transação adquire um **advisory lock** do PostgreSQL (`pg_advisory_xact_lock`) com chave derivada da data (ex.: hash de `YYYY-MM-DD`), serializando todas as tentativas de escrita para aquele dia. O lock é liberado automaticamente no commit/rollback.
2. **Revalidação dentro da transação:** com o lock adquirido, o backend roda de novo o cálculo de sobreposição/capacidade (passo 5 da seção 13) contra o estado atual do banco, dentro da mesma transação. Só então insere o `Appointment` + `AppointmentService`.
3. **Idempotência do lado do cliente:** o `POST /appointments` aceita um `Idempotency-Key` (UUID gerado no frontend); requisições repetidas com a mesma chave (ex.: duplo clique, retry de rede) retornam o mesmo resultado em vez de criar uma segunda reserva.

Isso garante que, mesmo com dois clientes clicando "confirmar" no mesmo milissegundo para o mesmo horário, apenas requisições até o limite de capacidade sejam aceitas — a serialização acontece no banco, não na aplicação (que pode ter múltiplas réplicas).

---

## 15. Estratégia de notificações

**[DECISÃO] Removido o lembrete de 20 minutos — decisão explícita do cliente para evitar custo de hospedagem.** A versão anterior desta especificação previa um scheduler (APScheduler) rodando continuamente para disparar o lembrete e marcar no-show automaticamente, o que exigia um plano de hospedagem *always-on*. A pedido do dono do produto, essa peça foi removida por completo — não apenas adiada.

Abstração `NotificationChannel` (interface) com uma implementação inicial `EmailChannel` (Resend). Todo evento de notificação agora é **disparado de forma síncrona (ou via `BackgroundTasks` do próprio FastAPI, que não exige processo separado) dentro da requisição HTTP que gerou o evento** — nunca por um job agendado:

| Evento | Disparado em | Canal |
|---|---|---|
| Confirmação de cadastro | `POST /auth/register` | E-mail |
| Confirmação de agendamento | `POST /appointments` | E-mail |
| Cancelamento | `DELETE /appointments/{id}` e `PATCH /admin/appointments/{id}/cancel` | E-mail |
| Redefinição de senha | `POST /auth/password-reset/request` | E-mail |

Cada disparo grava um registro em `Notification` (auditoria de envio), mas não depende de nenhum processo rodando em segundo plano. Adicionar WhatsApp/SMS no futuro = nova classe `WhatsAppChannel` implementando a mesma interface, sem tocar nas regras de agendamento.

**Consequência arquitetural direta:** sem lembrete e sem auto no-show por job (seção 4.7 já resolve no-show por cálculo sob demanda), o backend não precisa de nenhum processo contínuo. Isso libera a escolha de hospedagem na seção 19 para incluir opções gratuitas com "sleep" por inatividade, sem perda de funcionalidade.

**Se um dia quiser reativar o lembrete:** a peça que faltaria é só um gatilho externo chamando um endpoint (`POST /internal/send-reminders`) — pode ser um cron gratuito de terceiro (ex.: um GitHub Actions agendado, ou um cron job do próprio provedor) chamando esse endpoint a cada minuto, sem precisar manter o servidor principal sempre ligado. Fica registrado como opção de roadmap, não implementado agora.

---

## 16. Estratégia de segurança

- **Injeção SQL:** eliminada por design — todo acesso a dados via SQLAlchemy ORM/Core parametrizado, nunca SQL concatenado.
- **XSS:** Vue escapa interpolação por padrão; qualquer `v-html` é proibido para conteúdo vindo de usuário.
- **CSRF:** cookies de refresh com `SameSite=Strict`; nenhuma ação de escrita aceita via GET.
- **CORS:** allowlist explícita do domínio do frontend.
- **Rate limiting:** login, registro e reset de senha limitados por IP/conta; regras adicionais no nível do Cloudflare (WAF/rate limiting rules) como segunda camada.
- **Autorização:** dependency FastAPI reutilizável (`require_role(Role.ADMIN)`); toda query de recurso do cliente filtra explicitamente por `customer_id = current_user.id` — nunca confia em um `id` vindo do corpo da requisição para decidir "de quem" é o recurso.
- **Enumeração de usuários:** respostas de login/registro/reset nunca revelam se um e-mail/telefone existe.
- **Segredos:** todos em variáveis de ambiente, nunca commitados; `.env` no `.gitignore`; chave do Resend e do Sentry só no backend.
- **Headers de segurança:** HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP restritiva — aplicados via Cloudflare Transform Rules e/ou middleware do FastAPI.
- **Cookies:** `Secure`, `httpOnly`, `SameSite=Strict` no refresh token.
- **Auditoria:** ações administrativas sensíveis gravam `AuditLog` (ator, ação, entidade afetada, IP).
- **Race conditions de agenda:** cobertas na seção 14.

---

## 17. Estratégia de testes

- **Unitários (backend):** cálculo de duração total, geração de slots candidatos, cálculo de sobreposição/capacidade, transições de estado do `Appointment` (o que é permitido a partir de cada status), cálculo sob demanda de "possível no-show" (seção 4.7).
- **Integração (backend):** cada endpoint via `httpx.AsyncClient` contra um banco de testes real (Postgres em container), incluindo casos de borda (fora da janela D0–D2, capacidade excedida, horário fora do funcionamento).
- **Concorrência:** teste que dispara N requisições `POST /appointments` simultâneas para o mesmo horário com capacidade configurada em 2, e verifica que exatamente 2 são aceitas e as demais recebem `409 Conflict`.
- **Frontend:** testes de componente (Vitest) para o formulário de agendamento (soma de duração/preço, desabilitar horários indisponíveis) e para os guards de rota por role.
- **E2E (Playwright):** cadastro → login → agendamento → cancelamento; e login admin → criar serviço → configurar horário → ver na agenda.

---

## 18. Estratégia de observabilidade

- **Sentry** no frontend (erros JS não tratados, falhas de requisição) e no backend (exceptions não tratadas, com contexto de rota/usuário — sem PII: enviar `user.id`, nunca e-mail/telefone/nome; `send_default_pii=False`).
- **Logs estruturados** (JSON, via `structlog` ou `logging` configurado) no backend, com `request_id` correlacionando toda a requisição.
- **Health check:** `GET /health` verificando conexão com o banco, usado pelo provedor de deploy para restart automático.
- **Tratamento global de erros:** exception handler do FastAPI padroniza toda resposta de erro (`{"error": {"code", "message"}}`), evitando vazar stack trace ao cliente.

---

## 19. Estratégia de deploy

**Recomendação para uma barbearia pequena, priorizando custo baixo e manutenção simples:**

**[DECISÃO] Ordem de execução: local primeiro, domínio depois.** A pedido do dono do produto, as Fases 0–9 (seção 25/26) rodam inteiramente em ambiente local via Docker Compose — nenhuma delas depende de domínio, Cloudflare, Render ou Neon. Só a Fase 10 (deploy) precisa de infraestrutura externa, e mesmo essa Fase 10 **não exige comprar domínio de imediato**: tanto o Render quanto o Cloudflare Pages fornecem uma URL própria e gratuita (`*.onrender.com` e `*.pages.dev`) com HTTPS já incluso, então dá para colocar o sistema no ar de verdade, testar com dados reais e mostrar para o dono da barbearia antes de gastar um centavo com domínio. Registrar um domínio próprio (`suabarbearia.com.br` ou similar) fica reservado para quando fizer sentido apontar um endereço definitivo — nesse momento basta seguir a seção 20 para conectar o domínio ao que já está no ar.

Como o sistema não tem mais nenhum processo de background contínuo (seção 15), é possível rodar tudo em camadas gratuitas, com uma única ressalva de cold start. Abaixo, a combinação que fica em **R$ 0/mês de infraestrutura**, e o que cada peça exige de atenção:

| Peça | Serviço recomendado | Custo | Ressalva |
|---|---|---|---|
| Frontend | Cloudflare Pages | Grátis (bandwidth ilimitado, 500 builds/mês) | Nenhuma relevante para este porte |
| Backend (API) | **Render**, free web service | Grátis (750h/mês) | "Dorme" após ~15min sem tráfego; primeira requisição depois disso demora ~1min (cold start). Aceitável para uma barbearia — o pior caso é o cliente esperar um pouco ao abrir o app depois de um período parado |
| Banco de dados | **Neon** (Postgres serverless), não o Postgres do próprio Render | Grátis (tier permanente, ~0,5GB) | O Postgres gratuito do Render **expira em 30 dias** — não serve para produção. Neon tem tier gratuito permanente, por isso é a escolha aqui, mesmo hospedando a API no Render |
| E-mail transacional | Resend | Grátis (3.000 e-mails/mês, 100/dia) | Muito acima do volume de uma barbearia pequena |
| Observabilidade | Sentry, plano Developer | Grátis (5.000 eventos/mês, 1 usuário) | Suficiente para monitorar sozinho; se um segundo administrador precisar de acesso, aí sim vira plano pago |
| DNS/CDN/WAF | Cloudflare (plano Free da zona) | Grátis | — |
| Domínio | Registro em qualquer registrador | **Este é o único custo real**, ~R$ 40–60/ano | Não tem como fugir disso — é o nome do site |

**[DECISÃO] Railway deixou de ser recomendado como opção "gratuita".** A versão anterior desta seção citava Railway como alternativa ao Render; hoje o Railway não oferece mais um tier permanentemente gratuito (apenas um crédito de avaliação por tempo limitado, depois cobrança mínima mensal). Para manter o objetivo de custo zero, a recomendação passa a ser especificamente **Render (API) + Neon (banco)**. Railway continua sendo uma opção válida se um dia você decidir pagar por mais previsibilidade/performance, mas não entra mais na rota gratuita.

- **CI/CD:** GitHub Actions — em cada push para `main`: lint → testes (backend + frontend) → build → deploy automático (Cloudflare Pages via integração direta com o repo; Render via integração direta ou Action oficial).
- Preços mudam com frequência — antes de configurar de fato, vale conferir a página de preços atual de cada serviço.

`Domínio → Cloudflare (DNS+proxy, grátis) → { Cloudflare Pages (frontend, grátis) , api.dominio.com → Render free web service (backend, grátis) → Neon (Postgres, grátis) }`

---

## 20. Configuração Cloudflare

- Registro `A`/`CNAME` de `app` apontando para o Cloudflare Pages do projeto (nuvem laranja ativada).
- Registro `CNAME` de `api` apontando para o domínio público do Render (nuvem laranja ativada — assim o tráfego para a API também passa pelo WAF).
- SSL/TLS: modo **Full (strict)**.
- WAF: regras gerenciadas padrão ativadas; regra de rate limiting adicional em `/api/v1/auth/*` (ex.: bloquear IP após N requisições/minuto).
- Cache Rules: cache agressivo apenas para assets estáticos do frontend (JS/CSS/imagens); `api.dominio.com` com cache **desativado** (respostas dinâmicas).
- Security headers via Transform Rules (HSTS, X-Frame-Options) se não forem setados pela própria API.

---

## 21. Configuração Resend

- Domínio de envio verificado no Resend, com registros SPF/DKIM criados no Cloudflare DNS (a própria Resend fornece os valores exatos a inserir).
- `RESEND_API_KEY` **somente** em variável de ambiente do backend — nunca exposta ao frontend.
- Serviço de e-mail desacoplado (`EmailChannel`) com templates para: confirmação de cadastro, confirmação de agendamento, cancelamento, redefinição de senha.
- (Opcional, fase futura) Webhook do Resend para status de entrega/bounce, atualizando `Notification.status`.

---

## 22. Configuração Sentry

- Projetos separados (ou pelo menos `environment` separado) para frontend e backend, e entre `staging`/`production`.
- `SENTRY_DSN` em variável de ambiente de cada lado.
- `traces_sample_rate` baixo em produção (ex.: 0.1) para não gerar custo desnecessário.
- `send_default_pii = False`; `before_send` customizado removendo e-mail/telefone/nome de qualquer payload antes do envio.
- Tag de release automática vinda do commit SHA no pipeline de CI.

---

## 23. Variáveis de ambiente

**Backend (`.env`)**
```
DATABASE_URL=
JWT_SECRET_KEY=
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
RESEND_API_KEY=
RESEND_FROM_EMAIL=
SENTRY_DSN=
ENVIRONMENT=production
FRONTEND_ORIGIN=https://app.dominio.com
BARBERSHOP_TIMEZONE=America/Fortaleza
RATE_LIMIT_LOGIN_PER_MINUTE=10
```

**Frontend (`.env`)**
```
VITE_API_BASE_URL=https://api.dominio.com/api/v1
VITE_SENTRY_DSN=
```

---

## 24. Checklist de produção

- [ ] Migrations aplicadas e revisadas (nenhuma migration destrutiva sem backup prévio).
- [ ] Usuário ADMIN inicial criado via script/seed, não hardcoded no código.
- [ ] `.env` de produção conferido (nenhum segredo de desenvolvimento reaproveitado).
- [ ] HTTPS forçado ponta a ponta (Cloudflare Full Strict).
- [ ] Rate limiting ativo em login/registro/reset de senha.
- [ ] Sentry recebendo eventos de teste em frontend e backend.
- [ ] Domínio do Resend verificado (SPF/DKIM válidos) e e-mail de teste entregue.
- [ ] Teste de concorrência de agendamento rodado contra o ambiente de staging.
- [ ] Backup automático do PostgreSQL configurado e testado (restore, não só backup).
- [ ] Health check respondendo e configurado no provedor de deploy.
- [ ] CORS restrito ao domínio real de produção (não `*`).
- [ ] E-mails transacionais (confirmação/cancelamento/reset) testados ponta a ponta em produção.

---

## 25. Roadmap de implementação por fases

- **Fase 0 — Fundação:** scaffolding do backend (FastAPI + Alembic + config) e do frontend (Vite + Vue 3 + Vuetify + roteador básico); Docker Compose local com Postgres.
- **Fase 1 — Autenticação:** entidade `User`, registro, login, JWT + refresh, recuperação de senha, guards de rota no frontend.
- **Fase 2 — Cadastros administrativos:** CRUD de `Service`, `BusinessHours`, `SpecialDate`, `BlockedSlot`, `BarbershopSettings`.
- **Fase 3 — Motor de disponibilidade:** implementação e testes intensivos do algoritmo da seção 13 (sem UI ainda — testado via API/testes automatizados).
- **Fase 4 — Agendamento (núcleo crítico):** `POST /appointments` com o mecanismo anti-overbooking completo (seção 14) + testes de concorrência.
- **Fase 5 — Frontend do cliente:** catálogo, seleção de serviços, tela de disponibilidade, confirmação, "meus agendamentos", cancelamento.
- **Fase 6 — Frontend do admin:** dashboard, agenda (dia/semana), CRUD de clientes/serviços/horários pela UI.
- **Fase 7 — Notificações:** integração Resend, templates, disparo síncrono por evento (sem job em background).
- **Fase 8 — Segurança e auditoria:** rate limiting, `AuditLog`, revisão OWASP.
- **Fase 9 — Observabilidade:** Sentry (front/back), logs estruturados, health check.
- **Fase 10 — Deploy:** Cloudflare + Render (API) + Neon (Postgres) + CI/CD, na rota de custo zero descrita na seção 19.
- **Fase 11 — QA final:** E2E completo, checklist de produção, ajustes de performance mobile.
- **Roadmap futuro (fora do MVP):** push web (VAPID), WhatsApp/SMS, pagamento online, múltiplos profissionais/agendas, multi-unidade.

---

## 26. Plano executável para o Codex (tarefas verificáveis)

Cada item abaixo é uma unidade de trabalho pequena, com critério de "pronto" objetivo. Seguir na ordem — cada fase depende da anterior.

**Fase 0**
1. Criar repositório com `backend/` e `frontend/` conforme estrutura da seção 7. *Pronto quando:* `docker compose up` sobe API + Postgres, e `npm run dev` sobe o frontend, sem erro.
2. Configurar Alembic e criar migration inicial vazia. *Pronto quando:* `alembic upgrade head` roda sem erro num banco limpo.

**Fase 1**
3. Modelo `User` + migration. *Pronto quando:* constraint `email OR phone` é rejeitada corretamente em teste.
4. Endpoints de registro/login/refresh/logout + hashing Argon2. *Pronto quando:* suite de testes de integração de auth passa, incluindo tentativa de login com senha errada e bloqueio após N tentativas.
5. Reset de senha com envio via Resend (pode usar modo sandbox/teste do Resend nesta fase). *Pronto quando:* token expira corretamente e não pode ser reutilizado.
6. Guards de rota + store Pinia de sessão no frontend. *Pronto quando:* usuário não-admin é redirecionado ao tentar acessar rota `/admin/*`.

**Fase 2**
7. CRUD de `Service` (admin). *Pronto quando:* soft delete funciona (serviço inativo não aparece no catálogo do cliente, mas segue em agendamentos antigos).
8. CRUD de `BusinessHours` (múltiplos intervalos por dia). *Pronto quando:* é possível configurar terça com dois intervalos e a lacuna do meio é respeitada nos testes da Fase 3.
9. CRUD de `SpecialDate` e `BlockedSlot`.

**Fase 3**
10. Função pura de geração de slots candidatos (sem banco, testável isoladamente). *Pronto quando:* testes unitários cobrem: dia fechado, feriado, bloqueio parcial, serviço que não cabe antes do fechamento.
11. Função de checagem de capacidade por sobreposição. *Pronto quando:* testes cobrem o exemplo exato da seção 4.2 (capacidade 2, dois clientes 08:00–08:30).
12. Endpoint `GET /availability` ligando as duas funções ao banco real.

**Fase 4**
13. Implementar `POST /appointments` com advisory lock + revalidação transacional + suporte a `Idempotency-Key`. *Pronto quando:* o teste de concorrência da seção 17 passa de forma determinística em pelo menos 3 execuções seguidas.
14. Endpoints de cancelamento (cliente e admin) e transições `complete`/`no-show`. *Pronto quando:* transições inválidas (ex.: completar um agendamento já cancelado) retornam erro claro.

**Fase 5**
15. Tela de catálogo + seleção de serviços com soma de duração/preço reativa.
16. Tela de disponibilidade + confirmação, consumindo `GET /availability` e `POST /appointments`.
17. Tela "Meus agendamentos" com cancelamento.

**Fase 6**
18. Dashboard admin (indicadores: atendimentos de hoje, próximos, cancelamentos, resumo semanal).
19. Agenda admin (visão dia/semana) com criação manual e edição.
20. Telas de CRUD de clientes/serviços/horários/feriados/bloqueios.

**Fase 7**
21. `NotificationChannel` + `EmailChannel` (Resend) + templates para confirmação de cadastro, confirmação de agendamento, cancelamento e reset de senha. *Pronto quando:* cada evento dispara o e-mail correspondente dentro da própria requisição, sem nenhum processo separado rodando.
22. Cálculo sob demanda de "possível no-show" na agenda admin (seção 4.7), com botão de confirmação manual. *Pronto quando:* um agendamento `CONFIRMED` vencido aparece sinalizado na listagem sem que nenhum job tenha rodado.

**Fase 8**
23. Rate limiting em auth + `AuditLog` nas ações administrativas sensíveis.

**Fase 9**
24. Sentry front/back com scrub de PII + `/health` + logging estruturado.

**Fase 10**
25. Dockerfile de produção + pipeline GitHub Actions (lint → testes → build → deploy) + configuração Cloudflare/Render/Neon conforme seções 19–20 (sem exigência de plano always-on, tudo na rota de custo zero).

**Fase 11**
26. Suite E2E Playwright cobrindo os fluxos da seção 11 + checklist da seção 24 executado manualmente antes do lançamento.

---

*Fim da especificação. Este documento é a fonte de verdade — qualquer mudança de regra de negócio deve ser refletida aqui antes de alterar código.*
