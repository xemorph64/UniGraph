import { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap, 
  useNodesState, 
  useEdgesState, 
  addEdge,
  Connection,
  Edge,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Filter, 
  Calendar, 
  CheckCircle2, 
  ExternalLink, 
  AlertTriangle,
  Search,
  Maximize2
} from 'lucide-react';
import { cn } from "@/src/lib/utils";

interface GraphNode {
  id: string;
  label: string;
  type?: string;
  risk_score?: number;
  risk_level?: string;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
}

function convertToReactFlow(nodes: GraphNode[], edges: GraphEdge[]) {
  const nodeMap: Record<string, {x: number, y: number}> = {};
  const centerX = 400, centerY = 300;
  const spread = 200;
  
  nodes.forEach((n, i) => {
    if (!nodeMap[n.id]) {
      const angle = (i / nodes.length) * 2 * Math.PI;
      nodeMap[n.id] = {
        x: centerX + Math.cos(angle) * spread + (Math.random() - 0.5) * 100,
        y: centerY + Math.sin(angle) * spread + (Math.random() - 0.5) * 100
      };
    }
  });
  
  const rfNodes = nodes.map((n, i) => {
    const isHighRisk = (n.risk_level === "HIGH" || n.risk_level === "CRITICAL");
    const pos = nodeMap[n.id] || { x: 200 + (i % 4) * 150, y: 150 + Math.floor(i / 4) * 150 };
    return {
      id: n.id,
      type: 'default',
      data: { label: n.label || n.id },
      position: pos,
      style: {
        background: isHighRisk ? '#3a0007' : '#001b22',
        color: isHighRisk ? '#ef3b4d' : '#00d9ff',
        border: `2px solid ${isHighRisk ? '#ef3b4d' : '#00d9ff'}`,
        borderRadius: '50%',
        width: isHighRisk ? 70 : 60,
        height: isHighRisk ? 70 : 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '8px',
        fontWeight: 'bold'
      }
    };
  });
  
  const rfEdges = edges.map((e, i) => ({
    id: e.id || `e${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.type === 'HIGH_RISK',
    style: { stroke: e.type === 'HIGH_RISK' ? '#ef3b4d' : '#00d9ff', strokeWidth: e.type === 'HIGH_RISK' ? 2 : 1 },
    markerEnd: e.type === 'HIGH_RISK' ? { type: MarkerType.ArrowClosed, color: '#ef3b4d' } : undefined
  }));
  
  return { rfNodes, rfEdges };
}

export default function GraphExplorer() {
  const [selectedAccount, setSelectedAccount] = useState<string>("ACC-MULE-001");
  const [graphData, setGraphData] = useState<{nodes: GraphNode[], edges: GraphEdge[]} | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    fetch(`/api/v1/accounts/${selectedAccount}/graph?hops=2`)
      .then(res => res.json())
      .then(data => {
        if (data.nodes && data.nodes.length > 0) {
          const converted = convertToReactFlow(data.nodes, data.edges || []);
          setNodes(converted.rfNodes);
          setEdges(converted.rfEdges);
        }
      })
      .catch(console.error);
  }, [selectedAccount]);

  const onConnect = useCallback((params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const handleAccountSelect = (accountId: string) => {
    setSelectedAccount(accountId);
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden relative">
      {/* Filter Sidebar (Left) */}
      <div className="w-72 bg-surface-container-low/80 backdrop-blur-md border-r border-outline-variant/10 p-6 overflow-y-auto z-30">
        <h2 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-6 flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Graph Filters
        </h2>
        
        <div className="space-y-6">
          <section>
            <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 block">Alert Type</label>
            <div className="space-y-2">
              {["Structuring Patterns", "Cross-Border Velocity", "High-Risk Geographies"].map((type, i) => (
                <label key={type} className="flex items-center gap-3 cursor-pointer group">
                  <input defaultChecked={i < 2} className="rounded border-outline-variant bg-surface-container text-primary focus:ring-primary focus:ring-offset-surface-dim" type="checkbox"/>
                  <span className="text-sm text-on-surface group-hover:text-primary transition-colors">{type}</span>
                </label>
              ))}
            </div>
          </section>

          <section>
            <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 block">Risk Level Threshold</label>
            <input className="w-full h-1.5 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-primary" type="range"/>
            <div className="flex justify-between mt-2 text-[10px] text-on-surface-variant font-medium">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </section>

          <section>
            <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 block">Date Range</label>
            <div className="bg-surface-container p-3 rounded-xl border border-outline-variant/10 text-xs text-on-surface-variant flex justify-between items-center">
              Last 30 Days
              <Calendar className="w-4 h-4" />
            </div>
          </section>

          <section className="pt-4 border-t border-outline-variant/10">
            <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 block">Visual Layers</label>
            <div className="flex flex-col gap-2">
              <button className="text-xs py-2 px-3 rounded-lg bg-primary-container text-primary font-semibold flex items-center justify-between">
                Account Networks
                <CheckCircle2 className="w-4 h-4 fill-primary text-primary-container" />
              </button>
              {["Transaction Flows", "Mule Clusters"].map(layer => (
                <button key={layer} className="text-xs py-2 px-3 rounded-lg bg-surface-container-highest text-on-surface-variant hover:text-on-surface transition-colors flex items-center justify-between">
                  {layer}
                  <div className="w-4 h-4 rounded-full border border-outline-variant" />
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* Graph Canvas */}
      <div className="flex-1 relative bg-surface-dim overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Background color="#1d2b3c" gap={40} size={1} />
          <Controls className="bg-surface-container-high border-outline-variant/10" />
          <MiniMap 
            nodeColor={(n) => (n.id === '2' ? '#ef3b4d' : '#00d9ff')}
            maskColor="rgba(5, 20, 36, 0.7)"
            className="bg-surface-container-low border border-outline-variant/10"
          />
        </ReactFlow>

        {/* Breadcrumbs/Graph Meta Overlay */}
        <div className="absolute top-6 left-6 flex items-center gap-2 z-10">
          <div className="bg-surface-container-high/60 backdrop-blur-xl px-4 py-2 rounded-full border border-outline-variant/10 flex items-center gap-3">
            <span className="text-xs font-bold text-on-surface-variant uppercase tracking-tighter">Current Scope:</span>
            <span className="text-xs text-primary font-semibold">Tier 1 Connections</span>
            <div className="w-1.5 h-1.5 rounded-full bg-outline-variant"></div>
            <span className="text-xs text-on-surface-variant font-medium">Nodes: 1,422</span>
          </div>
        </div>
      </div>

      {/* Node Details Panel (Right) */}
      <div className="w-80 bg-surface-container-low border-l border-outline-variant/10 overflow-y-auto z-30">
        <div className="p-6">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Entity Profile</h3>
              <h2 className="text-lg font-bold text-primary tracking-tight">ACC_99283401</h2>
            </div>
            <button className="p-2 text-on-surface-variant hover:text-white transition-colors">
              <ExternalLink className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-8">
            {/* Risk Score Card */}
            <div className="bg-tertiary-container/30 border border-tertiary/20 p-5 rounded-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-tertiary/5 blur-3xl rounded-full -mr-12 -mt-12"></div>
              <div className="relative z-10">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-bold text-tertiary uppercase tracking-tighter">Fraud Risk Score</span>
                  <AlertTriangle className="text-tertiary w-5 h-5" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-black text-tertiary tracking-tighter">85</span>
                  <span className="text-sm font-medium text-tertiary/60">/ 100</span>
                </div>
                <div className="mt-4 h-1.5 w-full bg-tertiary/10 rounded-full overflow-hidden">
                  <div className="h-full bg-tertiary w-[85%]"></div>
                </div>
                <p className="mt-3 text-[10px] text-tertiary/80 font-medium">CRITICAL: High velocity in dormant account.</p>
              </div>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-1 gap-6">
              {[
                { label: "Last Activity", value: "Oct 24, 2023 - 14:22:10 UTC" },
                { label: "Account Holder", value: "Private Entity - High Wealth" },
                { label: "KYC Status", value: "Tier 3 Verified", status: "success" },
              ].map(meta => (
                <div key={meta.label} className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">{meta.label}</label>
                  <div className="flex items-center gap-2">
                    {meta.status === "success" && <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>}
                    <p className="text-sm font-medium">{meta.value}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Recent Connections */}
            <div className="space-y-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Top Linked Peers</h4>
              <div className="space-y-2">
                {[
                  { id: "ACC_11202", sub: "Secondary Layer", amount: "$1.2M", color: "bg-primary" },
                  { id: "ACC_88492", sub: "Mule Suspect", amount: "$450k", color: "bg-error" },
                ].map(peer => (
                  <div key={peer.id} className="flex items-center justify-between p-3 bg-surface-container rounded-xl hover:bg-surface-container-high transition-colors cursor-pointer group">
                    <div className="flex items-center gap-3">
                      <div className={cn("w-1 h-8 rounded-full", peer.color)}></div>
                      <div>
                        <p className={cn("text-xs font-bold transition-colors", peer.color === "bg-primary" ? "group-hover:text-primary" : "group-hover:text-error")}>{peer.id}</p>
                        <p className="text-[10px] text-on-surface-variant">{peer.sub}</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-on-surface-variant">{peer.amount}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 flex gap-2">
              <button className="flex-1 bg-surface-container-highest border border-outline-variant/10 text-xs font-bold py-3 rounded-xl hover:bg-surface-bright transition-colors">Generate STR</button>
              <button className="flex-1 bg-primary text-on-primary text-xs font-bold py-3 rounded-xl hover:opacity-90 transition-opacity">Freeze Entity</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
