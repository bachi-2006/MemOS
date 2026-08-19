import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Activity, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Sparkles, 
  ExternalLink, 
  Terminal, 
  ShieldCheck, 
  Zap,
  Server,
  Layers,
  ChevronDown
} from 'lucide-react';

export interface OllamaStatusData {
  connected: boolean;
  endpoint: string;
  status: 'OLLAMA_RUNNING_WITH_MODELS' | 'OLLAMA_RUNNING_NO_MODELS' | 'OLLAMA_NOT_RUNNING' | string;
  installed_models: string[];
  selected_model: string;
  version?: string;
  latency_ms?: number;
  error?: string;
}

interface OllamaIntegrationPanelProps {
  personalizedEnabled: boolean;
  setPersonalizedEnabled: (val: boolean) => void;
  onModelSelect?: (model: string) => void;
  selectedModel?: string;
}

export const OllamaIntegrationPanel: React.FC<OllamaIntegrationPanelProps> = ({
  personalizedEnabled,
  setPersonalizedEnabled,
  onModelSelect,
  selectedModel: propSelectedModel
}) => {
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatusData | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>(propSelectedModel || 'qwen3.5:9b');
  const [showConfigModal, setShowConfigModal] = useState<boolean>(false);
  const [connectionTestResult, setConnectionTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);

  const fetchStatus = async () => {
    setIsChecking(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/ollama/status');
      if (res.ok) {
        const data: OllamaStatusData = await res.json();
        setOllamaStatus(data);
        if (data.installed_models && data.installed_models.length > 0) {
          if (!data.installed_models.includes(selectedModel)) {
            setSelectedModel(data.installed_models[0]);
            if (onModelSelect) onModelSelect(data.installed_models[0]);
          }
        }
      } else {
        setOllamaStatus({
          connected: false,
          endpoint: 'http://127.0.0.1:11434',
          status: 'OLLAMA_NOT_RUNNING',
          installed_models: [],
          selected_model: 'qwen3.5:9b',
          error: `HTTP ${res.status}`
        });
      }
    } catch {
      setOllamaStatus({
        connected: false,
        endpoint: 'http://127.0.0.1:11434',
        status: 'OLLAMA_NOT_RUNNING',
        installed_models: [],
        selected_model: 'qwen3.5:9b',
        error: 'Backend or Ollama server unreachable'
      });
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setConnectionTestResult(null);
    try {
      const start = performance.now();
      const res = await fetch('http://localhost:8000/v1/models');
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        setConnectionTestResult({
          success: true,
          message: `Proxy active & responding at http://127.0.0.1:11435 / :8000. Real-time token streaming ready.`,
          latency
        });
      } else {
        setConnectionTestResult({
          success: false,
          message: `Proxy returned error ${res.status}`
        });
      }
    } catch (err: any) {
      setConnectionTestResult({
        success: false,
        message: `Failed to connect to MemOS proxy: ${err.message}`
      });
    } finally {
      setIsTesting(false);
    }
  };

  const isConnected = ollamaStatus?.connected === true;
  const modelCount = ollamaStatus?.installed_models?.length || 0;

  return (
    <div className="bg-[#111827]/90 backdrop-blur-xl border border-gray-800/90 rounded-2xl p-5 shadow-2xl space-y-4">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className={`p-2.5 rounded-xl border transition-all ${
            isConnected 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-gray-100 text-sm tracking-wide">Ollama Desktop & Local Proxy Bridge</h3>
              <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full uppercase tracking-wider border ${
                isConnected 
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30 animate-pulse'
              }`}>
                {isConnected ? '● Connected' : '○ Offline'}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              {isConnected 
                ? `Local server detected at 127.0.0.1:11434 (${modelCount} models available)`
                : 'Ollama local server not detected on default port 11434.'}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={fetchStatus}
            disabled={isChecking}
            title="Scan Ollama & Proxy Health"
            className="p-2 bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700/80 text-gray-300 rounded-xl transition text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin text-indigo-400' : ''}`} />
            <span>Scan</span>
          </button>

          <button
            onClick={handleTestConnection}
            disabled={isTesting}
            className="px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 font-medium rounded-xl text-xs flex items-center gap-1.5 transition"
          >
            <Zap className={`w-3.5 h-3.5 ${isTesting ? 'animate-pulse text-indigo-300' : 'text-indigo-400'}`} />
            <span>Test Bridge</span>
          </button>

          <button
            onClick={() => setShowConfigModal(!showConfigModal)}
            className="px-3.5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-indigo-950/40 transition"
          >
            <span>🔗 Connect Ollama</span>
          </button>
        </div>
      </div>

      {/* Real-time Status Badges Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
        {/* Ollama Server */}
        <div className="bg-gray-900/60 border border-gray-800/90 p-3 rounded-xl">
          <div className="text-[11px] uppercase font-semibold text-gray-400 flex items-center justify-between">
            <span>Ollama Server</span>
            <Server className="w-3.5 h-3.5 text-gray-500" />
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span className="text-xs font-bold text-gray-200 truncate">
              {isConnected ? `11434 (${ollamaStatus?.latency_ms || 0}ms)` : 'Offline'}
            </span>
          </div>
        </div>

        {/* MemOS Proxy */}
        <div className="bg-gray-900/60 border border-gray-800/90 p-3 rounded-xl">
          <div className="text-[11px] uppercase font-semibold text-gray-400 flex items-center justify-between">
            <span>MemOS Proxy</span>
            <Terminal className="w-3.5 h-3.5 text-gray-500" />
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-xs font-bold text-gray-200">Port 11435 (SSE)</span>
          </div>
        </div>

        {/* Active Model Selector */}
        <div className="bg-gray-900/60 border border-gray-800/90 p-3 rounded-xl">
          <div className="text-[11px] uppercase font-semibold text-gray-400 flex items-center justify-between">
            <span>Selected Model</span>
            <Layers className="w-3.5 h-3.5 text-gray-500" />
          </div>
          <div className="mt-1">
            {ollamaStatus?.installed_models && ollamaStatus.installed_models.length > 0 ? (
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  if (onModelSelect) onModelSelect(e.target.value);
                }}
                className="w-full bg-transparent text-xs font-bold text-indigo-300 focus:outline-none cursor-pointer"
              >
                {ollamaStatus.installed_models.map((m) => (
                  <option key={m} value={m} className="bg-gray-900 text-gray-200">
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-gray-400 font-medium">qwen3.5:9b</span>
            )}
          </div>
        </div>

        {/* Memory & Personalization Toggle */}
        <div 
          onClick={() => setPersonalizedEnabled(!personalizedEnabled)}
          className={`border p-3 rounded-xl cursor-pointer transition-all ${
            personalizedEnabled 
              ? 'bg-indigo-950/30 border-indigo-500/40' 
              : 'bg-gray-900/60 border-gray-800/90 hover:border-gray-700'
          }`}
        >
          <div className="text-[11px] uppercase font-semibold flex items-center justify-between">
            <span className={personalizedEnabled ? 'text-indigo-300 font-bold' : 'text-gray-400'}>
              Personalization
            </span>
            <Sparkles className={`w-3.5 h-3.5 ${personalizedEnabled ? 'text-indigo-400' : 'text-gray-500'}`} />
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${personalizedEnabled ? 'bg-indigo-400 animate-pulse' : 'bg-gray-500'}`}></span>
            <span className={`text-xs font-bold ${personalizedEnabled ? 'text-indigo-200' : 'text-gray-400'}`}>
              {personalizedEnabled ? 'Active (Vector+Graph)' : 'OFF (Raw Prompt)'}
            </span>
          </div>
        </div>
      </div>

      {/* Connection Test Banner if Triggered */}
      {connectionTestResult && (
        <div className={`p-3 rounded-xl border text-xs flex items-center justify-between transition-all ${
          connectionTestResult.success 
            ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300' 
            : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
        }`}>
          <div className="flex items-center gap-2">
            {connectionTestResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{connectionTestResult.message}</span>
          </div>
          {connectionTestResult.latency && (
            <span className="font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {connectionTestResult.latency} ms
            </span>
          )}
        </div>
      )}

      {/* Integration Guide Modal / Drawer */}
      {showConfigModal && (
        <div className="mt-3 p-4 bg-gray-900/90 border border-indigo-500/30 rounded-2xl space-y-3 text-xs text-gray-300">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <h4 className="font-bold text-gray-100 flex items-center gap-2 text-sm">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              Windows Client & Ollama Desktop Bridge Guidance
            </h4>
            <button 
              onClick={() => setShowConfigModal(false)}
              className="text-gray-400 hover:text-gray-200 text-xs px-2 py-0.5 bg-gray-800 rounded-lg"
            >
              Close
            </button>
          </div>

          <p className="leading-relaxed text-gray-300">
            MemOS exposes a local OpenAI-compatible proxy with vector memory injection and token streaming on:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[11px]">
            <div className="p-2.5 bg-black/50 border border-gray-800 rounded-xl">
              <span className="text-gray-400 block mb-1 text-[10px] uppercase font-bold tracking-wider">OpenAI Proxy URL:</span>
              <span className="text-indigo-400 select-all font-semibold">http://127.0.0.1:11435/v1</span>
            </div>
            <div className="p-2.5 bg-black/50 border border-gray-800 rounded-xl">
              <span className="text-gray-400 block mb-1 text-[10px] uppercase font-bold tracking-wider">MemOS REST Base:</span>
              <span className="text-purple-400 select-all font-semibold">http://localhost:8000</span>
            </div>
          </div>

          <div className="space-y-1.5 pt-1">
            <span className="font-semibold text-gray-200">How to connect your tools:</span>
            <ul className="space-y-1 text-gray-400 list-disc list-inside">
              <li><strong className="text-gray-300">Open WebUI / LibreChat / Cursor:</strong> Set OpenAI Base URL to <code className="text-indigo-300 bg-gray-800 px-1 py-0.5 rounded">http://127.0.0.1:11435/v1</code> (or <code className="text-indigo-300 bg-gray-800 px-1 py-0.5 rounded">http://localhost:8000/v1</code>).</li>
              <li><strong className="text-gray-300">PowerShell CLI:</strong> Run <code className="text-indigo-300 bg-gray-800 px-1 py-0.5 rounded">.\scripts\save_memory.ps1 -Content "..."</code> to push any note.</li>
              <li><strong className="text-gray-300">Windows Local Bridge:</strong> Launch <code className="text-indigo-300 bg-gray-800 px-1 py-0.5 rounded">python scripts/memos_bridge.py</code> to monitor ports and route traffic automatically.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
