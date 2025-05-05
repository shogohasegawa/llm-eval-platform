# LLM Evaluation Platform - Frontend

フロントエンドアプリケーションで、言語モデルのパフォーマンスを追跡、比較、可視化するためのWebUIを提供します。

## 機能

- 複数のLLMプロバイダーとそのモデルを管理
- 評価用のデータセットとデータセットアイテムを管理
- モデル推論と結果を記録
- さまざまなパフォーマンス指標を定義・追跡
- 異なる評価基準に基づくリーダーボードを表示

## 技術スタック

- React 18 with TypeScript
- Material UI コンポーネントライブラリ
- React Router ナビゲーション
- React Query API データ管理
- Vite 高速開発とビルド

## インストール

### 前提条件

- Node.js (version 16 以上)
- npm または yarn
- バックエンドAPIサーバー（`llm_eval_backend`）が実行中であること

### セットアップ

1. 依存関係をインストール:

```bash
npm install
```

または yarn を使用:

```bash
yarn install
```

2. 環境変数の設定:

`.env` ファイルを作成して以下の内容を設定:

```
VITE_API_BASE_URL=http://localhost:8000
```

※ バックエンドAPIのURLに合わせて調整してください

## 使用方法

### 開発

開発サーバーを起動（バックエンドAPIが実行中であることを確認）:

```bash
npm run dev
```

これにより開発サーバーが `http://localhost:3000` で起動します。

### 本番用ビルド

本番用にアプリケーションをビルド:

```bash
npm run build
```

これにより `dist` ディレクトリに最適化された本番ファイルが作成されます。

### 本番ビルドのプレビュー

本番ビルドをローカルでプレビュー:

```bash
npm run preview
```

### 型チェック

ファイルを生成せずにTypeScriptの型チェックを実行:

```bash
npm run typecheck
```

### Lint

コード品質の問題をチェックするためにESLintを実行:

```bash
npm run lint
```

## アプリケーション構造

- `/src` - メインソースコード
  - `/api` - APIクライアントとデータフェッチング用のサービスファイル
  - `/components` - 再利用可能なUIコンポーネント
  - `/contexts` - Reactコンテキストプロバイダー
  - `/hooks` - カスタムReactフック
  - `/pages` - トップレベルのページコンポーネント
  - `/types` - TypeScriptインターフェースと型定義

## バックエンドAPIとの連携

このフロントエンドアプリケーションは、`llm_eval_backend`で提供されるAPIエンドポイントを使用してデータを取得・更新します。
開発時には、Viteのプロキシ機能を使用して `/api` リクエストをバックエンドサーバーに転送します。

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細についてはLICENSEファイルを参照してください。