# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Development Guidelines

## Backend (Python FastAPI)

### Build & Test Commands
- Install dependencies: `cd llm_eval_backend && uv init && uv sync`
- Run all tests: `cd llm_eval_backend && pytest tests -vv` 
- Run single test: `cd llm_eval_backend && pytest tests/test_file.py::test_function_name -v`
- Run backend server (development): `cd llm_eval_backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Run backend server (production): `cd llm_eval_backend && python -m src.app.main`

## Frontend (React/TypeScript)

### Build & Test Commands
- Install dependencies: `cd llm_eval_frontend && npm install`
- Run frontend (development): `cd llm_eval_frontend && npm run dev`
- Build frontend: `cd llm_eval_frontend && npm run build`
- Type checking: `cd llm_eval_frontend && npm run typecheck`
- Lint frontend: `cd llm_eval_frontend && npm run lint`

## Docker

### Docker Commands
- Build and run all services: `docker-compose up -d`
- Build and run specific service: `docker-compose up -d service_name`
- View logs: `docker-compose logs -f service_name`
- Stop services: `docker-compose down`

## Code Style Guidelines

### Backend
- Python version: 3.11+
- Code formatting: Black with default settings
- Type annotations required for function parameters and return values
- Imports organization: standard library, third-party, local
- Use explicit exception handling

### Frontend
- TypeScript with React
- Use React hooks for state management
- Follow component structure in `components/` directory
- API clients in `api/` directory

# Architecture Overview

## System Components

1. **Backend (llm_eval_backend)**
   - FastAPI-based REST API
   - Metrics implementation for LLM evaluation
   - Dataset management
   - Integration with various LLM providers (OpenAI, Anthropic, Ollama)
   - Proxy functionality for MLflow and Ollama

2. **Frontend (llm_eval_frontend)**
   - React/TypeScript SPA
   - Material UI components
   - React Router for navigation
   - React Query for data fetching and caching

3. **Infrastructure (docker-compose.yml)**
   - API server container
   - Frontend container
   - MLflow for experiment tracking
   - Ollama for local model hosting

## Key Modules

### Backend

- **app/api/**: API endpoints and schemas
- **app/metrics/**: LLM evaluation metrics implementations
- **app/utils/**: Utility functions and helpers
- **app/core/**: Core evaluation logic

### Frontend

- **src/api/**: API client functions
- **src/components/**: Reusable UI components
- **src/contexts/**: React Context providers
- **src/hooks/**: Custom React hooks
- **src/pages/**: Page components
- **src/types/**: TypeScript type definitions

## Data Flow

1. Datasets are loaded and processed by the backend
2. LLM providers (Ollama, OpenAI, etc.) are configured
3. Models generate responses based on prompts from datasets
4. Metrics calculate scores by comparing generated responses with expected answers
5. Results are tracked in MLflow and displayed in the frontend

## Key Features

- Support for multiple LLM providers
- Various evaluation metrics (char_f1, exact_match, etc.)
- Few-shot learning capability
- Leaderboard for model comparison
- Dataset management
- MLflow integration for experiment tracking

## 新しい開発ルール

- 必ず日本語で応対すること
- 挙動が把握しやすいようにloggerを活用すること
- デバックを行う際には適宜ユーザーにログの連携を要求すること
- わからないことがあれば適宜tavily-mcpを使用してweb検索を行うこと
- 不要なファイル・不要な実装は必ず本当に不要なのか関連する実装を確認した上で、プロジェクト上に残さないようにすること
- もしコンテナの再ビルド・再起動などユーザー側のアクションが必要であればコマンドを示すこと
- 設定などはなるべく実装コードにハードコードせずにconfigや.envなどで一元管理するようにしたい
- コンテナの再ビルド・再起動は必要に応じて実行すること
- 改修を実行する際にはむやみにコードを変更するのではなく、ログや実装コードなどを基に原因を特定した上で改修してください
- プロジェクトroot配下のdocs/にプロジェクトに関する説明がmdファイルとして保存されているので適宜参照・更新してください