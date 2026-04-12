import { useMemo } from "react";

interface LiveGraphNode {
  id?: string;
  labels?: string[];
  risk_score?: number;
  [key: string]: unknown;
}

interface LiveGraphEdge {
  id?: string;
  source?: string;
  target?: string;
  type?: string;
  amount?: number;
  channel?: string;
  [key: string]: unknown;
}

interface Props {
  nodes: LiveGraphNode[];
  edges: LiveGraphEdge[];
  focusAccountId?: string;
}

const WIDTH = 920;
const HEIGHT = 420;
const RADIUS = 150;

function fmtAmount(amount?: number): string {
  if (typeof amount !== "number" || Number.isNaN(amount)) return "";
  return `INR ${Math.round(amount).toLocaleString("en-IN")}`;
}

export default function LiveGraph({ nodes, edges, focusAccountId }: Props) {
  const normalizedNodes = useMemo(() => {
    const ids = nodes
      .map((node) => String(node.id || "").trim())
      .filter((id) => Boolean(id));

    if (!ids.length) return [];

    return ids.map((id, index) => {
      const angle = (2 * Math.PI * index) / ids.length;
      const x = WIDTH / 2 + RADIUS * Math.cos(angle);
      const y = HEIGHT / 2 + RADIUS * Math.sin(angle);
      const isFocused = focusAccountId && id === focusAccountId;
      return {
        id,
        x,
        y,
        isFocused,
      };
    });
  }, [nodes, focusAccountId]);

  const nodeById = useMemo(() => {
    const map = new Map<string, { id: string; x: number; y: number; isFocused?: boolean }>();
    normalizedNodes.forEach((node) => map.set(node.id, node));
    return map;
  }, [normalizedNodes]);

  const normalizedEdges = useMemo(() => {
    return edges
      .map((edge) => {
        const source = String(edge.source || "").trim();
        const target = String(edge.target || "").trim();
        if (!source || !target) return null;

        const sourceNode = nodeById.get(source);
        const targetNode = nodeById.get(target);
        if (!sourceNode || !targetNode) return null;

        return {
          sourceNode,
          targetNode,
          amountLabel: fmtAmount(typeof edge.amount === "number" ? edge.amount : undefined),
          channel: String(edge.channel || edge.type || ""),
        };
      })
      .filter((edge): edge is NonNullable<typeof edge> => edge !== null);
  }, [edges, nodeById]);

  if (!normalizedNodes.length) {
    return (
      <div className="bg-card border border-border rounded-[10px] p-6 text-sm text-muted-foreground">
        No live graph data is available for this alert yet.
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-[10px] p-3 overflow-x-auto">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full min-w-[680px] h-[420px]">
        <defs>
          <marker id="live-graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <polygon points="0,0 8,4 0,8" fill="#9CA3AF" />
          </marker>
        </defs>

        {normalizedEdges.map((edge, index) => {
          const midX = (edge.sourceNode.x + edge.targetNode.x) / 2;
          const midY = (edge.sourceNode.y + edge.targetNode.y) / 2;
          return (
            <g key={`${edge.sourceNode.id}-${edge.targetNode.id}-${index}`}>
              <line
                x1={edge.sourceNode.x}
                y1={edge.sourceNode.y}
                x2={edge.targetNode.x}
                y2={edge.targetNode.y}
                stroke="#9CA3AF"
                strokeWidth={1.5}
                markerEnd="url(#live-graph-arrow)"
              />
              {(edge.amountLabel || edge.channel) && (
                <text
                  x={midX}
                  y={midY - 6}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  style={{ fontSize: 10 }}
                >
                  {[edge.amountLabel, edge.channel].filter(Boolean).join(" · ")}
                </text>
              )}
            </g>
          );
        })}

        {normalizedNodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={node.isFocused ? 30 : 24}
              fill={node.isFocused ? "#2563EB" : "#334155"}
              stroke="#E2E8F0"
              strokeWidth={2}
            />
            <text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              className="fill-white"
              style={{ fontSize: 10, fontWeight: 700 }}
            >
              {node.id}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
