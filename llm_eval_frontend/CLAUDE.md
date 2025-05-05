# LLM Leaderboard App Development Guide

## Commands
- Build: `npm run build`
- Dev server: `npm run dev`
- Lint: `npm run lint`
- Typecheck: `npm run typecheck`
- Test: `npm run test`
- Single test: `npm run test -- -t "test name"`

## Code Style Guidelines
- **TypeScript**: Use strict typing with proper interfaces in `types/` folder
- **Components**: Use functional React components with hooks
- **Naming**: 
  - PascalCase for components and interfaces
  - camelCase for variables, functions, and files
  - Descriptive, semantic naming
- **Imports**: Group imports by external libraries first, then internal modules
- **State Management**: Use React Context for global state, React Query for API data
- **Error Handling**: Try/catch in API calls, proper error propagation to UI
- **Comments**: Include JSDoc for functions, keep comments concise and meaningful

Follow existing patterns when adding new components or features. Respect the established folder structure and architecture.