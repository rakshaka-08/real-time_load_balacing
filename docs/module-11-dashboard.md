# Module 11: live dashboard

Open `/dashboard` after signing in. The login page, Tasks, and Virtual Machines
pages now link to it. Authentication stays in memory: reloading the browser
requires signing in again.

## Use

1. Create tasks and VMs through the existing management pages.
2. Choose **New simulation**, select tasks and VMs, and create the run.
3. Select **Start**. Watch simulated time, task progress, and machine activity.
4. Pause/resume or stop the run. Reset on a terminal run creates a separate run.
5. Select saved runs to inspect them. Refresh the list for current summaries.

The initial creation form uses LPT, seed 42, and queue redistribution.
Advanced algorithm selection/settings belong to Module 12. Busy time and queued
seconds are displayed as reported by the engine, not as CPU utilization.

## Connection behavior

Controls are disabled while a request is pending or live subscription is unavailable.
A disconnected monitor keeps its last snapshot with a stale-data notice. Reconnect
resubscribes; Refresh snapshot fetches current state through HTTP. REST and socket
responses are compared by revision so an older response cannot replace newer state.

## Run locally

Start the backend and MongoDB as usual, then run `npm run dev` in `frontend`.
The API defaults to `http://127.0.0.1:5000/api`. To use another backend, set
`VITE_API_BASE_URL` before starting Vite; e.g. in PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:5001/api"
npm run dev
```

The backend's `FRONTEND_ORIGIN` must match the frontend origin. The same API
configuration is used to derive the socket server address.

## Review checklist

- Empty state and links to task/VM setup.
- Paginated run list and paginated input selection.
- Loading, failure, and retry states.
- Live task/VM data, progress, and valid controls for each run status.
- Reset preserves the original record.
- Narrow layouts and keyboard focus indicators.
- Sign-out removes access to the protected dashboard.

Create a GitHub issue titled **Live simulation dashboard**, then link it in the
Module 11 pull request using its actual issue number. CI must pass before merge.
