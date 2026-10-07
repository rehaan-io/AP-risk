
import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';

export type ConfigState = {
  policy_mode: string;
  po_mode: string;
  setup_completed: boolean;
};

type ConfigContextType = {
  config: ConfigState | null;
  loading: boolean;
  refreshConfig: () => Promise<void>;
};

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export const ConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<ConfigState | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshConfig = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/config`);
      setConfig(res.data);
    } catch (e) {
      console.error('Failed to fetch config', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshConfig();
  }, []);

  return <ConfigContext.Provider value={{ config, loading, refreshConfig }}>{children}</ConfigContext.Provider>;
};

export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) throw new Error('useConfig must be used within ConfigProvider');
  return context;
};

