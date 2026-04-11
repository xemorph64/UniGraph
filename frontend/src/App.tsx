import React, { useEffect, useMemo, useRef, useState } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { alertsApi, reportsApi } from './services/api'

cytoscape.use(dagre)

interface FraudAlert {
  id: string
  transaction_id: string
  risk_score: number
  account_id: string
  status: string
  shap_top3: string[]
  rule_flags: string[]
  created_at: string
  risk_level: string
  recommendation: string
}

interface GraphData {
  nodes: { data: { id: string; label: string; risk: number; type: string } }[]
  edges: { data: { source: string; target: string; label: string } }[]
}

interface InvestigationPayload {
  alert: FraudAlert
  transaction?: { [k: string]: any }
  graph: {
    nodes: Array<{ [k: string]: any }>
    edges: Array<{ [k: string]: any }>
  }
  investigation_note: string
}

export default function App() {
  const [view, setView] = useState<'stream' | 'investigation'>('stream')
  const [alerts, setAlerts] = useState<FraudAlert[]>([])
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] })
  const [selectedAlert, setSelectedAlert] = useState<FraudAlert | null>(null)
  const [investigationNote, setInvestigationNote] = useState<string>('')
  const [investigationLoading, setInvestigationLoading] = useState(false)
  const [streamState, setStreamState] = useState<'connecting' | 'live' | 'offline'>('connecting')
  const [lastEventAt, setLastEventAt] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [strGenerating, setStrGenerating] = useState<string | null>(null)
  const [generatedStr, setGeneratedStr] = useState<string>('')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)

  useEffect(() => {
    fetchAlerts()
    connectWebSocket()

    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const fetchAlerts = async () => {
    try {
      const response = await alertsApi.list({ min_risk_score: 60, page_size: 200 })
      const items = (response.data.items || []) as FraudAlert[]
      setAlerts(sortAlerts(items))
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    }
  }

  const connectWebSocket = () => {
    const apiBase =
      (typeof window !== 'undefined' && (window as any).__UNIGRAPH_API_URL__) ||
      'http://localhost:8000/api/v1'
    const wsBase = apiBase.replace(/^http/, 'ws')
    const investigatorId = `ui-${Date.now()}`
    const socket = new WebSocket(`${wsBase}/ws/alerts/${investigatorId}`)

    wsRef.current = socket
    setStreamState('connecting')

    socket.onopen = () => {
      setStreamState('live')
    }

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload?.type !== 'ALERT_FIRED' || !payload.alert) {
          return
        }
        const nextAlert = payload.alert as FraudAlert
        if (nextAlert.risk_score < 60) {
          return
        }
        setLastEventAt(new Date().toISOString())
        setAlerts((prev) => sortAlerts(upsertAlert(prev, nextAlert)))
      } catch (err) {
        console.error('Failed to parse ws alert:', err)
      }
    }

    socket.onclose = () => {
      setStreamState('offline')
      reconnectTimerRef.current = window.setTimeout(() => {
        connectWebSocket()
      }, 2500)
    }

    socket.onerror = () => {
      setStreamState('offline')
    }
  }

  const investigateAlert = async (alert: FraudAlert) => {
    setInvestigationLoading(true)
    setLoading(true)
    setGeneratedStr('')
    try {
      const response = await alertsApi.investigate(alert.id, 2)
      const payload = response.data as InvestigationPayload
      const nodes = (payload.graph?.nodes || []).map((n: any) => ({
        data: {
          id: n.id || n.account_id || n.transaction_id,
          label: n.id || n.account_id || n.transaction_id,
          risk: Number(n.risk_score || 0),
          type: Array.isArray(n.labels) && n.labels.length ? n.labels[0] : 'Node',
        },
      }))
      const edges = (payload.graph?.edges || []).map((e: any) => ({
        data: {
          source: e.source,
          target: e.target,
          label: e.amount ? `INR ${Number(e.amount).toLocaleString()}` : e.type || 'FLOW',
        },
      }))

      setSelectedAlert(payload.alert || alert)
      setInvestigationNote(payload.investigation_note || 'No investigation note generated.')
      setGraphData({ nodes, edges })
      setView('investigation')
    } catch (error) {
      console.error('Failed to investigate alert:', error)
    }
    setLoading(false)
    setInvestigationLoading(false)
  }

  const generateSTR = async (alertId: string) => {
    setStrGenerating(alertId)
    try {
      const response = await reportsApi.generateSTR(alertId)
      setGeneratedStr(response.data.narrative)
    } catch (error) {
      console.error('Failed to generate STR:', error)
    }
    setStrGenerating(null)
  }

  const stats = useMemo(() => ({
    liveFraud: alerts.length,
    critical: alerts.filter(a => a.risk_score >= 90).length,
    mediumHigh: alerts.filter(a => a.risk_score >= 60 && a.risk_score < 90).length,
    open: alerts.filter(a => a.status === 'OPEN').length,
  }), [alerts])

  const graphElements = useMemo(
    () => [...graphData.nodes, ...graphData.edges],
    [graphData],
  )

  const renderStream = () => (
    <div>
      <div className="stream-header">
        <h2 className="section-title">Live Fraud Transaction Stream</h2>
        <span className={`stream-pill ${streamState}`}>{streamState === 'live' ? 'LIVE' : streamState.toUpperCase()}</span>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Fraud Transactions</h3>
          <div className="value critical">{stats.liveFraud}</div>
        </div>
        <div className="stat-card">
          <h3>Critical</h3>
          <div className="value critical">{stats.critical}</div>
        </div>
        <div className="stat-card">
          <h3>Medium + High</h3>
          <div className="value medium">{stats.mediumHigh}</div>
        </div>
        <div className="stat-card">
          <h3>Open Alerts</h3>
          <div className="value high">{stats.open}</div>
        </div>
      </div>

      <div className="pipeline-strip">
        {'Debezium -> Kafka -> Flink -> Neo4j -> ML -> LLM -> UI'}
      </div>

      <div className="stream-meta">
        {lastEventAt ? `Last event: ${new Date(lastEventAt).toLocaleString()}` : 'Waiting for live fraud events...'}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Txn ID</th>
              <th>Risk Score</th>
              <th>Account</th>
              <th>Rule Flags</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(alert => (
              <tr key={alert.id}>
                <td>{alert.id}</td>
                <td>{alert.transaction_id || '-'}</td>
                <td>
                  <span className={`badge ${alert.risk_score >= 90 ? 'critical' : alert.risk_score >= 80 ? 'high' : 'medium'}`}>
                    {alert.risk_score}
                  </span>
                </td>
                <td>{alert.account_id}</td>
                <td>{alert.rule_flags?.join(', ') || '-'}</td>
                <td>
                  <span className={`badge ${alert.status.toLowerCase()}`}>{alert.status}</span>
                </td>
                <td>
                  <button className="btn btn-primary" onClick={() => investigateAlert(alert)} disabled={investigationLoading}>
                    {investigationLoading ? 'Loading...' : 'Investigate'}
                  </button>
                  <button className="btn btn-secondary" onClick={() => generateSTR(alert.id)} disabled={strGenerating === alert.id}>
                    {strGenerating === alert.id ? 'Generating...' : 'LLM STR'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {generatedStr && (
        <div className="investigation-panel" style={{ marginTop: '1rem' }}>
          <h3 className="section-title" style={{ marginBottom: '0.75rem' }}>Latest LLM STR Draft</h3>
          <pre className="str-output">{generatedStr}</pre>
        </div>
      )}
    </div>
  )

  const renderInvestigation = () => (
    <div>
      <h2 className="section-title">Dynamic Investigation Graph</h2>
      {!selectedAlert ? (
        <div className="investigation-panel">
          Select a fraud transaction in Live Stream and click Investigate.
        </div>
      ) : (
        <>
          <div className="investigation-panel">
            <div className="detail-grid">
              <div>
                <div className="detail-label">Alert</div>
                <div className="detail-value">{selectedAlert.id}</div>
              </div>
              <div>
                <div className="detail-label">Transaction</div>
                <div className="detail-value">{selectedAlert.transaction_id || '-'}</div>
              </div>
              <div>
                <div className="detail-label">Account</div>
                <div className="detail-value">{selectedAlert.account_id}</div>
              </div>
              <div>
                <div className="detail-label">Risk</div>
                <div className="detail-value">{selectedAlert.risk_score}</div>
              </div>
            </div>
            <div className="llm-note">
              {investigationNote || 'No LLM investigation note available.'}
            </div>
          </div>
          <div className="graph-container">
            {loading ? (
              <div className="loading">Loading graph...</div>
            ) : graphData.nodes.length > 0 ? (
              <CytoscapeComponent
                elements={graphElements}
                style={{ width: '100%', height: '100%' }}
                layout={{ name: 'dagre', rankDir: 'LR', nodeSep: 30, rankSep: 80 }}
                stylesheet={[
                  {
                    selector: 'node',
                    style: {
                      'background-color': 'mapData(risk, 0, 100, #2dd4bf, #ef4444)',
                      'label': 'data(label)',
                      'color': '#f8fafc',
                      'font-size': '11px',
                      'font-weight': 700,
                      'text-wrap': 'wrap',
                      'text-max-width': '120px',
                      'width': 42,
                      'height': 42,
                    },
                  },
                  {
                    selector: 'edge',
                    style: {
                      'width': 2,
                      'line-color': '#64748b',
                      'target-arrow-color': '#64748b',
                      'target-arrow-shape': 'triangle',
                      'curve-style': 'bezier',
                      'label': 'data(label)',
                      'font-size': '9px',
                      'color': '#cbd5e1',
                    },
                  },
                ]}
              />
            ) : (
              <div className="loading">No graph edges available for this alert.</div>
            )}
          </div>
        </>
      )}
    </div>
  )

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="logo">UniGRAPH LiveOps</div>
        <div className={`nav-item ${view === 'stream' ? 'active' : ''}`} onClick={() => setView('stream')}>
          Fraud Stream
        </div>
        <div className={`nav-item ${view === 'investigation' ? 'active' : ''}`} onClick={() => setView('investigation')}>
          Investigation Graph
        </div>
      </div>
      <div className="main-content">
        {view === 'stream' && renderStream()}
        {view === 'investigation' && renderInvestigation()}
      </div>
    </div>
  )
}

function upsertAlert(existing: FraudAlert[], incoming: FraudAlert): FraudAlert[] {
  const index = existing.findIndex((a) => a.id === incoming.id)
  if (index === -1) {
    return [incoming, ...existing]
  }
  const copy = [...existing]
  copy[index] = { ...copy[index], ...incoming }
  return copy
}

function sortAlerts(items: FraudAlert[]): FraudAlert[] {
  return [...items].sort((a, b) => {
    const at = a.created_at ? new Date(a.created_at).getTime() : 0
    const bt = b.created_at ? new Date(b.created_at).getTime() : 0
    return bt - at
  })
}