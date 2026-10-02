# LoadLab — Real-Time Load Balancing Simulator

LoadLab is a full-stack platform for creating distributed workloads, scheduling tasks across heterogeneous virtual machines, and monitoring execution in real time.

## Capabilities

- JWT registration and authentication
- Task and virtual-machine management
- GA, HBA, Hybrid GA + HBA, LPT, and SPT scheduling
- Runtime task generation and configurable micro-batching
- Automatic execution with pause, resume, stop, and reset controls
- Private Socket.IO updates with reconnect recovery
- Live metrics, task flow, and virtual data-center visualization
- Fair multi-algorithm benchmarking and saved-run comparison
- JSON and CSV reports, replay timelines, and reusable shared templates
- Liveness, readiness, and system-health diagnostics
- GitHub Actions checks for backend tests and frontend builds

## Architecture

```text
React + Vite
   |  REST API + authenticated Socket.IO
Flask routes and socket namespace
   |  services, validation, ownership checks
Simulation engine and scheduling algorithms
   |  persisted users, tasks, VMs, templates, runs
MongoDB
```

See [Architecture](docs/architecture.md) for component responsibilities and data flow.

## Requirements

- Python 3.11
- Node.js 22 and npm 10
- MongoDB 8 or another compatible MongoDB server
- Git

## Local setup on Windows

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env

Set-Location frontend
npm ci
Copy-Item .env.example .env
Set-Location ..
```

Set a unique `JWT_SECRET_KEY` in the root `.env` file before starting the backend.

## Run the complete system

Start MongoDB, then open two PowerShell terminals.

Backend terminal:

```powershell
Set-Location "D:\RAKSHA MAJOR PROJECT\real-time_load_balacing"
.\.venv\Scripts\Activate.ps1
python backend\run.py
```

Frontend terminal:

```powershell
Set-Location "D:\RAKSHA MAJOR PROJECT\real-time_load_balacing\frontend"
npm run dev
```

Open [http://localhost:5173](http://localhost:5173), create an account, and sign in. The backend API runs at `http://127.0.0.1:5000/api`.

## Validation

```powershell
Set-Location "D:\RAKSHA MAJOR PROJECT\real-time_load_balacing\backend"
& "..\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"

Set-Location "D:\RAKSHA MAJOR PROJECT\real-time_load_balacing\frontend"
npm run build
```

The full real-time integration check requires a running backend:

```powershell
Set-Location "D:\RAKSHA MAJOR PROJECT\real-time_load_balacing\frontend"
node scripts\verify-simulation.mjs
```

## Health endpoints

- `GET /api/health/live` — process liveness
- `GET /api/health/ready` — MongoDB and application readiness
- `GET /api/health/status` — detailed diagnostic status

## Collaboration

Contributors work in feature branches on their forks and open pull requests against `shravan18-63/real-time_load_balacing:main`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## Deployment

The included server command is intended for development. Review [Deployment preparation](docs/deployment.md) before hosting the application.
