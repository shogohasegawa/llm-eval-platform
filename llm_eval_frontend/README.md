# LLM Leaderboard App

A web application for tracking, comparing, and visualizing language model performance across different providers, datasets, and metrics.

## Features

- Track multiple LLM providers and their models
- Manage datasets and dataset items for evaluation
- Record model inferences and their results
- Define and track various performance metrics
- View leaderboards based on different evaluation criteria

## Tech Stack

- React 18 with TypeScript
- Material UI for component library
- React Router for navigation
- React Query for API data management
- Vite for fast development and building

## Installation

### Prerequisites

- Node.js (version 16 or higher)
- npm or yarn

### Setup

1. Clone the repository:

```bash
git clone https://github.com/r488it/llm-leaderboard-app.git
cd llm-leaderboard-app
```

2. Install dependencies:

```bash
npm install
```

or using yarn:

```bash
yarn install
```

## Usage

### Development

To start the development server:

```bash
npm run dev
```

This will start the development server at `http://localhost:3000` (default Vite port).

### Building for Production

To build the application for production:

```bash
npm run build
```

This will create optimized production files in the `dist` directory.

### Preview Production Build

To preview the production build locally:

```bash
npm run preview
```

### Type Checking

Run TypeScript type checking without emitting files:

```bash
npm run typecheck
```

### Linting

Run ESLint to check for code quality issues:

```bash
npm run lint
```

## Application Structure

- `/src` - Main source code
  - `/api` - API client and service files for data fetching
  - `/components` - Reusable UI components
  - `/contexts` - React context providers
  - `/hooks` - Custom React hooks
  - `/pages` - Top-level page components
  - `/types` - TypeScript interfaces and type definitions

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.