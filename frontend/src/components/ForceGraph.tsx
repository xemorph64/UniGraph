import { useState, useRef, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { fraudGraphs } from "@/data/fraud-graphs";
import type { GraphNode, GraphLink } from "@/data/fraud-graphs";

const SVG_W = 960;
const SVG_H = 480;
const NODE_R = 36;

const FRAUD_TYPES = [
  "Rapid Layering",
  "Round-Tripping",
  "Structuring/Smurfing",
  "Dormant Activation",
  "Profile Mismatch",
  "Mule Account",
];

const NODE_COLORS: Record<string, string> = {
  source: "#1E40AF",
  suspicious: "#B91C1C",
  mule: "#B45309",
  destination: "#6D28D9",
  clean: "#166534",
  device: "#475569",
  branch: "#475569",
};

const ROLE_LABELS: Record<string, string> = {
  source: "Source",
  suspicious: "Suspicious",
  mule: "Mule",
  destination: "Dest",
  clean: "Clean",
  device: "Device",
  branch: "Branch",
};

/** Assign x,y positions based on fraud type and node roles */
function layoutNodes(fraudType: string, nodes: GraphNode[]): Array<GraphNode & { lx: number; ly: number }> {
  const result = nodes.map((n) => ({ ...n, lx: 0, ly: 0 }));

  if (fraudType === "Round-Tripping") {
    // Identify cycle nodes (companies) vs auxiliary
    const cycleTypes = new Set(["source", "suspicious", "mule"]);
    const cycleNodes = result.filter((n) => cycleTypes.has(n.type) && n.type !== "device" && n.type !== "branch");
    const auxNodes = result.filter((n) => n.type === "device" || n.type === "branch");
    const otherNodes = result.filter((n) => !cycleNodes.includes(n) && !auxNodes.includes(n));

    const cx = SVG_W / 2;
    const cy = SVG_H / 2;
    const r = 160;
    const allCircle = [...cycleNodes, ...otherNodes];
    allCircle.forEach((n, i) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / allCircle.length;
      n.lx = cx + r * Math.cos(angle);
      n.ly = cy + r * Math.sin(angle);
    });
    // Place aux nodes outside
    auxNodes.forEach((n, i) => {
      n.lx = 80;
      n.ly = 100 + i * 80;
    });
    return result;
  }

  // Left-to-right layered layout
  // Assign columns based on type
  const columns: Record<string, number> = {
    device: 0,
    branch: 0,
    source: 1,
    suspicious: 2,
    mule: 2,
    clean: 2,
    destination: 3,
  };

  // For Structuring: smurfs left, hub right
  if (fraudType === "Structuring/Smurfing") {
    const colX = [60, 200, 500, 820];
    const groups: Record<number, typeof result> = { 0: [], 1: [], 2: [], 3: [] };
    result.forEach((n) => {
      if (n.type === "device" || n.type === "branch") groups[0].push(n);
      else if (n.type === "suspicious" || n.type === "mule") groups[1].push(n);
      else if (n.type === "source") groups[2].push(n);
      else groups[3].push(n); // destination
    });
    Object.entries(groups).forEach(([col, gnodes]) => {
      const c = Number(col);
      const spacing = SVG_H / (gnodes.length + 1);
      gnodes.forEach((n, i) => {
        n.lx = colX[c];
        n.ly = spacing * (i + 1);
      });
    });
    return result;
  }

  // Generic layered
  const colX = [80, 200, 480, 840];
  const groups: Record<number, typeof result> = { 0: [], 1: [], 2: [], 3: [] };
  result.forEach((n) => {
    const col = columns[n.type] ?? 2;
    groups[col].push(n);
  });

  Object.entries(groups).forEach(([col, gnodes]) => {
    const c = Number(col);
    if (gnodes.length === 0) return;
    if (gnodes.length === 1) {
      gnodes[0].lx = colX[c];
      gnodes[0].ly = SVG_H / 2;
    } else {
      const totalHeight = (gnodes.length - 1) * 80;
      const startY = (SVG_H - totalHeight) / 2;
      gnodes.forEach((n, i) => {
        n.lx = colX[c];
        n.ly = startY + i * 80;
      });
    }
  });

  return result;
}

interface Props {
  fraudType?: string;
  onFraudTypeChange?: (ft: string) => void;
}

export default function ForceGraph({ fraudType = "Rapid Layering", onFraudTypeChange }: Props) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<(GraphNode & { lx: number; ly: number }) | null>(null);
  const [highlight, setHighlight] = useState(false);
  const [activeFraudType, setActiveFraudType] = useState(fraudType);

  const svgRef = useRef<SVGSVGElement>(null);
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: SVG_W, h: SVG_H });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, vx: 0, vy: 0 });

  const data = fraudGraphs[activeFraudType] || fraudGraphs["Rapid Layering"];
  const laidOut = useMemo(() => layoutNodes(activeFraudType, data.nodes), [activeFraudType, data.nodes]);
  const nodeMap = useMemo(() => {
    const m: Record<string, (typeof laidOut)[0]> = {};
    laidOut.forEach((n) => { m[n.id] = n; });
    return m;
  }, [laidOut]);

  const handleFraudTypeChange = (ft: string) => {
    setActiveFraudType(ft);
    setSelected(null);
    setHighlight(false);
    setViewBox({ x: 0, y: 0, w: SVG_W, h: SVG_H });
    onFraudTypeChange?.(ft);
  };

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;
    setViewBox((prev) => {
      const nw = Math.max(300, Math.min(SVG_W * 3, prev.w * factor));
      const nh = Math.max(150, Math.min(SVG_H * 3, prev.h * factor));
      return { x: prev.x + (prev.w - nw) * mx, y: prev.y + (prev.h - nh) * my, w: nw, h: nh };
    });
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY, vx: viewBox.x, vy: viewBox.y };
  }, [viewBox.x, viewBox.y]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const dx = ((e.clientX - panStart.current.x) / rect.width) * viewBox.w;
    const dy = ((e.clientY - panStart.current.y) / rect.height) * viewBox.h;
    setViewBox((prev) => ({ ...prev, x: panStart.current.vx - dx, y: panStart.current.vy - dy }));
  }, [viewBox.w, viewBox.h]);

  const handleMouseUp = useCallback(() => { isPanning.current = false; }, []);

  const resetView = () => {
    setSelected(null);
    setHighlight(false);
    setViewBox({ x: 0, y: 0, w: SVG_W, h: SVG_H });
  };

  // Parse edge label to get amount and channel
  const parseLabel = (link: GraphLink) => {
    const amount = typeof link.amount === "string" ? link.amount : "";
    const channel = typeof link.channel === "string" ? link.channel : "";
    return { amount, channel };
  };

  // Check if channel is ACCESS or BRANCH type
  const isMetaEdge = (channel: string) =>
    ["ACCESS", "BRANCH", "OWNED_BY"].includes(channel);

  return (
    <div className="space-y-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={activeFraudType}
          onChange={(e) => handleFraudTypeChange(e.target.value)}
          className="h-[34px] px-3 rounded-md border text-[13px] font-semibold bg-white text-[#374151] border-[#E2E8F0] outline-none"
          style={{ minWidth: 180 }}
        >
          {FRAUD_TYPES.map((ft) => (
            <option key={ft} value={ft}>{ft}</option>
          ))}
        </select>
        <button
          onClick={() => setHighlight(true)}
          className="h-[34px] px-4 rounded-md text-[13px] font-semibold text-white border-none cursor-pointer"
          style={{ background: "#B91C1C" }}
        >
          Highlight Path
        </button>
        <button
          onClick={() => setHighlight(false)}
          className="h-[34px] px-4 rounded-md text-[13px] font-semibold text-white border-none cursor-pointer"
          style={{ background: "#1E40AF" }}
        >
          Show All
        </button>
        <button
          onClick={resetView}
          className="h-[34px] px-4 rounded-md text-[13px] font-semibold border cursor-pointer"
          style={{ background: "#F1F5F9", color: "#374151", borderColor: "#E2E8F0" }}
        >
          Reset
        </button>
        <span className="text-[11px] ml-auto" style={{ color: "#94A3B8" }}>
          Scroll to zoom · Drag to pan
        </span>
      </div>

      {/* SVG */}
      <div
        className="overflow-hidden"
        style={{
          background: "white",
          border: "1px solid #E2E8F0",
          borderRadius: 8,
          boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        }}
      >
        <svg
          ref={svgRef}
          width="100%"
          height={SVG_H}
          viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
          style={{ display: "block", cursor: isPanning.current ? "grabbing" : "grab" }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* White background */}
          <rect x={viewBox.x - 500} y={viewBox.y - 500} width={viewBox.w + 1000} height={viewBox.h + 1000} fill="#FFFFFF" />

          {/* Subtle grid */}
          {Array.from({ length: Math.ceil(SVG_W / 80) + 2 }, (_, i) => (
            <line key={`gv${i}`} x1={i * 80} y1={0} x2={i * 80} y2={SVG_H} stroke="#F1F5F9" strokeWidth={0.5} />
          ))}
          {Array.from({ length: Math.ceil(SVG_H / 80) + 2 }, (_, i) => (
            <line key={`gh${i}`} x1={0} y1={i * 80} x2={SVG_W} y2={i * 80} stroke="#F1F5F9" strokeWidth={0.5} />
          ))}

          {/* Arrow marker */}
          <defs>
            <marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
              <polygon points="0,0 7,3.5 0,7" fill="#B91C1C" />
            </marker>
          </defs>

          {/* Edges */}
          {data.links.map((link, i) => {
            const srcId = typeof link.source === "string" ? link.source : link.source.id;
            const tgtId = typeof link.target === "string" ? link.target : link.target.id;
            const src = nodeMap[srcId];
            const tgt = nodeMap[tgtId];
            if (!src || !tgt) return null;

            const { amount, channel } = parseLabel(link);
            const isMeta = isMetaEdge(channel);
            const isFraud = !!link.isFraudPath;
            const opacity = highlight ? (isFraud ? 1 : 0.15) : 1;

            const mx = (src.lx + tgt.lx) / 2;
            const my = (src.ly + tgt.ly) / 2;

            // Offset to avoid overlapping labels
            const offsetY = 0;

            return (
              <g key={i} opacity={opacity}>
                <line
                  x1={src.lx}
                  y1={src.ly}
                  x2={tgt.lx}
                  y2={tgt.ly}
                  stroke={isFraud ? "#B91C1C" : "#94A3B8"}
                  strokeWidth={isFraud ? 2 : 1.5}
                  strokeDasharray={isFraud ? "none" : "6,4"}
                  markerEnd={isFraud ? "url(#arr)" : undefined}
                />

                {/* Edge labels */}
                {isMeta ? (
                  /* ACCESS / BRANCH: plain gray text */
                  <text
                    x={mx}
                    y={my - 4}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={9}
                    fill="#94A3B8"
                    fontWeight="500"
                  >
                    {channel}
                  </text>
                ) : amount ? (
                  /* Fraud/normal monetary edge: white pill */
                  <g>
                    <rect
                      x={mx - 30}
                      y={my - 12 + offsetY}
                      width={60}
                      height={20}
                      rx={10}
                      ry={10}
                      fill="white"
                      stroke={isFraud ? "#B91C1C" : "#94A3B8"}
                      strokeWidth={1.5}
                    />
                    <text
                      x={mx}
                      y={my - 1 + offsetY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={10}
                      fontWeight="700"
                      fill={isFraud ? "#B91C1C" : "#475569"}
                    >
                      {amount}
                    </text>
                    {channel && (
                      <text
                        x={mx}
                        y={my + 17 + offsetY}
                        textAnchor="middle"
                        fontSize={9}
                        fill="#64748B"
                      >
                        {channel}
                      </text>
                    )}
                  </g>
                ) : null}
              </g>
            );
          })}

          {/* Nodes */}
          {laidOut.map((node) => {
            const color = NODE_COLORS[node.type] || "#475569";
            const isSelected = selected?.id === node.id;
            const roleLabel = ROLE_LABELS[node.type] || node.type;
            // Shorten the display ID
            const displayId = node.id.length > 8 ? node.id.slice(0, 8) : node.id;

            return (
              <g
                key={node.id}
                style={{ cursor: "pointer" }}
                onClick={(e) => { e.stopPropagation(); setSelected(node); }}
              >
                <circle
                  cx={node.lx}
                  cy={node.ly}
                  r={NODE_R}
                  fill={color}
                  stroke={isSelected ? "#FCD34D" : "#FFFFFF"}
                  strokeWidth={3}
                />
                <text
                  x={node.lx}
                  y={node.ly - 5}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={11}
                  fontWeight="700"
                  fill="#FFFFFF"
                >
                  {displayId}
                </text>
                <text
                  x={node.lx}
                  y={node.ly + 9}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fill="#FFFFFF"
                  opacity={0.85}
                >
                  {roleLabel}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 flex-wrap" style={{ fontSize: 11, color: "#64748B" }}>
        {Object.entries(NODE_COLORS)
          .filter(([type]) => type !== "branch")
          .map(([type, color]) => (
            <span key={type} className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-full" style={{ background: color }} />
              <span className="capitalize">{type}</span>
            </span>
          ))}
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2" style={{ borderColor: "#B91C1C" }} />
          <span>Fraud Flow</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed" style={{ borderColor: "#94A3B8" }} />
          <span>Normal Link</span>
        </span>
      </div>

      {/* Selected Node Info Bar */}
      {selected && (
        <div
          className="flex items-center gap-0 flex-wrap"
          style={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            padding: "12px 16px",
          }}
        >
          <span className="font-bold text-sm" style={{ color: "#1E293B" }}>{selected.id}</span>
          <span className="mx-3 h-5 w-px" style={{ background: "#E2E8F0" }} />
          <span className="text-xs" style={{ color: "#64748B" }}>
            Type: <span className="font-semibold capitalize" style={{ color: NODE_COLORS[selected.type] }}>{selected.type}</span>
          </span>
          <span className="mx-3 h-5 w-px" style={{ background: "#E2E8F0" }} />
          <span className="text-xs" style={{ color: "#64748B" }}>
            KYC: <span className="font-semibold" style={{ color: "#1E293B" }}>{selected.kycStatus || "Verified"}</span>
          </span>
          <span className="mx-3 h-5 w-px" style={{ background: "#E2E8F0" }} />
          <span className="text-xs" style={{ color: "#64748B" }}>
            Risk: <span className="font-bold" style={{ color: (selected.riskScore || 0) >= 80 ? "#B91C1C" : "#1E293B" }}>{selected.riskScore ?? "N/A"}</span>
          </span>
          <span className="mx-3 h-5 w-px" style={{ background: "#E2E8F0" }} />
          <button
            onClick={() => { navigate("/str-generator"); toast.success(`${selected.id} added to STR evidence`); }}
            className="h-7 px-3 rounded text-xs font-semibold text-white border-none cursor-pointer"
            style={{ background: "#B91C1C" }}
          >
            Add to STR
          </button>
          <button
            onClick={() => navigate("/transactions")}
            className="h-7 px-3 rounded text-xs font-semibold text-white border-none cursor-pointer ml-2"
            style={{ background: "#1E40AF" }}
          >
            View Txns
          </button>
          <button
            onClick={() => setSelected(null)}
            className="h-7 px-3 rounded text-xs font-semibold border cursor-pointer ml-2"
            style={{ background: "#F1F5F9", color: "#374151", borderColor: "#E2E8F0" }}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
