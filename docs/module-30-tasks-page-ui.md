# Module 30 — Tasks page UI

The Tasks page now uses the same dark navy and mint visual language as
the simulation dashboard.

Existing behavior remains unchanged:

- JWT-protected task loading
- Task creation
- Task editing
- Task deletion
- Pagination
- Page-size selection
- Refresh
- Seeded workload generation
- Authentication failure handling
- Logout

The page adds responsive forms, summary cards, table styling, progress
feedback, empty states, success messages, and error messages.

The saved Tasks page represents reusable task definitions. Runtime
states such as pending, assigned, running, completed, and failed remain
available in simulation dashboards because those states belong to a
specific simulation run.