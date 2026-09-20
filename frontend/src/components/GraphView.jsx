import { useEffect, useState, useMemo } from "react";
import { fetchGraph } from "../lib/api.js";

const NODE_COLORS = {
  project: { bg: "#8b5cf6", border: "#7c3aed", glow: "rgba(139, 92, 246, 0.4)", text: "#ffffff" },
  technology: { bg: "#3b82f6", border: "#2563eb", glow: "rgba(59, 130, 246, 0.4)", text: "#ffffff" },
  tech: { bg: "#3b82f6", border: "#2563eb", glow: "rgba(59, 130, 246, 0.4)", text: "#ffffff" },
  skill: { bg: "#10b981", border: "#059669", glow: "rgba(16, 185, 129, 0.4)", text: "#ffffff" },
  concept: { bg: "#f59e0b", border: "#d97706", glow: "rgba(245, 158, 11, 0.4)", text: "#ffffff" },
  user: { bg: "#ec4899", border: "#db2777", glow: "rgba(236, 72, 153, 0.4)", text: "#ffffff" },
};

export default function GraphView({ onToast }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [connected, setConnected] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const data = await fetchGraph();
      if (data) {
        const incomingNodes = Array.isArray(data.nodes) ? data.nodes : [];
        const incomingEdges = Array.isArray(data.edges) ? data.edges : [];
        setNodes(incomingNodes);
        setEdges(incomingEdges);
        setConnected(true);
        if (onToast && incomingNodes.length > 0) {
          onToast(`Graph Synced: ${incomingNodes.length} memory entities mapped`);
        }
      }
    } catch {
      setNodes([]);
      setEdges([]);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      if (filter !== "all" && (n.type || "").toLowerCase() !== filter.toLowerCase()) return false;
      if (searchQuery) {
        return (n.label || n.id).toLowerCase().includes(searchQuery.toLowerCase());
      }
      return true;
    });
  }, [nodes, filter, searchQuery]);

  const nodePositions = useMemo(() => {
    const pos = {};
    const count = nodes.length;
    if (!count) return pos;

    const width = 860;
    const height = 480;
    const cx = width / 2;
    const cy = height / 2;

    const centerNode = nodes.find((n) => (n.type || "").toLowerCase() === "user") || nodes[0];
    if (centerNode) pos[centerNode.id] = { x: cx, y: cy };

    const otherNodes = nodes.filter((n) => !centerNode || n.id !== centerNode.id);
    const totalOthers = otherNodes.length;
    const innerCount = Math.min(6, totalOthers);
    const outerCount = totalOthers - innerCount;

    const innerRadius = 140;
    const outerRadius = 220;

    otherNodes.forEach((node, i) => {
      let r, angle;
      if (i < innerCount) {
        r = innerRadius;
        angle = (i / innerCount) * 2 * Math.PI - Math.PI / 2;
      } else {
        r = outerRadius;
        const outerIndex = i - innerCount;
        angle = (outerIndex / Math.max(1, outerCount)) * 2 * Math.PI - Math.PI / 4;
      }
      pos[node.id] = {
        x: Math.round(cx + r * Math.cos(angle)),
        y: Math.round(cy + r * Math.sin(angle)),
      };
    });

    return pos;
  }, [nodes]);

  const activeNodeId = hoveredNodeId || selectedNodeId;
  const selectedNode = useMemo(() => nodes.find((n) => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);
  const selectedEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return edges.filter((e) => e.source === selectedNodeId || e.target === selectedNodeId);
  }, [edges, selectedNodeId]);

  return (
    <div className="view-panel" id="viewGraph">
      <div className="panel-head">
        <div>
          <h2>Memory Knowledge Graph</h2>
          <p className="panel-sub">
            Interactive associative entity graph mapped from your persistent memories, facts, and profile traits.
          </p>
        </div>
        <div className="panel-actions">
          <button className="btn outline" onClick={fetchGraph} disabled={loading}>
            {loading ? "Syncing…" : "↻ Sync Graph"}
          </button>
        </div>
      </div>

      <div className="graph-stats-row">
        <div className="graph-badge">
          <span className="dot on" />
          <span>{nodes.length} Entity Nodes</span>
        </div>
        <div className="graph-badge">
          <span className="dot on" />
          <span>{edges.length} Knowledge Triples</span>
        </div>
        <div className="graph-filters">
          {["all", "project", "technology", "skill", "concept"].map((f) => (
            <button
              key={f}
              className={"filter-chip" + (filter === f ? " active" : "")}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="graph-search">
          <input
            type="text"
            placeholder="Find node…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {nodes.length === 0 ? (
        <div className="empty-graph-card">
          <div className="empty-graph-icon">🧠</div>
          <h3>Your Memory Knowledge Graph is Empty</h3>
          <p>
            The knowledge graph visualizes entities, projects, skills, and relationships
            automatically mapped from your memories and conversation facts.
          </p>
          <div className="empty-hint">
            💡 <strong>Tip:</strong> Start chatting with MemOS or teach it a fact in the <em>Memory Drawer</em> (e.g. &ldquo;I prefer FastAPI for microservices&rdquo;), and your personal knowledge graph will connect here automatically!
          </div>
        </div>
      ) : (
        <>
          {/* Interactive SVG Node-Link Canvas */}
          <div className="svg-canvas-container">
            <svg viewBox="0 0 860 480" className="graph-svg" preserveAspectRatio="xMidYMid meet">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(148, 163, 184, 0.6)" />
            </marker>
            <marker id="arrow-active" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#8b5cf6" />
            </marker>
          </defs>

          {/* Render Edges */}
          <g className="edges-layer">
            {edges.map((e, idx) => {
              const srcPos = nodePositions[e.source];
              const tgtPos = nodePositions[e.target];
              if (!srcPos || !tgtPos) return null;

              const isEdgeActive = activeNodeId && (e.source === activeNodeId || e.target === activeNodeId);
              const isDimmed = activeNodeId && !isEdgeActive;
              const dx = tgtPos.x - srcPos.x;
              const dy = tgtPos.y - srcPos.y;
              const mx = (srcPos.x + tgtPos.x) / 2 - dy * 0.1;
              const my = (srcPos.y + tgtPos.y) / 2 + dx * 0.1;
              const pathD = `M ${srcPos.x} ${srcPos.y} Q ${mx} ${my} ${tgtPos.x} ${tgtPos.y}`;

              return (
                <g key={idx} className={"graph-edge " + (isEdgeActive ? "active" : "") + (isDimmed ? " dimmed" : "")}>
                  <path
                    d={pathD}
                    fill="none"
                    stroke={isEdgeActive ? "#8b5cf6" : "rgba(148, 163, 184, 0.3)"}
                    strokeWidth={isEdgeActive ? 2.5 : 1.5}
                    markerEnd={isEdgeActive ? "url(#arrow-active)" : "url(#arrow)"}
                  />
                  <text
                    x={mx}
                    y={my}
                    className="edge-label"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={isEdgeActive ? "#a78bfa" : "rgba(148, 163, 184, 0.7)"}
                    fontSize={10}
                    fontWeight={isEdgeActive ? "600" : "400"}
                  >
                    {e.relationship}
                  </text>
                </g>
              );
            })}
          </g>

          {/* Render Nodes */}
          <g className="nodes-layer">
            {nodes.map((n) => {
              const pos = nodePositions[n.id];
              if (!pos) return null;

              const colorInfo = NODE_COLORS[(n.type || "").toLowerCase()] || NODE_COLORS.concept;
              const isSelected = selectedNodeId === n.id;
              const isHovered = hoveredNodeId === n.id;
              const isConnectedToActive =
                activeNodeId &&
                edges.some(
                  (e) =>
                    (e.source === activeNodeId && e.target === n.id) ||
                    (e.target === activeNodeId && e.source === n.id)
                );
              const isHighlighted = isSelected || isHovered || isConnectedToActive || activeNodeId === n.id;
              const isDimmed = activeNodeId && !isHighlighted;
              const isMatch = !searchQuery || (n.label || n.id).toLowerCase().includes(searchQuery.toLowerCase());

              return (
                <g
                  key={n.id}
                  className={"graph-node " + (isSelected ? "selected" : "") + (isDimmed ? " dimmed" : "")}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => setSelectedNodeId(isSelected ? null : n.id)}
                  onMouseEnter={() => setHoveredNodeId(n.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  style={{ cursor: "pointer" }}
                >
                  {isHighlighted && <circle r={28} fill={colorInfo.glow} className="node-glow" />}
                  <circle
                    r={20}
                    fill={colorInfo.bg}
                    stroke={isSelected ? "#ffffff" : colorInfo.border}
                    strokeWidth={isSelected ? 3 : 2}
                  />
                  <text textAnchor="middle" dominantBaseline="central" fill={colorInfo.text} fontSize={11} fontWeight="700">
                    {(n.label || n.id).slice(0, 2).toUpperCase()}
                  </text>
                  <text y={32} textAnchor="middle" className="node-svg-label" fill={isMatch ? "var(--fg)" : "var(--muted)"} fontSize={11} fontWeight={isHighlighted ? "600" : "500"}>
                    {n.label || n.id}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {selectedNode && (
          <div className="graph-inspector">
            <div className="inspector-head">
              <span className="inspector-title">{selectedNode.label || selectedNode.id}</span>
              <button className="inspector-close" onClick={() => setSelectedNodeId(null)}>×</button>
            </div>
            <div className="inspector-badge">
              <span className={"type-pill " + (selectedNode.type || "concept").toLowerCase()}>
                {selectedNode.type || "Concept"}
              </span>
            </div>
            <div className="inspector-sub">Connected Relationships ({selectedEdges.length}):</div>
            <div className="inspector-triples">
              {selectedEdges.length === 0 ? (
                <div className="inspector-empty">No direct edges linked.</div>
              ) : (
                selectedEdges.map((e, idx) => (
                  <div key={idx} className="inspector-triple-row">
                    <span className="t-src">{e.source}</span>
                    <span className="t-rel">--[{e.relationship}]--&gt;</span>
                    <span className="t-tgt">{e.target}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Grid below canvas: Entity Nodes & Triples */}
      <div className="graph-grid">
        <div className="graph-card">
          <div className="graph-card-head">
            <span>Entity Nodes ({filteredNodes.length})</span>
          </div>
          <div className="node-list">
            {filteredNodes.length === 0 ? (
              <div className="empty-sub">No graph nodes found for &ldquo;{filter}&rdquo;</div>
            ) : (
              filteredNodes.map((n, i) => (
                <div
                  key={i}
                  className={"node-chip " + (n.type || "concept").toLowerCase() + (selectedNodeId === n.id ? " active" : "")}
                  onClick={() => setSelectedNodeId(selectedNodeId === n.id ? null : n.id)}
                  style={{ cursor: "pointer" }}
                >
                  <span className="node-icon">◆</span>
                  <span className="node-name">{n.label || n.id}</span>
                  <span className="node-type">{n.type || "Concept"}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="graph-card">
          <div className="graph-card-head">
            <span>Knowledge Triples ({edges.length})</span>
          </div>
          <div className="triple-list">
            {edges.length === 0 ? (
              <div className="empty-sub">No knowledge triples extracted yet. Chat with MemOS to generate entity relationships!</div>
            ) : (
              edges.map((e, i) => (
                <div key={i} className="triple-row">
                  <span className="triple-src">{e.source}</span>
                  <span className="triple-rel">-- [{e.relationship}] --&gt;</span>
                  <span className="triple-tgt">{e.target}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  );
}
