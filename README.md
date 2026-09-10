# Sistema Barbearia

Sistema web de agendamento para uma barbearia, conforme `BARBEARIA_SYSTEM_SPEC.md`.

## Desenvolvimento local

### Backend e banco

```bash
docker compose up --build
```

API: <http://localhost:8000>
Documentação: <http://localhost:8000/docs>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: <http://localhost:5173>

## Estrutura

- `backend/`: API FastAPI, migrations Alembic e testes.
- `frontend/`: aplicação Vue 3 + TypeScript + Vuetify.
- `docker-compose.yml`: PostgreSQL local e API.
- `BARBEARIA_SYSTEM_SPEC.md`: fonte de verdade do produto.
