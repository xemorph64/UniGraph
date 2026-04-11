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
  Maximize2,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { cn } from "@/src/lib/utils";

interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  risk_score?: number;
  risk_level?: string;
  account_type?: string;
  kyc_tier?: number;
  is_dormant?: boolean;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
  amount?: number;
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
    const risk = n.risk_score || 0;
    const isHighRisk = risk > 70;
    const isMediumRisk = risk > 40;
    const pos = nodeMap[n.id] || { x: 200 + (i % 4) * 150, y: 150 + Math.floor(i / 4) * 150 };
    const nodeId = n.id || n.label;
    
    return {
      id: nodeId,
      type: 'default',
      data: { label: nodeId },
      position: pos,
      style: {
        background: isHighRisk ? '#3a0007' : isMediumRisk ? '#1a2200' : '#001b22',
        color: isHighRisk ? '#ef3b4d' : isMediumRisk ? '#a3e635' : '#00d9ff',
        border: `2px solid ${isHighRisk ? '#ef3b4d' : isMediumRisk ? '#a3e635' : '#00d9ff'}`,
        borderRadius: '50%',
        width: isHighRisk ? 75 : 60,
        height: isHighRisk ? 75 : 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '7px',
        fontWeight: 'bold'
      }
    };
  });
  
  const rfEdges = edges.map((e, i) => {
    const isHighRisk = e.type === 'HIGH_RISK' || (e.amount && e.amount > 500000);
    return {
      id: e.id || `e${i}`,
      source: e.source,
      target: e.target,
      label: e.label || (e.amount ? `₹${(e.amount / 100000).toFixed(1)}L` : undefined),
      animated: isHighRisk,
      style: { stroke: isHighRisk ? '#ef3b4d' : '#00d9ff', strokeWidth: isHighRisk ? 2 : 1 },
      markerEnd: isHighRisk ? { type: MarkerType.ArrowClosed, color: '#ef3b4d' } : { type: MarkerType.ArrowClosed, color: '#00d9ff' }
    };
  });
  
  return { rfNodes, rfEdges };
}

export default function GraphExplorer() {
  const [selectedAccount, setSelectedAccount] = useState<string>("ACC-LAYER-001");
  const [hops, setHops] = useState<number>(2);
  const [graphData, setGraphData] = useState<{nodes: GraphNode[], edges: GraphEdge[]} | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fraudAccounts, setFraudAccounts] = useState<string[]>([]);
  const [accountProfile, setAccountProfile] = useState<any>(null);

  useEffect(() => {
    fetch("/health")
      .then(r => r.json())
      .then(data => {
        if (data.graph_stats?.accounts && data.graph_stats.accounts > 0) {
          setFraudAccounts([
            "ACC-LAYER-001",
            "ACC-DORMANT-001",
            "ACC-MULE-001"
          ]);
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedAccount) return;
    
    setLoading(true);
    setError(null);
    
    Promise.all([
      fetch(`/api/v1/accounts/${selectedAccount}/graph?hops=${hops}`).then(r => r.json()),
      fetch(`/api/v1/accounts/${selectedAccount}/profile/`).then(r => r.json()).catch(() => null)
    ])
      .then(([graphData, profile]) => {
        setGraphData(graphData);
        setAccountProfile(profile);
        if (graphData.nodes && graphData.nodes.length > 0) {
          const converted = convertToReactFlow(graphData.nodes, graphData.edges || []);
          setNodes(converted.rfNodes);
          setEdges(converted.rfEdges);
        } else {
          setError("No connected nodes found for this account");
        }
      })
      .catch(err => {
        console.error(err);
        setError("Failed to fetch graph data");
      })
      .finally(() => setLoading(false));
  }, [selectedAccount, hops]);

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
            <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 block">Select Account</label>
            <select 
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="w-full bg-surface-container p-3 rounded-xl border border-outline-variant/10 text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              <optgroup label="Fraud Scenarios">
                <option value="ACC-LAYER-001">Rapid Layering (6-hop chain)</option>
                <option value="ACC-DORMANT-001">Dormant Account Awakening</option>
                <option value="ACC-MULE-001">Mule Network</option>
              </optgroup>
            </select>
            <div className="mt-3 flex gap-2">
              <button 
                onClick={() => setHops(1)}
                className={cn("flex-1 text-xs py-2 rounded-lg border", hops === 1 ? "bg-primary/20 border-primary text-primary" : "border-outline-variant text-on-surface-variant")}
              >
                1 Hop
              </button>
              <button 
                onClick={() => setHops(2)}
                className={cn("flex-1 text-xs py-2 rounded-lg border", hops === 2 ? "bg-primary/20 border-primary text-primary" : "border-outline-variant text-on-surface-variant")}
              >
                2 Hops
              </button>
              <button 
                onClick={() => setHops(3)}
                className={cn("flex-1 text-xs py-2 rounded-lg border", hops === 3 ? "bg-primary/20 border-primary text-primary" : "border-outline-variant text-on-surface-variant")}
              >
                3 Hops
              </button>
            </div>
          </section>

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
        {loading && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-surface-dim/80">
            <div className="flex items-center gap-3 bg-surface-container p-4 rounded-xl">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <span className="text-sm font-bold text-on-surface">Loading subgraph...</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 bg-surface-container p-6 rounded-xl border border-error/30">
            <p className="text-sm font-bold text-error">{error}</p>
            <p className="text-xs text-on-surface-variant mt-2">Click "Start System" on Dashboard first</p>
          </div>
        )}
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
            <span className="text-xs font-bold text-on-surface-variant uppercase tracking-tighter">Scope:</span>
            <span className="text-xs text-primary font-semibold">{selectedAccount}</span>
            <div className="w-1.5 h-1.5 rounded-full bg-outline-variant"></div>
            <span className="text-xs text-on-surface-variant font-medium">{hops}-hop</span>
            <div className="w-1.5 h-1.5 rounded-full bg-outline-variant"></div>
            <span className="text-xs text-on-surface-variant font-medium">Nodes: {nodes.length}</span>
          </div>
        </div>
      </div>

      {/* Node Details Panel (Right) */}
      <div className="w-80 bg-surface-container-low border-l border-outline-variant/10 overflow-y-auto z-30">
        <div className="p-6">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Entity Profile</h3>
              <h2 className="text-lg font-bold text-primary tracking-tight">{selectedAccount}</h2>
            </div>
            <button className="p-2 text-on-surface-variant hover:text-white transition-colors">
              <ExternalLink className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-8">
            {/* Risk Score Card */}
            <div className={cn(
              "border p-5 rounded-2xl relative overflow-hidden",
              accountProfile?.risk_score > 70 ? "bg-tertiary-container/30 border-tertiary/20" :
              accountProfile?.risk_score > 40 ? "bg-orange-900/20 border-orange-500/20" :
              "bg-surface-container border-outline-variant/10"
            )}>
              <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 blur-3xl rounded-full -mr-12 -mt-12"></div>
              <div className="relative z-10">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-bold text-on-surface-variant uppercase tracking-tighter">Fraud Risk Score</span>
                  <AlertTriangle className={cn("w-5 h-5", accountProfile?.risk_score > 70 ? "text-tertiary" : "text-primary")} />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className={cn("text-5xl font-black tracking-tighter", 
                    accountProfile?.risk_score > 70 ? "text-tertiary" :
                    accountProfile?.risk_score > 40 ? "text-orange-400" : "text-on-surface"
                  )}>
                    {Math.round(accountProfile?.risk_score || 0)}
                  </span>
                  <span className="text-sm font-medium text-on-surface-variant">/ 100</span>
                </div>
                <div className="mt-4 h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                  <div className={cn("h-full", 
                    accountProfile?.risk_score > 70 ? "bg-tertiary" :
                    accountProfile?.risk_score > 40 ? "bg-orange-400" : "bg-primary"
                  )} style={{ width: `${accountProfile?.risk_score || 0}%` }}></div>
                </div>
                <p className="mt-3 text-[10px] text-on-surface-variant font-medium">
                  {accountProfile?.risk_score > 70 ? "HIGH RISK: Immediate action required" :
                   accountProfile?.risk_score > 40 ? "MEDIUM RISK: Monitor closely" :
                   "LOW RISK: Normal activity"}
                </p>
              </div>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-1 gap-6">
              {[
                { label: "Account Type", value: accountProfile?.account_type || "SAVINGS" },
                { label: "KYC Tier", value: `Tier ${accountProfile?.kyc_tier || 1}` },
                { label: "Dormant", value: accountProfile?.is_dormant ? "Yes" : "No", status: accountProfile?.is_dormant ? "warning" : "success" },
                { label: "Community ID", value: accountProfile?.community_id || "N/A" },
                { label: "PageRank", value: accountProfile?.pagerank ? accountProfile.pagerank.toFixed(3) : "N/A" },
              ].map(meta => (
                <div key={meta.label} className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">{meta.label}</label>
                  <div className="flex items-center gap-2">
                    {meta.status === "success" && <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>}
                    {meta.status === "warning" && <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>}
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
