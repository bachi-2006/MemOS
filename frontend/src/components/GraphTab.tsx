import React, { useState, useEffect } from 'react';
import { Network, Cpu, Target, Code, Sparkles, RefreshCw, Layers } from 'lucide-react';

interface GraphNode {
  id: string;
  name: string;
  type: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export const GraphTab: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  const fetchGraph = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/graph/');
      if (res.ok) {
        const data = await res.json();
        if (data.nodes && data.nodes.length > 0) {
          setNodes(data.nodes);
          setEdges(data.edges || []);
        } else {
          setFallbackGraph();
        }
      } else {
        setFallbackGraph();
      }
    } catch {
      setFallbackGraph();
    } finally {
      setIsLoading(false);
    }
  };

  const setFallbackGraph = () => {
    setNodes([
      { id: '1', name: 'User', type: 'Person' },
      { id: '2', name: 'MemOS', type: 'Project' },
      { id: '3', name: 'FastAPI', type: 'Technology' },
      { id: '4', name: 'Next.js', type: 'Technology' },
      { id: '5', name: 'Qdrant', type: 'Technology' },
      { id: '6', name: 'Neo4j', type: 'Technology' },
      { id: '7', name: 'AI Engineering', type: 'Skill' },
    ]);
    setEdges([
      { source: 'User', target: 'MemOS', relationship: 'DEVELOPING' },
      { source: 'MemOS', target: 'FastAPI', relationship: 'USES_BACKEND' },
      { source: 'MemOS', target: 'Next.js', relationship: 'USES_FRONTEND' },
      { source: 'MemOS', target: 'Qdrant', relationship: 'USES_VECTOR_STORE' },
      { source: 'MemOS', target: 'Neo4j', relationship: 'USES_GRAPH_STORE' },
      { source: 'User', target: 'AI Engineering', relationship: 'SKILLED_IN' },
    ]);
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const filteredNodes =
    selectedFilter === 'all'
      ? nodes
      : nodes.filter((n) => n.type.toLowerCase() === selectedFilter.toLowerCase());

  const getNodeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'project':
        return <Target className="w-4 h-4 text-purple-400" />;
      case 'technology':
        return <Code className="w-4 h-4 text-indigo-400" />;
      case 'skill':
        return <Cpu className="w-4 h-4 text-emerald-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-amber-400" />;
    }
  };

  const getTypeStyle = (type: string) => {
    switch (type.toLowerCase()) {
      case 'project':
        return 'bg-purple-500/10 border-purple-500/30 text-purple-300';
      case 'technology':
        return 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300';
      case 'skill':
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300';
      default:
        return 'bg-amber-500/10 border-amber-500/30 text-amber-300';
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
            <Network className="w-8 h-8 text-indigo-400" />
            Knowledge Graph Synapses (Neo4j)
          </h2>
          <p className="text-gray-400 mt-1">
            Entity-Relationship Graph dynamically updated during memory extraction & chat analysis.
          </p>
        </div>

        <button
          onClick={fetchGraph}
          disabled={isLoading}
          className="flex items-center space-x-2 bg-gray-800 hover:bg-gray-700 text-gray-200 px-4 py-2 rounded-xl border border-gray-700 text-xs font-semibold transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Sync Graph</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
        <span className="text-xs text-gray-400 font-medium mr-2">Filter Entities:</span>
        {['all', 'project', 'technology', 'skill', 'person'].map((filter) => (
          <button
            key={filter}
            onClick={() => setSelectedFilter(filter)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              selectedFilter === filter
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 shadow-sm'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* Node & Triple Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Extracted Entity Nodes */}
        <div className="bg-[#111827]/80 border border-gray-800 p-6 rounded-2xl shadow-xl space-y-4">
          <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Graph Entity Nodes ({filteredNodes.length})
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-1">
            {filteredNodes.map((node) => (
              <div
                key={node.id}
                className={`p-3 rounded-xl border flex items-center space-x-3 ${getTypeStyle(node.type)}`}
              >
                <div className="p-2 bg-gray-900/60 rounded-lg">{getNodeIcon(node.type)}</div>
                <div className="overflow-hidden">
                  <div className="text-sm font-semibold truncate">{node.name}</div>
                  <div className="text-[10px] uppercase font-bold tracking-wider opacity-75">{node.type}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Knowledge Triples (Relationships) */}
        <div className="bg-[#111827]/80 border border-gray-800 p-6 rounded-2xl shadow-xl space-y-4">
          <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <Network className="w-5 h-5 text-purple-400" />
            Knowledge Triples ({edges.length})
          </h3>

          <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            {edges.map((edge, idx) => (
              <div
                key={idx}
                className="bg-gray-900/90 border border-gray-800/80 p-3 rounded-xl flex items-center justify-between text-xs"
              >
                <span className="font-semibold text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                  {edge.source}
                </span>

                <div className="flex flex-col items-center px-2">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">
                    -- [{edge.relationship}] --&gt;
                  </span>
                </div>

                <span className="font-semibold text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                  {edge.target}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
