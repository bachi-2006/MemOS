import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { fetchGraph as fetchGraphAPI } from "../lib/api.js";

const NODE_COLORS = {
  project: { bg: "#8b5cf6", border: "#7c3aed", glow: "rgba(139, 92, 246, 0.45)", text: "#ffffff", label: "Project" },
  technology: { bg: "#3b82f6", border: "#2563eb", glow: "rgba(59, 130, 246, 0.45)", text: "#ffffff", label: "Technology" },
  tech: { bg: "#3b82f6", border: "#2563eb", glow: "rgba(59, 130, 246, 0.45)", text: "#ffffff", label: "Technology" },
  skill: { bg: "#10b981", border: "#059669", glow: "rgba(16, 185, 129, 0.45)", text: "#ffffff", label: "Skill" },
  concept: { bg: "#f59e0b", border: "#d97706", glow: "rgba(245, 158, 11, 0.45)", text: "#ffffff", label: "Concept" },
  user: { bg: "#ec4899", border: "#db2777", glow: "rgba(236, 72, 153, 0.5)", text: "#ffffff", label: "User Core" },
};

const WIDTH = 920;
const HEIGHT = 520;
const CX = WIDTH / 2;
const CY = HEIGHT / 2;

export default function GraphView({ onToast, memItems = [] }) {
  const [rawNodes, setRawNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [connected, setConnected] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Canvas Pan & Zoom
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const svgRef = useRef(null);

  // Physics Simulation Nodes (x, y, vx, vy, fx, fy)
  const [simNodes, setSimNodes] = useState([]);
  const simNodesRef = useRef([]);
  const edgesRef = useRef([]);
  const alphaRef = useRef(0);
  const animFrameRef = useRef(null);

  // Dragging state
  const draggingNodeRef = useRef(null);
  const isPanningRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0, initialPanX: 0, initialPanY: 0 });

  // 1. Fetch graph data cleanly without shadowing
  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGraphAPI();
      if (data) {
        const incomingNodes = Array.isArray(data.nodes) ? data.nodes : [];
        const incomingEdges = Array.isArray(data.edges) ? data.edges : [];
        setRawNodes(incomingNodes);
        setEdges(incomingEdges);
        setConnected(true);
        if (onToast && incomingNodes.length > 0) {
          onToast(`Graph Synced: ${incomingNodes.length} entities & ${incomingEdges.length} relations mapped`);
        }
      }
    } catch (err) {
      console.error("[GraphView] Failed to load graph:", err);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // 2. Initialize or merge simulation node positions
  useEffect(() => {
    edgesRef.current = edges;
    if (!rawNodes || rawNodes.length === 0) {
      setSimNodes([]);
      simNodesRef.current = [];
      return;
    }

    const existingMap = new Map();
    simNodesRef.current.forEach((n) => {
      existingMap.set(n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy });
    });

    const count = rawNodes.length;
    const newSimNodes = rawNodes.map((n, i) => {
      const existing = existingMap.get(n.id);
      if (existing) {
        return {
          ...n,
          x: existing.x,
          y: existing.y,
          vx: existing.vx || 0,
          vy: existing.vy || 0,
          fx: null,
          fy: null,
        };
      }

      // Initial placement in a circle with jitter
      const isUser = (n.type || "").toLowerCase() === "user" || n.id === "User";
      if (isUser) {
        return { ...n, x: CX, y: CY, vx: 0, vy: 0, fx: null, fy: null };
      }

      const angle = (i / Math.max(1, count)) * 2 * Math.PI;
      const radius = 120 + ((i % 3) * 45);
      return {
        ...n,
        x: CX + Math.cos(angle) * radius + (Math.random() - 0.5) * 20,
        y: CY + Math.sin(angle) * radius + (Math.random() - 0.5) * 20,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        fx: null,
        fy: null,
      };
    });

    simNodesRef.current = newSimNodes;
    setSimNodes(newSimNodes);

    // Heat up simulation
    alphaRef.current = 1.0;
  }, [rawNodes, edges]);

  // 3. Force-Directed Physics Engine Loop
  const runPhysicsTick = useCallback(() => {
    const nodes = simNodesRef.current;
    const currentEdges = edgesRef.current;
    if (!nodes || nodes.length === 0) return;

    const alpha = alphaRef.current;
    if (alpha <= 0.003 && !draggingNodeRef.current) {
      // Simulation has settled
      return;
    }

    const nodeCount = nodes.length;
    const nodeMap = new Map();
    for (let i = 0; i < nodeCount; i++) {
      nodeMap.set(nodes[i].id, nodes[i]);
    }

    // A. Center Gravity
    const gravity = 0.04 * alpha;
    for (let i = 0; i < nodeCount; i++) {
      const n = nodes[i];
      if (n.fx != null) continue;
      n.vx += (CX - n.x) * gravity;
      n.vy += (CY - n.y) * gravity;
    }

    // B. Coulomb Repulsion between all node pairs
    const repulsionStrength = 2200 * alpha;
    for (let i = 0; i < nodeCount; i++) {
      const n1 = nodes[i];
      for (let j = i + 1; j < nodeCount; j++) {
        const n2 = nodes[j];
        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let distSq = dx * dx + dy * dy;
        if (distSq < 1) {
          dx = (Math.random() - 0.5) * 2;
          dy = (Math.random() - 0.5) * 2;
          distSq = 4;
        }
        const dist = Math.sqrt(distSq);
        if (dist > 350) continue; // Repulsion cutoff

        const force = repulsionStrength / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (n1.fx == null) { n1.vx += fx; n1.vy += fy; }
        if (n2.fx == null) { n2.vx -= fx; n2.vy -= fy; }
      }
    }

    // C. Spring Attraction along Edges
    const springLength = 110;
    const springStrength = 0.05 * alpha;
    for (let i = 0; i < currentEdges.length; i++) {
      const e = currentEdges[i];
      const src = nodeMap.get(e.source);
      const tgt = nodeMap.get(e.target);
      if (!src || !tgt) continue;

      let dx = tgt.x - src.x;
      let dy = tgt.y - src.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;

      const displacement = dist - springLength;
      const force = displacement * springStrength;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (src.fx == null) { src.vx += fx; src.vy += fy; }
      if (tgt.fx == null) { tgt.vx -= fx; tgt.vy -= fy; }
    }

    // D. Velocity Integration & Damping
    const friction = 0.84;
    for (let i = 0; i < nodeCount; i++) {
      const n = nodes[i];
      if (n.fx != null) {
        n.x = n.fx;
        n.y = n.fy;
        n.vx = 0;
        n.vy = 0;
      } else {
        n.vx *= friction;
        n.vy *= friction;

        // Limit maximum speed
        const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
        const maxSpeed = 12;
        if (speed > maxSpeed) {
          n.vx = (n.vx / speed) * maxSpeed;
          n.vy = (n.vy / speed) * maxSpeed;
        }

        n.x += n.vx;
        n.y += n.vy;

        // Soft boundaries around canvas
        const pad = 35;
        if (n.x < pad) { n.x = pad; n.vx = Math.abs(n.vx) * 0.5; }
        if (n.x > WIDTH - pad) { n.x = WIDTH - pad; n.vx = -Math.abs(n.vx) * 0.5; }
        if (n.y < pad) { n.y = pad; n.vy = Math.abs(n.vy) * 0.5; }
        if (n.y > HEIGHT - pad) { n.y = HEIGHT - pad; n.vy = -Math.abs(n.vy) * 0.5; }
      }
    }

    // Decay alpha
    if (!draggingNodeRef.current) {
      alphaRef.current *= 0.985;
    }

    setSimNodes([...nodes]);
  }, []);

  // Run animation frame loop
  useEffect(() => {
    let active = true;
    const loop = () => {
      if (!active) return;
      runPhysicsTick();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => {
      active = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [runPhysicsTick]);

  const reheatPhysics = () => {
    alphaRef.current = 0.8;
  };

  // 4. Mouse Handlers for Dragging & Panning
  const getSvgCoordinates = (e) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const clientX = e.clientX;
    const clientY = e.clientY;
    // Map to SVG coordinate space factoring in zoom and pan
    const svgX = ((clientX - rect.left) / rect.width) * WIDTH;
    const svgY = ((clientY - rect.top) / rect.height) * HEIGHT;
    // Factor in pan and zoom transform: (svgX - pan.x) / zoom
    const transX = (svgX - pan.x) / zoom;
    const transY = (svgY - pan.y) / zoom;
    return { x: transX, y: transY, screenX: clientX, screenY: clientY };
  };

  const handleNodeMouseDown = (e, nodeId) => {
    e.stopPropagation();
    const coords = getSvgCoordinates(e);
    const node = simNodesRef.current.find((n) => n.id === nodeId);
    if (node) {
      node.fx = coords.x;
      node.fy = coords.y;
      draggingNodeRef.current = node;
      alphaRef.current = 0.4; // Reheat physics during drag
    }
  };

  const handleSvgMouseDown = (e) => {
    // If not clicking a node, start canvas panning
    if (e.target.closest(".graph-node")) return;
    isPanningRef.current = true;
    panStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      initialPanX: pan.x,
      initialPanY: pan.y,
    };
  };

  const handleSvgMouseMove = (e) => {
    // Handle Node Dragging
    if (draggingNodeRef.current) {
      const coords = getSvgCoordinates(e);
      draggingNodeRef.current.fx = coords.x;
      draggingNodeRef.current.fy = coords.y;
      alphaRef.current = Math.max(alphaRef.current, 0.3);
      return;
    }

    // Handle Canvas Panning
    if (isPanningRef.current) {
      const dx = e.clientX - panStartRef.current.x;
      const dy = e.clientY - panStartRef.current.y;
      setPan({
        x: panStartRef.current.initialPanX + dx,
        y: panStartRef.current.initialPanY + dy,
      });
    }
  };

  const handleSvgMouseUp = () => {
    if (draggingNodeRef.current) {
      // Release pinned position so physics can settle naturally
      draggingNodeRef.current.fx = null;
      draggingNodeRef.current.fy = null;
      draggingNodeRef.current = null;
      alphaRef.current = Math.max(alphaRef.current, 0.2);
    }
    isPanningRef.current = false;
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((prev) => Math.min(2.5, Math.max(0.4, Number((prev + delta).toFixed(2)))));
  };

  const resetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    reheatPhysics();
  };

  // Node position map
  const positionMap = useMemo(() => {
    const map = {};
    simNodes.forEach((n) => {
      map[n.id] = { x: n.x, y: n.y };
    });
    return map;
  }, [simNodes]);

  // Active / Selected interactions
  const activeNodeId = hoveredNodeId || selectedNodeId;
  const selectedNode = useMemo(() => simNodes.find((n) => n.id === selectedNodeId) || null, [simNodes, selectedNodeId]);

  const selectedEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return edges.filter((e) => e.source === selectedNodeId || e.target === selectedNodeId);
  }, [edges, selectedNodeId]);

  // Find memories related to selected node
  const nodeMemories = useMemo(() => {
    if (!selectedNode || !memItems || memItems.length === 0) return [];
    const term = (selectedNode.label || selectedNode.id).toLowerCase();
    return memItems.filter((m) => {
      const content = (m.content || "").toLowerCase();
      const tags = (m.tags || []).map((t) => String(t).toLowerCase());
      return content.includes(term) || tags.includes(term);
    }).slice(0, 4);
  }, [selectedNode, memItems]);

  const filteredNodes = useMemo(() => {
    return simNodes.filter((n) => {
      if (filter !== "all" && (n.type || "").toLowerCase() !== filter.toLowerCase()) return false;
      if (searchQuery) {
        return (n.label || n.id).toLowerCase().includes(searchQuery.toLowerCase());
      }
      return true;
    });
  }, [simNodes, filter, searchQuery]);

  return (
    <div className="view-panel" id="viewGraph">
      <div className="panel-head">
        <div>
          <h2>Memory Knowledge Graph</h2>
          <p className="panel-sub">
            Interactive force-directed associative network mapped from your persistent memories, facts, and conversation context.
          </p>
        </div>
        <div className="panel-actions">
          <button className="btn outline" onClick={loadGraph} disabled={loading}>
            {loading ? "Syncing…" : "↻ Sync Graph"}
          </button>
        </div>
      </div>

      <div className="graph-stats-row">
        <div className="graph-badge">
          <span className="dot on" />
          <span>{simNodes.length} Entity Nodes</span>
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
              onClick={() => {
                setFilter(f);
                reheatPhysics();
              }}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="graph-search">
          <input
            type="text"
            placeholder="Search entities…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {simNodes.length === 0 ? (
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
          {/* Force-Directed Canvas */}
          <div className="svg-canvas-container">
            {/* Interactive Canvas Controls Bar */}
            <div className="canvas-controls-overlay">
              <button className="canvas-ctrl-btn" onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))} title="Zoom In">
                +
              </button>
              <button className="canvas-ctrl-btn" onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))} title="Zoom Out">
                −
              </button>
              <button className="canvas-ctrl-btn" onClick={resetView} title="Reset View & Center">
                ⊙
              </button>
              <button className="canvas-ctrl-btn" onClick={reheatPhysics} title="Relax & Re-simulate Physics">
                ⚡
              </button>
              <span className="zoom-indicator">{Math.round(zoom * 100)}%</span>
            </div>

            <svg
              ref={svgRef}
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              className="graph-svg"
              preserveAspectRatio="xMidYMid meet"
              onMouseDown={handleSvgMouseDown}
              onMouseMove={handleSvgMouseMove}
              onMouseUp={handleSvgMouseUp}
              onMouseLeave={handleSvgMouseUp}
              onWheel={handleWheel}
              style={{ cursor: isPanningRef.current ? "grabbing" : "grab" }}
            >
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="25"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(148, 163, 184, 0.6)" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="26"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#8b5cf6" />
                </marker>
                <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Pan & Zoom Transform Layer */}
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* 1. Edges Layer */}
                <g className="edges-layer">
                  {edges.map((e, idx) => {
                    const srcPos = positionMap[e.source];
                    const tgtPos = positionMap[e.target];
                    if (!srcPos || !tgtPos) return null;

                    const isEdgeActive = activeNodeId && (e.source === activeNodeId || e.target === activeNodeId);
                    const isDimmed = activeNodeId && !isEdgeActive;
                    const dx = tgtPos.x - srcPos.x;
                    const dy = tgtPos.y - srcPos.y;
                    const mx = (srcPos.x + tgtPos.x) / 2 - dy * 0.12;
                    const my = (srcPos.y + tgtPos.y) / 2 + dx * 0.12;
                    const pathD = `M ${srcPos.x} ${srcPos.y} Q ${mx} ${my} ${tgtPos.x} ${tgtPos.y}`;

                    return (
                      <g key={idx} className={"graph-edge " + (isEdgeActive ? "active" : "") + (isDimmed ? " dimmed" : "")}>
                        <path
                          d={pathD}
                          fill="none"
                          stroke={isEdgeActive ? "#8b5cf6" : "rgba(148, 163, 184, 0.35)"}
                          strokeWidth={isEdgeActive ? 2.5 : 1.5}
                          markerEnd={isEdgeActive ? "url(#arrow-active)" : "url(#arrow)"}
                        />
                        {/* Edge Label Pill */}
                        <g transform={`translate(${mx}, ${my})`}>
                          <rect
                            x={-((e.relationship || "").length * 3.5 + 6)}
                            y={-8}
                            width={(e.relationship || "").length * 7 + 12}
                            height={16}
                            rx={4}
                            fill={isEdgeActive ? "#4f46e5" : "var(--panel)"}
                            stroke={isEdgeActive ? "#818cf8" : "var(--line)"}
                            strokeWidth={1}
                            opacity={isDimmed ? 0.3 : 0.95}
                          />
                          <text
                            textAnchor="middle"
                            dominantBaseline="central"
                            fill={isEdgeActive ? "#ffffff" : "var(--muted)"}
                            fontSize={9.5}
                            fontWeight={isEdgeActive ? "700" : "500"}
                          >
                            {e.relationship}
                          </text>
                        </g>
                      </g>
                    );
                  })}
                </g>

                {/* 2. Nodes Layer */}
                <g className="nodes-layer">
                  {simNodes.map((n) => {
                    const pos = positionMap[n.id];
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
                    const isFiltered = filter !== "all" && (n.type || "").toLowerCase() !== filter.toLowerCase();
                    const isSearchMatch = !searchQuery || (n.label || n.id).toLowerCase().includes(searchQuery.toLowerCase());

                    const nodeOpacity = isDimmed || isFiltered || !isSearchMatch ? 0.25 : 1.0;

                    return (
                      <g
                        key={n.id}
                        className={"graph-node " + (isSelected ? "selected" : "") + (isDimmed ? " dimmed" : "")}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onMouseDown={(e) => handleNodeMouseDown(e, n.id)}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedNodeId(isSelected ? null : n.id);
                        }}
                        onMouseEnter={() => setHoveredNodeId(n.id)}
                        onMouseLeave={() => setHoveredNodeId(null)}
                        style={{ cursor: "grab", opacity: nodeOpacity, transition: "opacity 0.2s ease" }}
                      >
                        {/* Glow on active */}
                        {isHighlighted && (
                          <circle r={28} fill={colorInfo.glow} className="node-glow" filter="url(#nodeGlow)" />
                        )}

                        {/* Node circle */}
                        <circle
                          r={20}
                          fill={colorInfo.bg}
                          stroke={isSelected ? "#ffffff" : colorInfo.border}
                          strokeWidth={isSelected ? 3.5 : 2}
                        />

                        {/* Central badge text */}
                        <text
                          textAnchor="middle"
                          dominantBaseline="central"
                          fill={colorInfo.text}
                          fontSize={11}
                          fontWeight="700"
                          pointerEvents="none"
                        >
                          {(n.label || n.id).slice(0, 2).toUpperCase()}
                        </text>

                        {/* Node Label underneath */}
                        <text
                          y={32}
                          textAnchor="middle"
                          className="node-svg-label"
                          fill={isHighlighted ? "var(--ink)" : "var(--muted)"}
                          fontSize={11}
                          fontWeight={isHighlighted ? "700" : "500"}
                          pointerEvents="none"
                        >
                          {n.label || n.id}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </g>
            </svg>

            {/* Interactive Node & Fact Inspector Drawer */}
            {selectedNode && (
              <div className="graph-inspector">
                <div className="inspector-head">
                  <div>
                    <span className="inspector-title">{selectedNode.label || selectedNode.id}</span>
                    <div className="inspector-type-tag">
                      <span className={"type-pill " + (selectedNode.type || "concept").toLowerCase()}>
                        {NODE_COLORS[(selectedNode.type || "").toLowerCase()]?.label || selectedNode.type || "Concept"}
                      </span>
                    </div>
                  </div>
                  <button className="inspector-close" onClick={() => setSelectedNodeId(null)} title="Close Inspector">
                    ×
                  </button>
                </div>

                <div className="inspector-actions">
                  <button
                    className="inspector-action-btn"
                    onClick={() => {
                      const pos = positionMap[selectedNode.id];
                      if (pos) {
                        setPan({ x: CX - pos.x * zoom, y: CY - pos.y * zoom });
                      }
                    }}
                  >
                    🎯 Center in View
                  </button>
                </div>

                {/* Connected Relationships */}
                <div className="inspector-sub">
                  Connected Triples ({selectedEdges.length}):
                </div>
                <div className="inspector-triples">
                  {selectedEdges.length === 0 ? (
                    <div className="inspector-empty">No direct edges linked to this node.</div>
                  ) : (
                    selectedEdges.map((e, idx) => {
                      const isOutgoing = e.source === selectedNode.id;
                      return (
                        <div key={idx} className="inspector-triple-row">
                          <span className="t-dir">{isOutgoing ? "→" : "←"}</span>
                          <span className="t-rel">{e.relationship}</span>
                          <span className="t-target">{isOutgoing ? e.target : e.source}</span>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Associated Memories */}
                <div className="inspector-sub">Associated Memories ({nodeMemories.length}):</div>
                <div className="inspector-memories">
                  {nodeMemories.length === 0 ? (
                    <div className="inspector-empty">Mapped from conversation entity analysis.</div>
                  ) : (
                    nodeMemories.map((m) => (
                      <div key={m.id} className="inspector-mem-item">
                        <div className="insp-mem-content">{m.content}</div>
                        <div className="insp-mem-footer">
                          <span className="insp-score">
                            Score: {(m.importance_score != null ? m.importance_score : 1.0).toFixed(2)}
                          </span>
                          {(m.tags || []).slice(0, 2).map((t) => (
                            <span key={t} className="insp-tag">#{t}</span>
                          ))}
                        </div>
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
                      className={
                        "node-chip " +
                        (n.type || "concept").toLowerCase() +
                        (selectedNodeId === n.id ? " active" : "")
                      }
                      onClick={() => {
                        const newId = selectedNodeId === n.id ? null : n.id;
                        setSelectedNodeId(newId);
                        if (newId) {
                          const pos = positionMap[newId];
                          if (pos) {
                            setPan({ x: CX - pos.x * zoom, y: CY - pos.y * zoom });
                          }
                        }
                      }}
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
                  <div className="empty-sub">
                    No knowledge triples extracted yet. Chat with MemOS to generate entity relationships!
                  </div>
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
