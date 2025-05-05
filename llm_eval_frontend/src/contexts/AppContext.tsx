import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Provider } from '../types/provider';

interface AppContextType {
  // プロバイダ関連の状態
  selectedProvider: Provider | null;
  setSelectedProvider: (provider: Provider | null) => void;
  
  // テーマ設定
  darkMode: boolean;
  toggleDarkMode: () => void;
  
  // その他のアプリケーション全体の状態
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  clearError: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  // プロバイダ関連の状態
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  
  // テーマ設定
  const [darkMode, setDarkMode] = useState<boolean>(
    localStorage.getItem('darkMode') === 'true'
  );
  
  // その他のアプリケーション全体の状態
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // ダークモードの切り替え
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', String(newDarkMode));
  };

  // エラーのクリア
  const clearError = () => {
    setError(null);
  };

  const value = {
    selectedProvider,
    setSelectedProvider,
    darkMode,
    toggleDarkMode,
    isLoading,
    setIsLoading,
    error,
    setError,
    clearError,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useAppContext = (): AppContextType => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
