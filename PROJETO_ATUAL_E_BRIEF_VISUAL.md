# Sistema Barbearia — Estado atual e briefing para redesign

## Objetivo deste documento

Este arquivo descreve o estado atual do projeto para servir como contexto a outro agente de desenvolvimento ou design, especialmente para formular um prompt de redesign visual completo.

O objetivo do próximo trabalho é melhorar a interface, hierarquia visual, botões, responsividade e experiência de uso sem quebrar as rotas, regras de negócio ou integrações existentes.

> Não incluir neste documento chaves de API, tokens, senhas reais ou conteúdo do arquivo `.env`.

---

## 1. Visão geral

Sistema web de agendamento para uma barbearia, com dois perfis:

- **Administrador:** gerencia agenda, clientes, serviços, horários e configurações.
- **Cliente:** consulta serviços, escolhe horários, cria, edita e cancela seus agendamentos.

O projeto é single-tenant: atualmente representa uma única barbearia.

O nome usado na aplicação é **Sistema Barbearia**. Ainda não existe uma identidade final chamada “BarberStyle”; essa pode ser criada em um redesign futuro.

---

## 2. Stack atual

### Frontend

- Vue 3
- Composition API
- TypeScript
- Vite
- Vuetify 3
- Vue Router
- Pinia
- Material Design Icons (`@mdi/font`)
- Fontsource:
  - Instrument Serif
  - Manrope

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy Async
- PostgreSQL 16
- Alembic
- Pydantic Settings
- Argon2 para hash de senha
- JWT para access token
- Cookie HttpOnly para refresh token
- Resend preparado para e-mails transacionais

### Infraestrutura local

- Docker Compose
- Container PostgreSQL: `barbearia-db`
- Container API: `barbearia-api`
- Frontend executado localmente com Vite

---

## 3. Como executar localmente

### Backend e banco

Na raiz do projeto:

```bash
docker compose up -d --build api
```

API:

```text
http://localhost:8000
```

Documentação da API:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O Vite normalmente utiliza:

```text
http://localhost:5173
```

Se a porta estiver ocupada, ele pode iniciar em `5174` ou outra porta exibida no terminal.

Build de produção:

```bash
npm run build
```

---

## 4. Estrutura relevante de pastas

```text
.
├── BARBEARIA_SYSTEM_SPEC.md
├── docker-compose.yml
├── .env                         # não versionar
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   │   ├── appointments.py
│   │   │   ├── auth.py
│   │   │   ├── availability.py
│   │   │   ├── customers.py
│   │   │   ├── schedule.py
│   │   │   └── services.py
│   │   ├── audit.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── notifications.py
│   │   ├── schemas.py
│   │   └── security.py
│   └── tests/
└── frontend/
    ├── index.html
    └── src/
        ├── App.vue
        ├── main.ts
        ├── router/index.ts
        ├── services/api.ts
        ├── stores/auth.ts
        ├── styles/main.css
        └── views/
            ├── AdminView.vue
            ├── DashboardView.vue
            ├── ForgotPasswordView.vue
            ├── LoginView.vue
            ├── RegisterView.vue
            └── ResetPasswordView.vue
```

---

## 5. Rotas do frontend

| Rota | Acesso | Função |
|---|---|---|
| `/` | público | Redireciona para `/dashboard` |
| `/login` | visitante | Login por e-mail ou telefone |
| `/cadastro` | visitante | Cadastro de cliente |
| `/recuperar-senha` | visitante | Solicita recuperação de senha |
| `/reset-password?token=...` | visitante | Define nova senha |
| `/dashboard` | autenticado | Catálogo e agendamento do cliente |
| `/admin` | somente ADMIN | Painel completo da barbearia |

O guard do Vue Router:

- Redireciona visitantes para `/login` ao acessar páginas protegidas.
- Redireciona clientes que tentam acessar `/admin` para `/dashboard`.
- Redireciona usuários autenticados que acessam páginas de visitante para o dashboard.

---

## 6. Tela de login e autenticação

### Funcionalidades existentes

- Login por e-mail ou telefone.
- Senha com opção de mostrar/ocultar.
- Cadastro de conta.
- Recuperação de senha por e-mail.
- Redirecionamento automático de administrador para `/admin`.
- Redirecionamento de cliente para `/dashboard`.
- Sessão persistida por refresh token em cookie HttpOnly.

### Observação importante

Ao abrir o projeto, o navegador pode entrar diretamente no painel administrativo porque a sessão anterior continua válida no cookie. Para trocar de usuário, é necessário clicar em **Sair** ou limpar os dados do site.

### Ponto de redesign

A tela precisa ser revisada visualmente mantendo a funcionalidade atual. O foco deve ser:

- hierarquia clara;
- formulário compacto;
- excelente experiência mobile;
- estados de erro e carregamento;
- acessibilidade de foco e teclado;
- identidade premium de barbearia.

---

## 7. Área do cliente — `/dashboard`

### Funcionalidades atuais

- Lista de serviços ativos.
- Seleção de um ou mais serviços.
- Soma automática de preço e duração.
- Escolha de data dentro da janela permitida.
- Consulta de horários disponíveis.
- Criação de agendamento.
- Campo de observações.
- Lista dos próprios agendamentos.
- Cancelamento de agendamento.
- Edição dos serviços de um agendamento existente.

### Regra de edição

O cliente mantém a mesma data e horário ao editar os serviços.

Exemplo:

- serviço original de 30 minutos;
- cliente adiciona outro serviço e passa para 60 minutos;
- o backend verifica se o segundo bloco de 30 minutos está livre;
- se estiver livre, atualiza o agendamento;
- se não estiver, rejeita a alteração e preserva o agendamento original.

### Ponto de redesign

A tela deve ser reorganizada para reduzir a sensação de formulário longo. Sugestão de direção:

- catálogo de serviços com seleção evidente;
- resumo fixo ou sticky do agendamento;
- calendário e horários em uma sequência visual simples;
- área “Meus agendamentos” separada do fluxo de contratação;
- feedback visual claro após criar, editar ou cancelar.

---

## 8. Área administrativa — `/admin`

O painel inicia na seção **Agendamentos**.

### Navegação administrativa atual

- Agendamentos
- Dashboard
- Serviços
- Clientes
- Horários
- Exceções
- Configurações

### 8.1 Agendamentos

Recursos existentes:

- Lista de agendamentos.
- Filtro por data.
- Filtro por status.
- Botão para visualizar todos.
- Nome do cliente.
- Serviços utilizados.
- Horário.
- Valor.
- Status compacto.
- Concluir atendimento.
- Menu de ações secundárias.
- Cancelar agendamento.
- Marcar como “Não compareceu”.
- Confirmação visual antes de concluir ou cancelar.
- Gestos de arrastar:
  - direita: iniciar conclusão;
  - esquerda: iniciar cancelamento.
- A linha acompanha visualmente o arraste até um limite de segurança.

### Pontos críticos atuais da UX

- A lista pode ficar densa em telas estreitas.
- O agendamento manual aparece ao lado da lista e pode competir visualmente com ela.
- A ação por gesto precisa continuar tendo alternativa clara para desktop.
- O menu de ações deve ser consistente e não misturar ações destrutivas com ações frequentes.
- O status precisa ser facilmente compreendido sem depender de termos técnicos.

### 8.2 Dashboard administrativo

Indicadores existentes:

- Agendamentos ativos.
- Faturamento previsto.
- Atendimentos concluídos.
- Agendamentos cancelados.
- Serviço mais procurado.

Agendamentos cancelados não entram no total de ativos nem no faturamento previsto.

### 8.3 Agendar cliente

O administrador pode criar manualmente um agendamento para um cliente cadastrado, escolhendo:

- cliente;
- um ou mais serviços;
- data;
- horário disponível;
- observações.

O agendamento manual respeita disponibilidade e capacidade, mas não fica limitado à janela de dois dias usada pelo cliente.

### 8.4 Serviços

O administrador pode:

- criar serviço;
- editar serviço;
- informar nome, descrição, preço e duração;
- desativar serviço.

Serviços desativados não aparecem para novos clientes, mas continuam preservados nos agendamentos antigos.

### 8.5 Clientes

O administrador pode:

- buscar por nome, e-mail ou telefone;
- cadastrar cliente;
- editar dados;
- alterar senha opcionalmente;
- desativar cliente.

Clientes inativos permanecem preservados no histórico.

### 8.6 Horários de funcionamento

O administrador pode configurar intervalos independentes por dia, incluindo:

- período da manhã;
- período da tarde;
- dias fechados;
- múltiplos intervalos.

Regra atual da barbearia:

- horários de 30 em 30 minutos;
- pausa de almoço das 12:00 às 14:00;
- expediente da tarde começa às 14:00;
- capacidade padrão de dois atendimentos simultâneos.

### 8.7 Exceções

O administrador pode cadastrar:

- feriado ou dia fechado;
- data com horário especial;
- bloqueio pontual de horário;
- motivo do bloqueio;
- remoção da exceção.

### 8.8 Configurações

Configurações da barbearia:

- nome;
- fuso horário;
- capacidade simultânea;
- janela de agendamento;
- prazo mínimo para cancelamento;
- tolerância para ausência;
- intervalo entre slots.

Configurações do administrador:

- nome;
- e-mail;
- telefone;
- nova senha.

---

## 9. Regras de negócio importantes

### Capacidade

Até dois atendimentos podem ocorrer simultaneamente, desde que sejam clientes diferentes e a capacidade configurada permita.

### Mesmo cliente

O mesmo cliente não pode manter dois agendamentos ativos sobrepostos.

### Horários

- Slots padrão a cada 30 minutos.
- Pausa fixa entre 12:00 e 14:00.
- Serviços com duração maior ocupam blocos consecutivos.
- O serviço precisa caber completamente no intervalo de funcionamento.

### Cancelamento

- Cancelamento não apaga o registro.
- O status muda para `CANCELLED`.
- O histórico permanece.
- O administrador pode cancelar sem a restrição de prazo do cliente.

### Conclusão

- `CONFIRMED` pode virar `COMPLETED`.
- A conclusão atualiza os indicadores administrativos.

### Ausência

- O sistema calcula possível ausência sob demanda.
- O administrador confirma manualmente “Não compareceu”.
- Não existe job automático rodando em segundo plano.

---

## 10. Identidade visual atual

### Tokens principais

```css
--ink: #0A0D12;
--navy-deep: #0F1B2E;
--navy: #1F3B63;
--steel-blue: #5D8AC4;
--paper: #F4F6F9;
--slate: #8B96A8;
```

### Tipografia atual

- Títulos: Instrument Serif.
- Interface e corpo: Manrope.

### Princípios já adotados

- Fundo claro para áreas internas.
- Painéis escuros para ações e formulários importantes.
- Bordas hairline em vez de sombras exageradas.
- Azul aço como cor de interação.
- Cantos discretos.
- Layout responsivo.
- Foco visível em campos e botões.

### Problemas visuais a revisar

- Algumas telas ainda parecem mais funcionais do que premium.
- A densidade de informações da agenda pode comprometer a leitura.
- A navegação administrativa possui muitas opções lado a lado em telas menores.
- Botões e ações precisam de uma hierarquia mais clara.
- Campos de formulário podem ser agrupados em etapas ou blocos semânticos.
- Estados vazios, carregamento e erros podem receber tratamento visual mais refinado.
- É importante revisar textos com acentuação e encoding em todos os componentes.
- A experiência deve ser testada em 360px, 430px, tablet e desktop.

---

## 11. API atual

Todas as rotas usam o prefixo `/api/v1`.

### Autenticação

```text
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout
GET    /auth/me
PATCH  /auth/me
POST   /auth/password-reset/request
POST   /auth/password-reset/confirm
```

### Serviços

```text
GET    /services
GET    /admin/services
POST   /admin/services
PATCH  /admin/services/{service_id}
DELETE /admin/services/{service_id}
```

### Horários e exceções

```text
GET    /admin/settings
PATCH  /admin/settings
GET    /admin/business-hours
PUT    /admin/business-hours
GET    /admin/special-dates
POST   /admin/special-dates
PATCH  /admin/special-dates/{special_date_id}
DELETE /admin/special-dates/{special_date_id}
GET    /admin/blocked-slots
POST   /admin/blocked-slots
DELETE /admin/blocked-slots/{blocked_slot_id}
```

### Disponibilidade e agendamentos

```text
GET    /availability
POST   /appointments
GET    /appointments/me
PATCH  /appointments/{appointment_id}
DELETE /appointments/{appointment_id}
GET    /admin/appointments
POST   /admin/appointments
GET    /admin/appointments/dashboard
PATCH  /admin/appointments/{appointment_id}/cancel
PATCH  /admin/appointments/{appointment_id}/complete
PATCH  /admin/appointments/{appointment_id}/no-show
```

### Clientes administrativos

```text
GET    /admin/customers
POST   /admin/customers
GET    /admin/customers/{customer_id}
PATCH  /admin/customers/{customer_id}
DELETE /admin/customers/{customer_id}
```

---

## 12. Notificações

O backend possui infraestrutura de e-mail transacional via Resend.

Eventos preparados:

- cadastro confirmado;
- solicitação de recuperação de senha;
- agendamento confirmado;
- agendamento cancelado.

Sem domínio verificado, o sistema pode registrar a notificação como ignorada ou falhar conforme a configuração do Resend. O layout não deve depender da entrega do e-mail para concluir uma operação.

---

## 13. Banco de dados e entidades principais

- `users`
- `refresh_tokens`
- `password_reset_tokens`
- `services`
- `barbershop_settings`
- `business_hours`
- `special_dates`
- `blocked_slots`
- `appointments`
- `appointment_services`
- `idempotency_records`
- `audit_logs`
- `notifications`

Migrações atuais: `0001` até `0007`.

---

## 14. Restrições para o redesign

O redesign visual deve:

- preservar as rotas atuais;
- preservar os endpoints atuais;
- preservar a lógica de autenticação;
- preservar as regras de disponibilidade;
- preservar as ações de arrastar e confirmação;
- preservar a distinção entre cliente e administrador;
- não introduzir pagamento, WhatsApp ou múltiplos barbeiros nesta fase;
- não remover funcionalidades existentes sem propor substituição equivalente;
- manter mobile-first;
- evitar textos técnicos para o usuário final;
- não exibir tokens, IDs ou detalhes internos na interface;
- manter botões acessíveis, com área mínima de toque de 44px;
- respeitar `prefers-reduced-motion`.

---

## 15. O que o próximo prompt para o Claude deve solicitar

O prompt deve pedir que o Claude atue como especialista em:

- Vue 3 Composition API;
- TypeScript;
- Vuetify 3;
- design systems;
- UX mobile-first;
- acessibilidade;
- sistemas de agendamento;
- interfaces administrativas densas.

O redesign deve analisar todas as telas existentes:

1. Login.
2. Cadastro.
3. Recuperação de senha.
4. Nova senha.
5. Dashboard do cliente.
6. Meus agendamentos.
7. Painel administrativo.
8. Agenda administrativa.
9. Dashboard administrativo.
10. Serviços.
11. Clientes.
12. Horários.
13. Exceções.
14. Configurações.

Para cada tela, o prompt deve exigir:

- diagnóstico dos problemas atuais;
- nova hierarquia visual;
- wireframe textual;
- proposta de componentes;
- estados de carregamento, erro, vazio e sucesso;
- comportamento mobile e desktop;
- regras de acessibilidade;
- tokens de cor, espaçamento, tipografia e raio;
- código compatível com a estrutura atual;
- nenhuma alteração na lógica de negócio sem autorização.

---

## 16. Próximas melhorias recomendadas

### Alta prioridade

- Redesign completo da navegação administrativa para telas pequenas.
- Separar visualmente agenda, criação manual e histórico.
- Melhorar a visualização de um agendamento individual.
- Criar filtros persistentes e mais claros.
- Adicionar paginação ou carregamento incremental na lista de clientes.
- Melhorar feedback de ações assíncronas.

### Média prioridade

- Dashboard com período selecionável: hoje, semana, mês.
- Gráfico de faturamento e serviços mais utilizados.
- Histórico de alterações administrativas.
- Melhor visualização de horários ocupados e capacidade restante.
- Testes E2E para login, agendamento, edição e cancelamento.

### Futuro

- Deploy em ambiente público.
- Domínio próprio.
- Resend com domínio verificado.
- Sentry.
- Backup automatizado do PostgreSQL.
- CI/CD.
- WhatsApp ou SMS.
- Múltiplos barbeiros e agendas independentes.

---

## 17. Critério de sucesso do redesign

O redesign será considerado bom quando:

- um cliente conseguir marcar um horário sem confusão;
- o administrador identificar rapidamente os atendimentos do dia;
- as ações de concluir, cancelar e marcar ausência não competirem visualmente;
- a agenda funcionar bem em celular sem rolagem horizontal;
- os principais botões forem facilmente identificáveis;
- o sistema tiver aparência premium e consistente;
- a interface não parecer um conjunto de telas isoladas;
- nenhuma regra atual de disponibilidade ou segurança for perdida.

