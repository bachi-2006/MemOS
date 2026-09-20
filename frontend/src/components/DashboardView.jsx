import { useEffect, useState } from "react";
import { fetchDashboardMetrics, fetchHealth, triggerOptimization } from "../lib/api.js";

export default function DashboardView({ onToast }) {
  const [metrics, setMetrics] = useState({
    total_memories: 0,
    active_memories: 0,
    compressed_memories: 0,
    forgotten_memories: 0,
    average_importance_score: 1.0,
    average_memory_confidence: 0,
    graph_triples: 0,
  });
  const [health, setHealth] = useState({
    database: "checking",
    ollama: "checking",
    qdrant: "checking",
    neo4j: "checking",
  });
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const [mRes, healthRes] = await Promise.allSettled([
        fetchDashboardMetrics(),
        fetchHealth(),
      ]);

      if (mRes.status === "fulfilled" && mRes.value) {
        setMetrics(mRes.value);
      }
      const services = healthRes.status === "fulfilled" ? healthRes.value.services || {} : {};
      setHealth({
        database: services.database?.status === "connected" ? "connected" : "standalone",
        ollama: services.ollama?.connected ? "connected" : "offline",
        qdrant: services.qdrant?.status === "connected" ? "connected" : "in-process",
        neo4j: services.neo4j?.status === "connected" ? "connected" : "standalone",
      });
    } catch {
      // Fallbacks
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    setOptimizing(true);
    try {
      const data = await triggerOptimization();
      if (data) {
        if (onToast) {
          onToast(
            `🧹 Optimize Complete: Scanned ${data.memories_scanned}, Compressed ${data.memories_compressed}, Forgotten ${data.memories_forgotten}`
          );
        }
        fetchDashboard();
      }
    } catch (e) {
      if (onToast) onToast("Optimization notice: " + (e.message || e));
    } finally {
      setOptimizing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  return (
    <div className="view-panel" id="viewDashboard">
      <div className="panel-head">
        <div>
          <h2>System Health &amp; Memory Analytics</h2>
          <p className="panel-sub">Real-time lifecycle distribution, multi-store metrics, and cognitive maintenance</p>
        </div>
        <div className="panel-actions">
          <button className="btn outline" onClick={fetchDashboard} disabled={loading}>
            {loading ? "Refreshing…" : "↻ Refresh Metrics"}
          </button>
          <button className="btn primary" onClick={handleOptimize} disabled={optimizing}>
            {optimizing ? "Sweeping…" : "🧹 Optimize Memory Store"}
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Memories</div>
          <div className="stat-val">{metrics.total_memories ?? 0}</div>
          <div className="stat-note">Canonical multi-store records</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Memories</div>
          <div className="stat-val accent">{metrics.active_memories ?? 0}</div>
          <div className="stat-note">Available for context recall</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Importance</div>
          <div className="stat-val highlight">{typeof metrics.average_importance_score === "number" ? metrics.average_importance_score.toFixed(2) : "1.00"}</div>
          <div className="stat-note">Weighted decay score</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Memory Confidence</div>
          <div className="stat-val muted">{Number(metrics.average_memory_confidence ?? 0).toFixed(1)}%</div>
          <div className="stat-note">Average extraction confidence</div>
        </div>
      </div>

      <div className="section-head" style={{ marginTop: 24 }}>
        <h3>Subsystem Health Diagnostics</h3>
      </div>

      <div className="health-grid">
        <div className="health-card">
          <div className="h-top">
            <span className="h-name">Ollama LLM Server</span>
            <span className={"dot " + (health.ollama === "connected" ? "on" : "off")} />
          </div>
          <div className="h-status">{health.ollama === "connected" ? "● Online & Ready" : "○ Offline / Unreachable"}</div>
          <div className="h-meta">Port 11434 · Local inference engine</div>
        </div>

        <div className="health-card">
          <div className="h-top">
            <span className="h-name">Database (Postgres / SQLite)</span>
            <span className={"dot " + (health.database === "connected" || health.database === "standalone" ? "on" : "off")} />
          </div>
          <div className="h-status">
            {health.database === "connected" ? "● Connected (Postgres 15)" : "● Active (SQLite Companion)"}
          </div>
          <div className="h-meta">Canonical metadata, users, messages</div>
        </div>

        <div className="health-card">
          <div className="h-top">
            <span className="h-name">Vector Engine (Qdrant)</span>
            <span className={"dot " + (health.qdrant === "connected" || health.qdrant === "in-process" ? "on" : "off")} />
          </div>
          <div className="h-status">
            {health.qdrant === "connected" ? "● Connected (Port 6333)" : "● In-Process Local Vector Store"}
          </div>
          <div className="h-meta">768d embeddings (nomic-embed-text)</div>
        </div>

        <div className="health-card">
          <div className="h-top">
            <span className="h-name">Knowledge Graph (Neo4j)</span>
            <span className={"dot " + (health.neo4j === "connected" || health.neo4j === "standalone" ? "on" : "off")} />
          </div>
          <div className="h-status">
            {health.neo4j === "connected" ? "● Connected (Port 7687)" : "● Active (In-Memory Traversal)"}
          </div>
          <div className="h-meta">Cypher entity-relationship triples</div>
        </div>
      </div>
    </div>
  );
}
