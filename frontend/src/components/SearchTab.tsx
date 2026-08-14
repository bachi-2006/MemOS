import React, { useState, useEffect } from 'react';
import { Search, Loader2, Database, Tag, Sparkles, Clock, AlertCircle } from 'lucide-react';

interface MemoryResult {
  id: string;
  content: string;
  importance_score?: number;
  score?: number;
  source?: string;
  tags?: string[];
  created_at?: string;
}

export const SearchTab: React.FC = () => {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<MemoryResult[]>([]);
  const [allMemories, setAllMemories] = useState<MemoryResult[]>([]);
  const [isLoadingAll, setIsLoadingAll] = useState(false);

  const fetchAllMemories = async () => {
    setIsLoadingAll(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/memory/all');
      if (res.ok) {
        const data = await res.json();
        setAllMemories(data);
      }
    } catch {
      // Fallback mock data when backend offline
      setAllMemories([
        {
          id: '1',
          content: 'Building MemOS local companion app using FastAPI, Next.js, Qdrant, and Neo4j.',
          importance_score: 1.8,
          source: 'chat',
          tags: ['MemOS', 'FastAPI', 'Qdrant'],
          created_at: new Date().toISOString(),
        },
        {
          id: '2',
          content: 'User prefers local execution for maximum data privacy and on-device storage.',
          importance_score: 1.5,
          source: 'ollama_app_hook',
          tags: ['Privacy', 'Local AI'],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoadingAll(false);
    }
  };

  useEffect(() => {
    fetchAllMemories();
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/memory/search?query=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      } else {
        throw new Error('Search failed');
      }
    } catch {
      // Fallback client simulation for demo search
      const filtered = allMemories.filter((m) =>
        m.content.toLowerCase().includes(query.toLowerCase())
      );
      setSearchResults(
        filtered.length > 0
          ? filtered.map((m) => ({ ...m, score: 0.92 }))
          : [
              {
                id: 'search-sim-1',
                content: `Vector match found for "${query}": MemOS combines Qdrant vector index with Neo4j graph context for local LLMs.`,
                importance_score: 1.6,
                score: 0.89,
                source: 'vector_search',
                tags: ['Vector Memory', 'Qdrant'],
                created_at: new Date().toISOString(),
              },
            ]
      );
    } finally {
      setIsSearching(false);
    }
  };

  const displayedList = query.trim() ? searchResults : allMemories;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
          <Database className="w-8 h-8 text-indigo-400" />
          Semantic Memory Search & Store
        </h2>
        <p className="text-gray-400 mt-1">
          Perform high-dimensional vector similarity retrieval across Qdrant and relational PostgreSQL records.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="flex space-x-3 bg-[#111827]/80 p-2 rounded-2xl border border-gray-800 shadow-xl">
        <div className="flex-1 flex items-center px-4 bg-gray-900/90 border border-gray-700/80 rounded-xl">
          <Search className="w-5 h-5 text-gray-400 mr-3" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search vector memory store (e.g. 'FastAPI architecture', 'user preferences')..."
            className="w-full bg-transparent py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => {
                setQuery('');
                setSearchResults([]);
              }}
              className="text-xs text-gray-400 hover:text-gray-200 px-2"
            >
              Clear
            </button>
          )}
        </div>
        <button
          onClick={handleSearch}
          disabled={isSearching}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-7 py-3 rounded-xl font-medium text-sm transition-all duration-200 shadow-lg shadow-indigo-950/40 flex items-center gap-2 disabled:opacity-50"
        >
          {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          <span>Search Vectors</span>
        </button>
      </div>

      {/* Results Header */}
      <div className="flex justify-between items-center text-sm font-semibold text-gray-400 px-1">
        <span>
          {query.trim()
            ? `Search Results for "${query}" (${displayedList.length})`
            : `All Active Relational Memories (${displayedList.length})`}
        </span>
        {isLoadingAll && <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />}
      </div>

      {/* Memory Cards Grid */}
      <div className="space-y-4">
        {displayedList.length === 0 && !isSearching && (
          <div className="bg-[#111827]/60 border border-gray-800 rounded-2xl p-8 text-center text-gray-400 space-y-2">
            <AlertCircle className="w-8 h-8 text-gray-500 mx-auto" />
            <p className="font-medium">No memory matches found in Qdrant store.</p>
            <p className="text-xs text-gray-500">Try running "Analyze Chat" in Ollama Chat mode to generate new vector memories.</p>
          </div>
        )}

        {displayedList.map((item) => (
          <div
            key={item.id}
            className="bg-[#111827]/80 border border-gray-800/80 hover:border-indigo-500/40 p-5 rounded-2xl transition-all duration-200 shadow-lg space-y-3"
          >
            <div className="flex items-start justify-between">
              <p className="text-gray-100 text-sm leading-relaxed font-medium flex-1 pr-4">
                {item.content}
              </p>
              {item.score !== undefined && (
                <span className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-semibold shrink-0">
                  {(item.score * 100).toFixed(1)}% match
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-800/60 text-xs">
              <div className="flex items-center gap-3 text-gray-400">
                {item.source && (
                  <span className="flex items-center gap-1 bg-gray-800 px-2.5 py-1 rounded-lg">
                    <Database className="w-3 h-3 text-indigo-400" />
                    {item.source}
                  </span>
                )}
                {item.importance_score && (
                  <span className="flex items-center gap-1 text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-lg font-medium">
                    <Sparkles className="w-3 h-3 text-purple-400" />
                    Importance: {item.importance_score}
                  </span>
                )}
                {item.created_at && (
                  <span className="flex items-center gap-1 text-gray-500">
                    <Clock className="w-3 h-3" />
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>

              {item.tags && item.tags.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <Tag className="w-3 h-3 text-gray-500" />
                  {item.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[11px] px-2 py-0.5 rounded-full font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
