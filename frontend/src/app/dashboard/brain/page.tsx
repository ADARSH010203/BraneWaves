/* ─── ARC Platform — Brain Knowledge Graph Visualization ─────────────────── */
"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Brain, Search, Trash2, X, Sparkles, GitBranch, Zap, Loader2 } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  description: string;
  task_count: number;
  occurrence_count: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphEdge {
  id: string;
  from: string;
  to: string;
  weight: number;
  source?: GraphNode;
  target?: GraphNode;
}

const NODE_COLORS: Record<string, string> = {
  topic: "#a855f7",
  entity: "#3b82f6",
  technology: "#14b8a6",
  concept: "#f59e0b",
};

export default function BrainPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [deleting, setDeleting] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<any>(null);

  const fetchGraph = useCallback(async () => {
    try {
      const data = await api.getMemoryGraph();
      setNodes(data.nodes);
      setEdges(data.edges);
    } catch (err) {
      console.error("Failed to fetch memory graph:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // D3 Force Simulation
  useEffect(() => {
    if (nodes.length === 0 || !svgRef.current) return;

    const loadD3 = async () => {
      // @ts-ignore
      if (typeof window !== "undefined" && !(window as any).d3) {
        await new Promise<void>((resolve) => {
          const script = document.createElement("script");
          script.src = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js";
          script.onload = () => resolve();
          document.head.appendChild(script);
        });
      }

      // @ts-ignore
      const d3 = (window as any).d3;
      if (!d3) return;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();

      const rect = svgRef.current!.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;

      const getRadius = (d: GraphNode) => Math.max(8, Math.min(24, 8 + d.occurrence_count * 3));
      const getColor = (d: GraphNode) => NODE_COLORS[d.type] || NODE_COLORS.topic;

      // Clone data for D3
      const simNodes = nodes.map((n) => ({ ...n }));
      const simEdges = edges
        .map((e) => ({
          ...e,
          source: e.from,
          target: e.to,
        }))
        .filter((e) => simNodes.some((n) => n.id === e.source) && simNodes.some((n) => n.id === e.target));

      const simulation = d3
        .forceSimulation(simNodes)
        .force("link", d3.forceLink(simEdges).id((d: any) => d.id).distance(80))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius((d: any) => getRadius(d) + 10));

      simulationRef.current = simulation;

      // Zoom
      const g = svg.append("g");
      svg.call(
        d3.zoom().scaleExtent([0.3, 3]).on("zoom", (event: any) => {
          g.attr("transform", event.transform);
        })
      );

      // Edges
      const link = g
        .append("g")
        .selectAll("line")
        .data(simEdges)
        .join("line")
        .attr("stroke", "rgba(148, 163, 184, 0.15)")
        .attr("stroke-width", (d: any) => Math.max(1, d.weight));

      // Node groups
      const node = g
        .append("g")
        .selectAll("g")
        .data(simNodes)
        .join("g")
        .style("cursor", "pointer")
        .call(
          d3
            .drag()
            .on("start", (event: any, d: any) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on("drag", (event: any, d: any) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on("end", (event: any, d: any) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            })
        );

      // Node glow
      node
        .append("circle")
        .attr("r", (d: any) => getRadius(d) + 4)
        .attr("fill", (d: any) => getColor(d))
        .attr("opacity", 0.15);

      // Node circles
      node
        .append("circle")
        .attr("r", (d: any) => getRadius(d))
        .attr("fill", (d: any) => getColor(d))
        .attr("stroke", "#0f172a")
        .attr("stroke-width", 2)
        .attr("class", "node-circle");

      // Labels
      node
        .append("text")
        .text((d: any) => d.label)
        .attr("text-anchor", "middle")
        .attr("dy", (d: any) => getRadius(d) + 16)
        .attr("fill", "#94a3b8")
        .attr("font-size", "10px")
        .attr("font-family", "system-ui, sans-serif");

      // Click handler
      node.on("click", (_event: any, d: any) => {
        setSelectedNode(d);
      });

      // Tick
      simulation.on("tick", () => {
        link
          .attr("x1", (d: any) => d.source.x)
          .attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x)
          .attr("y2", (d: any) => d.target.y);

        node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
      });
    };

    loadD3();

    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, [nodes, edges]);

  // Search logic
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await api.searchMemory(searchQuery);
        setSearchResults(data.results.filter((r) => r.score > 0.4).map((r) => r.label));
      } catch {
        setSearchResults([]);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Highlight matching nodes
  useEffect(() => {
    if (!svgRef.current) return;
    // @ts-ignore
    const d3 = (window as any).d3;
    if (!d3) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-circle").attr("opacity", (d: any) => {
      if (searchResults.length === 0) return 1;
      return searchResults.some((r) => r.toLowerCase() === d.label.toLowerCase()) ? 1 : 0.2;
    });
  }, [searchResults]);

  const handleDeleteNode = async (nodeId: string) => {
    setDeleting(true);
    try {
      await api.deleteMemoryNode(nodeId);
      setSelectedNode(null);
      await fetchGraph();
    } catch (err) {
      console.error("Failed to delete node:", err);
    } finally {
      setDeleting(false);
    }
  };

  const totalTasks = new Set(nodes.flatMap((n) => Array.isArray(n.task_count) ? [] : [n.task_count])).size;

  if (loading) {
    return (
      <div className="animate-fade-in flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="h-12 w-12 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading knowledge graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in relative">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
            ARC Brain <Brain className="h-7 w-7 text-purple-400 animate-pulse" />
          </h1>
          <p className="text-slate-400">Your persistent research memory graph — grows smarter with every task.</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Memory Nodes", value: nodes.length, icon: Brain, color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20" },
          { label: "Connections", value: edges.length, icon: GitBranch, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20" },
          { label: "Tasks Analyzed", value: new Set(nodes.flatMap((n) => [] as string[])).size || nodes.length, icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
        ].map((s) => (
          <div key={s.label} className={`glass-card p-5 border ${s.border}`}>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center`}>
                <s.icon className={`h-5 w-5 ${s.color}`} />
              </div>
              <div>
                <h3 className="text-2xl font-black text-white">{s.value}</h3>
                <p className="text-xs text-slate-400">{s.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Search + Graph */}
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0">
          {/* Search Bar */}
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memory nodes..."
              className="w-full bg-slate-950 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
            />
            {searchResults.length > 0 && (
              <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-white/10 rounded-xl p-2 z-20">
                <p className="text-xs text-slate-500 px-2 mb-1">{searchResults.length} matches highlighted</p>
                {searchResults.map((r) => (
                  <div key={r} className="text-sm text-purple-300 px-2 py-1">{r}</div>
                ))}
              </div>
            )}
          </div>

          {/* Graph Canvas */}
          {nodes.length === 0 ? (
            <div className="glass-card p-16 text-center">
              <Brain className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">No memories yet</h3>
              <p className="text-slate-400 max-w-md mx-auto">
                Complete your first research task to build your research memory. The ARC Brain automatically extracts key topics and entities from your reports.
              </p>
            </div>
          ) : (
            <div className="glass-card overflow-hidden" style={{ height: 520 }}>
              <svg ref={svgRef} width="100%" height="100%" style={{ background: "transparent" }} />
            </div>
          )}

          {/* Legend */}
          {nodes.length > 0 && (
            <div className="flex gap-4 mt-3 justify-center">
              {Object.entries(NODE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-xs text-slate-400 capitalize">{type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Side Panel */}
        {selectedNode && (
          <div className="w-full lg:w-72 shrink-0">
            <div className="glass-card p-5 sticky top-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-white text-sm">Node Details</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-white transition">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: NODE_COLORS[selectedNode.type] || NODE_COLORS.topic }}
                  />
                  <span className="text-xs text-slate-400 capitalize">{selectedNode.type}</span>
                </div>
                <h4 className="text-lg font-bold text-white mb-1">{selectedNode.label}</h4>
                <p className="text-sm text-slate-400 leading-relaxed">{selectedNode.description || "No description"}</p>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Tasks used in</span>
                  <span className="text-white font-medium">{selectedNode.task_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Occurrences</span>
                  <span className="text-white font-medium">{selectedNode.occurrence_count}</span>
                </div>
              </div>

              <button
                onClick={() => handleDeleteNode(selectedNode.id)}
                disabled={deleting}
                className="flex items-center justify-center gap-2 w-full px-3 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm hover:bg-red-500/20 disabled:opacity-50 transition"
              >
                {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                {deleting ? "Deleting..." : "Delete Node"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
