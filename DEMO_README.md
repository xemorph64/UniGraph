# UniGRAPH Demo - Quick Start

## Prerequisites
- Docker & Docker Compose
- 8GB RAM minimum

## Start Demo (5 minutes)

### 1. Start Infrastructure
```bash
cd docker
docker compose -f docker-compose.demo.yml up -d
```

Wait 30s for Neo4j to be ready.

### 2. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend runs at http://localhost:8000

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:5173

### 4. Seed Demo Data
```bash
python scripts/demo_seeder.py
```

### 5. Run Transaction Simulator
```bash
# Live stream mode
python scripts/simulate_transactions.py --mode live --rate 2

# Or run specific fraud scenarios
python scripts/simulate_transactions.py --mode scenario --scenario rapid_layering
python scripts/simulate_transactions.py --mode scenario --scenario mule_network
```

## Demo Flow

1. **Dashboard** - Click "Start System" to seed demo data
2. **Live Ticker** - Watch transactions stream in real-time
3. **Run Scenario** - Trigger a fraud scenario (e.g., `rapid_layering`)
4. **Alerts** - See the alert appear in the Alerts page
5. **Graph Explorer** - Click an alert to see the money trail
6. **STR Report** - Generate AI-powered investigation report

## Test Cases

| Scenario | Command | Expected |
|----------|---------|----------|
| Normal | `--mode live` | Most transactions show LOW risk |
| Rapid Layering | `--mode scenario --scenario rapid_layering` | 6 transactions, HIGH/CRITICAL alerts |
| Structuring | `--mode scenario --scenario structuring` | 12 transactions, STRUCTURING flag |
| Mule Network | `--mode scenario --scenario mule_network` | MULE_NETWORK pattern detected |

## API Endpoints

- `GET /health` - System health check
- `POST /api/v1/transactions` - Submit a transaction
- `GET /api/v1/transactions/recent` - Recent transactions for ticker
- `GET /api/v1/alerts/` - List alerts
- `GET /api/v1/accounts/{id}/graph` - Get account subgraph
- `POST /api/v1/reports/str/generate` - Generate STR report

## Troubleshooting

**Neo4j not ready**: Wait 30s after docker compose start
**No data showing**: Run `python scripts/demo_seeder.py` again
**Frontend can't reach backend**: Check Vite proxy in `vite.config.ts`