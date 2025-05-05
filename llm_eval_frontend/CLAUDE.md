# LLM Evaluation Platform - Frontend Development Guide

## Commands
- Build: `npm run build`
- Dev server: `npm run dev` (バックエンドAPIが起動していることを確認)
- Lint: `npm run lint`
- Typecheck: `npm run typecheck`
- 本番プレビュー: `npm run preview`

## 環境構築
1. 依存関係のインストール: `npm install`
2. `.env`ファイルの設定: `VITE_API_BASE_URL=http://localhost:8000`
3. バックエンドサーバーの起動確認
4. フロントエンド開発サーバーの起動: `npm run dev`

## アーキテクチャ
- **API通信**: `/api`ディレクトリ内のAPIクライアントを使用してバックエンドと通信
- **データアクセス**: 常にバックエンドAPIを経由し、フロントエンドからDBに直接アクセスしない
- **プロキシ設定**: 開発時は`/api/*`リクエストをバックエンドに転送

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