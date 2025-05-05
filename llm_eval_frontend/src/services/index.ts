import app from './api';
import { databaseSetup } from '../db/setup';
import path from 'path';
import fs from 'fs';

const DB_PATH = path.resolve(process.cwd(), 'llm_leaderboard.db');

/**
 * データベースが存在するかチェック
 */
function isDatabaseInitialized() {
  try {
    return fs.existsSync(DB_PATH) && fs.statSync(DB_PATH).size > 0;
  } catch (error) {
    return false;
  }
}

/**
 * APIサーバーの初期化と起動
 */
async function startServer() {
  // データベースが初期化されていない場合はセットアップを実行
  const isInitialized = isDatabaseInitialized();
  
  // 初期化処理
  if (!isInitialized) {
    console.log('Database not initialized. Setting up initial data...');
    try {
      await databaseSetup.setupInitialData();
      console.log('Database initialization completed.');
    } catch (error) {
      console.error('Failed to initialize database:', error);
      console.log('Attempting to continue despite initialization errors...');
    }
  } else {
    console.log('Database already initialized.');
  }
  
  // APIサーバーを起動
  const PORT = process.env.PORT || 3001;
  app.listen(PORT, () => {
    console.log(`API server running on port ${PORT}`);
  });
}

// サーバーを起動
startServer().catch(error => {
  console.error('Failed to start server:', error);
  process.exit(1);
});

export default app;
