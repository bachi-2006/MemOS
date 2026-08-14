import React, { useState, useEffect } from 'react';
import { Database, Brain, Activity, Network, RefreshCw, MessageSquare, Archive, Trash2 } from 'lucide-react';

interface MetricsData {
  total_memories: number;
  active_memories: number;
  archived_memories: number;
  forgotten_memories: number;
  total_chats: number;
  average_importance_score: number;
  compression_ratio: string;
  retrieval_accuracy: string;
}

export const DashboardTab: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchMetrics = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/dashboard/metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Failed to load metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-gray-100">Memory Lifecycle Dashboard</h2>
          <p className="text-gray-400 mt-1">Real-time metrics for long-term agent context management.</p>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 rounded-xl transition text-sm font-medium"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Metrics
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl">
          <div className="flex justify-between items-center text-indigo-400 mb-2">
            <span className="text-sm font-medium">Total Memories</span>
            <Database className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {metrics ? metrics.total_memories.toLocaleString() : '---'}
          </div>
          <div className="text-xs text-gray-500 mt-2">Active across PostgreSQL & Qdrant</div>
        </div>

        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl">
          <div className="flex justify-between items-center text-purple-400 mb-2">
            <span className="text-sm font-medium">Avg Importance</span>
            <Brain className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {metrics ? metrics.average_importance_score : '---'}
          </div>
          <div className="text-xs text-gray-500 mt-2">Weighted Lifecycle Score</div>
        </div>

        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl">
          <div className="flex justify-between items-center text-emerald-400 mb-2">
            <span className="text-sm font-medium">Retrieval Confidence</span>
            <Activity className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {metrics ? metrics.retrieval_accuracy : '---'}
          </div>
          <div className="text-xs text-gray-500 mt-2">Vector Similarity + Context</div>
        </div>

        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl">
          <div className="flex justify-between items-center text-blue-400 mb-2">
            <span className="text-sm font-medium">Compression Savings</span>
            <Network className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {metrics ? metrics.compression_ratio : '---'}
          </div>
          <div className="text-xs text-gray-500 mt-2">Hierarchical Summary Savings</div>
        </div>
      </div>

      {/* Memory Status Breakdown */}
      {metrics && (
        <div className="bg-[#111827]/60 p-6 rounded-2xl border border-gray-800 shadow-xl">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">Memory Status Distribution</h3>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-gray-900/50 p-4 rounded-xl border border-emerald-500/20">
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
                <Database className="w-4 h-4" /> Active
              </div>
              <div className="text-2xl font-bold text-white mt-1">{metrics.active_memories}</div>
            </div>
            <div className="bg-gray-900/50 p-4 rounded-xl border border-amber-500/20">
              <div className="flex items-center gap-2 text-amber-400 text-sm font-medium">
                <Archive className="w-4 h-4" /> Archived
              </div>
              <div className="text-2xl font-bold text-white mt-1">{metrics.archived_memories}</div>
            </div>
            <div className="bg-gray-900/50 p-4 rounded-xl border border-rose-500/20">
              <div className="flex items-center gap-2 text-rose-400 text-sm font-medium">
                <Trash2 className="w-4 h-4" /> Forgotten
              </div>
              <div className="text-2xl font-bold text-white mt-1">{metrics.forgotten_memories}</div>
            </div>
            <div className="bg-gray-900/50 p-4 rounded-xl border border-indigo-500/20">
              <div className="flex items-center gap-2 text-indigo-400 text-sm font-medium">
                <MessageSquare className="w-4 h-4" /> Total Chats
              </div>
              <div className="text-2xl font-bold text-white mt-1">{metrics.total_chats}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
