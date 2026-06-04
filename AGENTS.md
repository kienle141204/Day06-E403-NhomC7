# Repository Guidelines

## Project Structure & Module Organization

This repository is organized for a Day 06 AI Product Hackathon submission. Root-level Markdown files document the assignment, workflow, rules, and product specification process. Keep product planning material in `spec/` and implementation work in `codebase/`.

The active prototype is a Vite React app in `codebase/frontend/`:

- `src/App.jsx` contains the main MedChat UI and user flows.
- `src/api/client.js` defines the API adapter used by the app.
- `src/data/mockApi.js` provides local mock responses for prototype/demo use.
- `src/index.css` and Tailwind utility classes define styling.
- Static entry files live in `index.html`, `src/main.jsx`, and `vite.config.js`.

## Build, Test, and Development Commands

Run commands from `codebase/frontend/`.

```bash
npm install
npm run dev
npm run build
npm run preview
```

- `npm install` installs React, Vite, Tailwind, icons, and font dependencies.
- `npm run dev` starts the local Vite development server on all interfaces.
- `npm run build` creates a production build and is the current primary verification command.
- `npm run preview` serves the built output locally for smoke testing.

## Coding Style & Naming Conventions

Use modern React with functional components and hooks. Component files use `.jsx`; modules use ES imports/exports because the package is configured with `"type": "module"`. Follow the existing style: two-space indentation, single quotes, no semicolons, and descriptive camelCase names for functions, state, and props. React components should use PascalCase, for example `PrescriptionPanel` and `ChatWindow`.

Prefer Tailwind utility classes for layout and styling. Keep UI text concise and domain-specific. Do not commit generated build output or dependency folders.

## Testing Guidelines

No automated test framework is configured yet. Before submitting changes, run `npm run build` and manually exercise the core flow: upload/select a prescription file, confirm medications, ask a follow-up question, create reminders, and load specialist appointments.

If tests are added later, place them near the related source files or in a clear `tests/` directory, and use names such as `App.test.jsx` or `client.test.js`.

## Commit & Pull Request Guidelines

Git history currently uses short, imperative messages such as `upload code base` and `first commit`. Keep commits focused and descriptive, for example `add reminder scheduling UI` or `wire prescription API adapter`.

Pull requests should include a short summary, verification steps, screenshots for UI changes, and any required environment variables such as `VITE_API_BASE_URL`. Never include API keys, `.env` files, or private health data in commits.
