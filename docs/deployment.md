# Deployment preparation

## Required configuration

Set these values through the hosting platform's secret or environment manager:

- `MONGO_URI`
- `MONGO_DB_NAME`
- `JWT_SECRET_KEY` with at least 32 unpredictable characters
- `FRONTEND_ORIGIN` with the deployed frontend origin
- `VITE_API_BASE_URL` while building the frontend

Never commit production secrets or a populated `.env` file.

## Backend

Install `requirements.txt`, expose the Flask application created by `backend/app/__init__.py`, and use a production server that supports the selected Flask-SocketIO deployment mode. Keep all WebSocket clients and background runners compatible with the chosen process topology. Validate multi-instance coordination before using more than one backend process.

## Frontend

Run `npm ci` and `npm run build` from `frontend`. Serve the generated `dist` directory from static hosting with single-page-application fallback enabled.

## MongoDB

- Use authentication and encrypted connections.
- Restrict network access to the backend environment.
- Configure backups and retention.
- Verify indexes during application startup.

## Release checks

1. Run all backend tests.
2. Build the frontend from a clean dependency install.
3. Verify `/api/health/live` and `/api/health/ready`.
4. Register and sign in with a test account.
5. Create tasks and VMs, run a simulation, and confirm live updates.
6. Verify analytics, export, replay, templates, and system status.
7. Confirm secrets and generated artifacts are absent from the commit.
