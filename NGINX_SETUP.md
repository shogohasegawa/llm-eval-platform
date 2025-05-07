# Nginxリバースプロキシ設定ガイド

このガイドでは、Nginxをリバースプロキシとして使用して、すべてのLLM Evaluation Platformのサービスに単一のポートからアクセスする方法を説明します。

## メリット

1. **単一のエントリーポイント** - すべてのサービスに同じポート（80）からアクセス可能
2. **クロスドメイン問題の解決** - 同一オリジンからのアクセスにより、CORS問題を回避
3. **統一されたURLスキーム** - シンプルなURLパスでサービスを区別

## インストール方法

### 1. Nginxのインストール

```bash
# Ubuntuの場合
sudo apt update
sudo apt install nginx

# CentOS/RHELの場合
sudo yum install epel-release
sudo yum install nginx
```

### 2. 設定ファイルのコピー

```bash
sudo cp /home/shogohasegawa/workspace/llm-eval-platform/nginx.conf /etc/nginx/nginx.conf
```

### 3. Nginxの起動

```bash
sudo systemctl restart nginx
sudo systemctl enable nginx  # システム起動時に自動起動
```

## アクセス方法

Nginxを設定すると、以下のURLからサービスにアクセスできます：

- **フロントエンド**: http://サーバーIPアドレス/ui/
- **APIサーバー**: http://サーバーIPアドレス/api/
- **MLflow**: http://サーバーIPアドレス/mlflow/
- **APIドキュメント**: http://サーバーIPアドレス/docs

すべてのサービスが同じポート（80）で提供されるため、クロスドメイン問題が解消され、MLflowの実行詳細表示の問題も解決されます。

## トラブルシューティング

### Nginxのログ確認

```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Nginxの設定テスト

```bash
sudo nginx -t
```

### Nginxの再起動

```bash
sudo systemctl restart nginx
```

## セキュリティ上の注意点

本番環境では、以下のセキュリティ対策を検討してください：

1. SSL/TLS証明書の設定（HTTPS対応）
2. アクセス制限の追加（IPベースのアクセス制限など）
3. Basic認証またはその他の認証方式の導入

## SSL/TLS証明書の設定例

Let's Encryptを使用したSSL/TLS証明書の取得方法：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

設定後はHTTPSでアクセスできるようになります：
https://your-domain.com/ui/