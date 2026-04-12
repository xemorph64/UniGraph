import { useState, useRef, useCallback, useMemo } from "react";

const SVG_W = 980;
const SVG_H = 460;
const NODE_R = 38;

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
  suspicious: "#991B1B",
  mule: "#92400E",
  destination: "#5B21B6",
  clean: "#166534",
  device: "#475569",
};

interface GNode {
  id: string;
  label: string;
  role: string;
  type: string;
  x: number;
  y: number;
}

interface GEdge {
  from: string;
  to: string;
  amount: string;
  channel: string;
  fraud: boolean;
}

interface GraphData {
  nodes: GNode[];
  edges: GEdge[];
}

const graphData: Record<string, GraphData> = {
  "Rapid Layering": {
    nodes: [
      { id: "DEV001", label: "DEV001", role: "Device", type: "device", x: 160, y: 80 },
      { id: "ACC001", label: "ACC001", role: "Source", type: "source", x: 160, y: 230 },
      { id: "ACC002", label: "ACC002", role: "Susp.", type: "suspicious", x: 480, y: 80 },
      { id: "ACC003", label: "ACC003", role: "Susp.", type: "suspicious", x: 480, y: 190 },
      { id: "ACC004", label: "ACC004", role: "Mule", type: "mule", x: 480, y: 300 },
      { id: "ACC005", label: "ACC005", role: "Susp.", type: "suspicious", x: 480, y: 400 },
      { id: "DEST", label: "ACC009", role: "Dest", type: "destination", x: 800, y: 230 },
    ],
    edges: [
      { from: "DEV001", to: "ACC001", amount: "", channel: "ACCESS", fraud: false },
      { from: "ACC001", to: "ACC002", amount: "₹4.5L", channel: "UPI", fraud: true },
      { from: "ACC001", to: "ACC003", amount: "₹3.2L", channel: "NEFT", fraud: true },
      { from: "ACC001", to: "ACC004", amount: "₹2.8L", channel: "IMPS", fraud: true },
      { from: "ACC001", to: "ACC005", amount: "₹4.1L", channel: "UPI", fraud: true },
      { from: "ACC002", to: "DEST", amount: "₹4.2L", channel: "RTGS", fraud: true },
      { from: "ACC003", to: "DEST", amount: "₹3.0L", channel: "UPI", fraud: true },
      { from: "ACC004", to: "DEST", amount: "₹2.5L", channel: "NEFT", fraud: true },
      { from: "ACC005", to: "DEST", amount: "₹3.8L", channel: "IMPS", fraud: true },
    ],
  },
  "Round-Tripping": (() => {
    const cx = 490, cy = 230, r = 160;
    const angles = [270, 342, 54, 126, 198].map((a) => (a * Math.PI) / 180);
    const ids = ["ACC101", "ACC102", "ACC103", "ACC104", "ACC105"];
    const roles = ["Source", "Susp.", "Susp.", "Mule", "Susp."];
    const types = ["source", "suspicious", "suspicious", "mule", "suspicious"];
    return {
      nodes: ids.map((id, i) => ({
        id, label: id, role: roles[i], type: types[i],
        x: Math.round(cx + r * Math.cos(angles[i])),
        y: Math.round(cy + r * Math.sin(angles[i])),
      })),
      edges: [
        { from: "ACC101", to: "ACC102", amount: "₹15L", channel: "RTGS", fraud: true },
        { from: "ACC102", to: "ACC103", amount: "₹14L", channel: "NEFT", fraud: true },
        { from: "ACC103", to: "ACC104", amount: "₹13L", channel: "UPI", fraud: true },
        { from: "ACC104", to: "ACC105", amount: "₹12L", channel: "IMPS", fraud: true },
        { from: "ACC105", to: "ACC101", amount: "₹11L", channel: "UPI", fraud: true },
      ],
    };
  })(),
  "Structuring/Smurfing": {
    nodes: [
      { id: "SMF-01", label: "SMF-01", role: "Smurf", type: "suspicious", x: 160, y: 60 },
      { id: "SMF-02", label: "SMF-02", role: "Smurf", type: "suspicious", x: 160, y: 130 },
      { id: "SMF-03", label: "SMF-03", role: "Smurf", type: "suspicious", x: 160, y: 200 },
      { id: "SMF-04", label: "SMF-04", role: "Smurf", type: "mule", x: 160, y: 270 },
      { id: "SMF-05", label: "SMF-05", role: "Smurf", type: "mule", x: 160, y: 340 },
      { id: "SMF-06", label: "SMF-06", role: "Smurf", type: "suspicious", x: 160, y: 410 },
      { id: "HUB-01", label: "HUB-01", role: "Dest", type: "destination", x: 800, y: 230 },
    ],
    edges: [
      { from: "SMF-01", to: "HUB-01", amount: "₹9.8L", channel: "Cash", fraud: true },
      { from: "SMF-02", to: "HUB-01", amount: "₹9.5L", channel: "Cash", fraud: true },
      { from: "SMF-03", to: "HUB-01", amount: "₹9.7L", channel: "Cash", fraud: true },
      { from: "SMF-04", to: "HUB-01", amount: "₹9.4L", channel: "Cash", fraud: true },
      { from: "SMF-05", to: "HUB-01", amount: "₹9.6L", channel: "Cash", fraud: true },
      { from: "SMF-06", to: "HUB-01", amount: "₹9.3L", channel: "Cash", fraud: true },
    ],
  },
  "Dormant Activation": {
    nodes: [
      { id: "DEV-X", label: "DEV-X", role: "Device", type: "device", x: 160, y: 80 },
      { id: "MASTER", label: "MASTER", role: "Source", type: "source", x: 160, y: 230 },
      { id: "DORM-01", label: "DORM-01", role: "Dormant", type: "suspicious", x: 480, y: 130 },
      { id: "DORM-02", label: "DORM-02", role: "Dormant", type: "suspicious", x: 480, y: 230 },
      { id: "DORM-03", label: "DORM-03", role: "Dormant", type: "suspicious", x: 480, y: 330 },
      { id: "DEST", label: "DEST", role: "Dest", type: "destination", x: 800, y: 230 },
    ],
    edges: [
      { from: "DEV-X", to: "MASTER", amount: "", channel: "ACCESS", fraud: false },
      { from: "MASTER", to: "DORM-01", amount: "₹1.5Cr", channel: "RTGS", fraud: true },
      { from: "MASTER", to: "DORM-02", amount: "₹5L", channel: "NEFT", fraud: true },
      { from: "MASTER", to: "DORM-03", amount: "₹8L", channel: "NEFT", fraud: true },
      { from: "DORM-01", to: "DEST", amount: "₹1.5Cr", channel: "SWIFT", fraud: true },
      { from: "DORM-02", to: "DEST", amount: "₹4.8L", channel: "NEFT", fraud: true },
      { from: "DORM-03", to: "DEST", amount: "₹7.5L", channel: "UPI", fraud: true },
    ],
  },
  "Profile Mismatch": {
    nodes: [
      { id: "STUDENT", label: "STUDENT", role: "Susp.", type: "suspicious", x: 160, y: 230 },
      { id: "CORP-01", label: "CORP-01", role: "Source", type: "source", x: 480, y: 100 },
      { id: "DEST-01", label: "DEST-01", role: "Dest", type: "destination", x: 480, y: 230 },
      { id: "DEST-02", label: "DEST-02", role: "Dest", type: "destination", x: 640, y: 330 },
      { id: "DEST-03", label: "DEST-03", role: "Dest", type: "destination", x: 800, y: 150 },
    ],
    edges: [
      { from: "CORP-01", to: "STUDENT", amount: "₹10K×50", channel: "UPI", fraud: true },
      { from: "STUDENT", to: "DEST-01", amount: "₹5L", channel: "NEFT", fraud: true },
      { from: "STUDENT", to: "DEST-02", amount: "₹4L", channel: "UPI", fraud: true },
      { from: "STUDENT", to: "DEST-03", amount: "₹6L", channel: "IMPS", fraud: true },
    ],
  },
  "Mule Account": {
    nodes: [
      { id: "CTRL", label: "CTRL", role: "Controller", type: "source", x: 160, y: 230 },
      { id: "MULE-01", label: "MULE-01", role: "Mule", type: "mule", x: 480, y: 80 },
      { id: "MULE-02", label: "MULE-02", role: "Mule", type: "mule", x: 480, y: 190 },
      { id: "MULE-03", label: "MULE-03", role: "Mule", type: "mule", x: 480, y: 300 },
      { id: "MULE-04", label: "MULE-04", role: "Mule", type: "mule", x: 480, y: 400 },
      { id: "OVERSEAS", label: "OVERSEAS", role: "Dest", type: "destination", x: 800, y: 230 },
    ],
    edges: [
      { from: "CTRL", to: "MULE-01", amount: "₹8L", channel: "NEFT", fraud: true },
      { from: "CTRL", to: "MULE-02", amount: "₹6L", channel: "NEFT", fraud: true },
      { from: "CTRL", to: "MULE-03", amount: "₹3L", channel: "UPI", fraud: true },
      { from: "CTRL", to: "MULE-04", amount: "₹5L", channel: "IMPS", fraud: true },
      { from: "MULE-01", to: "OVERSEAS", amount: "₹7.8L", channel: "UPI", fraud: true },
      { from: "MULE-02", to: "OVERSEAS", amount: "₹5.8L", channel: "UPI", fraud: true },
      { from: "MULE-03", to: "OVERSEAS", amount: "₹2.9L", channel: "UPI", fraud: true },
      { from: "MULE-04", to: "OVERSEAS", amount: "₹4.5L", channel: "SWIFT", fraud: true },
    ],
  },
};

interface Props {
  activeFraudType: string;
  onFraudTypeChange: (ft: string) => void;
}

export default function SimpleGraph({ activeFraudType, onFraudTypeChange }: Props) {
  const [highlight, setHighlight] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: SVG_W, h: SVG_H });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, vx: 0, vy: 0 });

  const data = graphData[activeFraudType] || graphData["Rapid Layering"];
  const nodeMap = useMemo(() => {
    const m: Record<string, GNode> = {};
    data.nodes.forEach((n) => { m[n.id] = n; });
    return m;
  }, [data.nodes]);

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

  const handleChange = (ft: string) => {
    onFraudTypeChange(ft);
    setHighlight(false);
    setViewBox({ x: 0, y: 0, w: SVG_W, h: SVG_H });
  };

  // Compute bezier midpoint with offset to avoid overlap
  const getEdgePath = (edge: GEdge) => {
    const src = nodeMap[edge.from];
    const tgt = nodeMap[edge.to];
    if (!src || !tgt) return null;

    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist === 0) return null;

    // Start/end at circle edge
    const sx = src.x + (dx / dist) * NODE_R;
    const sy = src.y + (dy / dist) * NODE_R;
    const ex = tgt.x - (dx / dist) * NODE_R;
    const ey = tgt.y - (dy / dist) * NODE_R;

    // Midpoint for label placement
    const labelX = (sx + ex) / 2;
    const labelY = (sy + ey) / 2;

    return { sx, sy, ex, ey, labelX, labelY };
  };

  // Group edges by source for offset calculation
  const edgesBySource = useMemo(() => {
    const m: Record<string, number[]> = {};
    data.edges.forEach((_, i) => {
      const key = data.edges[i].from;
      if (!m[key]) m[key] = [];
      m[key].push(i);
    });
    return m;
  }, [data.edges]);

  return (
    <div className="space-y-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={activeFraudType}
          onChange={(e) => handleChange(e.target.value)}
          className="h-[34px] px-3 rounded-md border text-[13px] font-semibold bg-white text-[#374151] border-[#E2E8F0] outline-none"
          style={{ minWidth: 200 }}
        >
          {FRAUD_TYPES.map((ft) => (
            <option key={ft} value={ft}>{ft}</option>
          ))}
        </select>
        <button
          onClick={() => setHighlight(!highlight)}
          className="h-[34px] px-4 rounded-md text-[13px] font-semibold text-white border-none cursor-pointer"
          style={{ background: highlight ? "#1E40AF" : "#991B1B" }}
        >
          {highlight ? "Show All" : "Highlight Fraud Path"}
        </button>
      </div>

      {/* SVG Graph */}
      <div
        className="bg-card text-card-foreground border border-border rounded-lg overflow-hidden"
      >
        <svg
          ref={svgRef}
          width="100%"
          height={SVG_H}
          viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
          className="block cursor-grab dark:invert dark:hue-rotate-180"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <rect x={viewBox.x - 500} y={viewBox.y - 500} width={viewBox.w + 1000} height={viewBox.h + 1000} className="fill-card" />

          {/* Arrows */}
          <defs>
            <marker id="red-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <polygon points="0,0 8,4 0,8" fill="#991B1B" />
            </marker>
            <marker id="gray-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <polygon points="0,0 8,4 0,8" fill="#94A3B8" />
            </marker>
          </defs>

          {/* Edges */}
           {data.edges.map((edge, i) => {
             const path = getEdgePath(edge);
             if (!path) return null;

             const opacity = highlight ? (edge.fraud ? 1 : 0.12) : 1;
             const isMeta = edge.channel === "ACCESS" || edge.channel === "BRANCH";

             return (
               <g key={i} opacity={opacity}>
                 <line
                   x1={path.sx}
                   y1={path.sy}
                   x2={path.ex}
                   y2={path.ey}
                   stroke={edge.fraud ? "#991B1B" : "#94A3B8"}
                   strokeWidth={edge.fraud ? 2 : 1.5}
                   strokeDasharray={edge.fraud ? "none" : "5,4"}
                   markerEnd={edge.fraud ? "url(#red-arrow)" : "url(#gray-arrow)"}
                 />

                {isMeta ? (
                  <text
                    x={path.labelX}
                    y={path.labelY - 4}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={9}
                    fill="#94A3B8"
                    fontWeight={500}
                  >
                    {edge.channel}
                  </text>
                ) : edge.amount ? (
                  <g>
                    <rect
                      x={path.labelX - 26}
                      y={path.labelY - 10}
                      width={52}
                      height={18}
                      rx={9}
                      fill="white"
                      stroke={edge.fraud ? "#991B1B" : "#94A3B8"}
                      strokeWidth={1}
                    />
                    <text
                      x={path.labelX}
                      y={path.labelY + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={10}
                      fontWeight={700}
                      fill={edge.fraud ? "#991B1B" : "#475569"}
                    >
                      {edge.amount}
                    </text>
                    <text
                      x={path.labelX}
                      y={path.labelY + 16}
                      textAnchor="middle"
                      fontSize={9}
                      fill="#64748B"
                    >
                      {edge.channel}
                    </text>
                  </g>
                ) : null}
              </g>
            );
          })}

          {/* Nodes */}
          {data.nodes.map((node) => {
            const color = NODE_COLORS[node.type] || "#475569";
            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={NODE_R}
                  fill={color}
                  stroke="#FFFFFF"
                  strokeWidth={3}
                />
                <text
                  x={node.x}
                  y={node.y - 6}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={11}
                  fontWeight={700}
                  fill="#FFFFFF"
                >
                  {node.label}
                </text>
                <text
                  x={node.x}
                  y={node.y + 10}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fill="#FFFFFF"
                  opacity={0.8}
                >
                  {node.role}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 flex-wrap" style={{ fontSize: 11, color: "#64748B" }}>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="capitalize">{type}</span>
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2" style={{ borderColor: "#991B1B" }} />
          <span>Fraud Flow</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed" style={{ borderColor: "#94A3B8" }} />
          <span>Normal Link</span>
        </span>
      </div>
    </div>
  );
}
