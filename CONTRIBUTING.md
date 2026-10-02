# Contributing

## Repository workflow

1. Fork the repository and clone your fork.
2. Add the main repository as `upstream`.
3. Update your local `main` from `upstream/main`.
4. Create a focused feature branch.
5. Make small, meaningful commits.
6. Run the complete backend suite and frontend production build.
7. Push the feature branch to your fork.
8. Open a pull request into `shravan18-63/real-time_load_balacing:main`.

```powershell
git fetch upstream
git switch main
git pull --ff-only upstream main
git push origin main
git switch -c feature/short-description
```

## Commit guidance

- Keep one logical change in each commit.
- Use an imperative message such as `Add simulation benchmark charts`.
- Do not commit `.env`, virtual environments, `node_modules`, build output, logs, or test artifacts.
- Do not rewrite another contributor's published branch.

## Required validation

```powershell
Set-Location backend
& "..\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"

Set-Location ..\frontend
npm run build
```

Pull requests should explain the resulting behavior, list material implementation details, and include the validation results.
