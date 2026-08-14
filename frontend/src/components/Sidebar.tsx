import React from 'react';
import { Activity, MessageSquare, Search, Network, UserCheck, Brain } from 'lucide-react';

export type TabType = 'dashboard' | 'chat' | 'search' | 'graph' | 'profile';

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  return (
    <aside className="w-64 bg-[#111827] border-r border-gray-800/80 flex flex-col justify-between">
      <div>
        <div className="p-6 border-b border-gray-800/80 flex items-center space-x-3">
          <div className="p-2 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-indigo-400">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-indigo-400">MemOS</h1>
            <p className="text-xs text-gray-400 font-medium">Ollama Companion</p>
          </div>
        </div>

        <nav className="p-4 space-y-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              activeTab === 'dashboard'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-950/40 font-semibold'
                : 'text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'
            }`}
          >
            <Activity className="w-5 h-5" />
            <span className="text-sm">Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              activeTab === 'chat'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-950/40 font-semibold'
                : 'text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span className="text-sm">Ollama Chat</span>
          </button>

          <button
            onClick={() => setActiveTab('search')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              activeTab === 'search'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-950/40 font-semibold'
                : 'text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'
            }`}
          >
            <Search className="w-5 h-5" />
            <span className="text-sm">Semantic Search</span>
          </button>

          <button
            onClick={() => setActiveTab('graph')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              activeTab === 'graph'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-950/40 font-semibold'
                : 'text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'
            }`}
          >
            <Network className="w-5 h-5" />
            <span className="text-sm">Knowledge Graph</span>
          </button>

          <button
            onClick={() => setActiveTab('profile')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              activeTab === 'profile'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-950/40 font-semibold'
                : 'text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'
            }`}
          >
            <UserCheck className="w-5 h-5" />
            <span className="text-sm">User Profile</span>
          </button>
        </nav>
      </div>

      <div className="p-4 border-t border-gray-800/80">
        <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 px-3.5 py-2.5 rounded-xl border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-medium">Local Ollama Companion Ready</span>
        </div>
      </div>
    </aside>
  );
};
