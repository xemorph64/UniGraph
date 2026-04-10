import React, { useState, useEffect } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api, alertsApi, accountsApi, reportsApi } from './services/api'

cytoscape.use(dagre)

interface Alert {
  id: string
  risk_score: number
  account_id: string
  status: string
  shap_top3: string[]
  rule_flags: string[]
  created_at: string
  risk_level: string
  recommendation: string
}

interface Case {
  case_id: string
  title: string
  priority: string
  status: string
  created_at: string
}

interface GraphData {
  nodes: { data: { id: string; label: string; risk: number } }[]
  edges: { data: { source: string; target: string; label: string } }[]
}

export default function App() {
  const [view, setView] = useState<'dashboard' | 'alerts' | 'graph' | 'cases'>('dashboard')
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] })
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [strGenerating, setStrGenerating] = useState<string | null>(null)
  const [generatedStr, setGeneratedStr] = useState<string>('')

  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      const response = await alertsApi.list({})
      setAlerts(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    }
  }

  const fetchGraph = async (accountId: string) => {
    if (!accountId) return
    setLoading(true)
    try {
      const response = await accountsApi.subgraph(accountId, { hops: 2 })
      const nodes = (response.data.nodes || []).map((n: any) => ({
        data: { id: n.id, label: n.id, risk: n.risk_score || 0 }
      }))
      const edges = (response.data.edges || []).map((e: any) => ({
        data: { source: e.source, target: e.target, label: `₹${e.amount || 0}` }
      }))
      setGraphData({ nodes, edges })
    } catch (error) {
      console.error('Failed to fetch graph:', error)
    }
    setLoading(false)
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

  const stats = {
    open: alerts.filter(a => a.status === 'OPEN').length,
    investigating: alerts.filter(a => a.status === 'INVESTIGATING').length,
    critical: alerts.filter(a => a.risk_score >= 90).length,
    high: alerts.filter(a => a.risk_score >= 80 && a.risk_score < 90).length,
  }

  const chartData = [
    { name: 'Mon', alerts: 12 },
    { name: 'Tue', alerts: 19 },
    { name: 'Wed', alerts: 15 },
    { name: 'Thu', alerts: 8 },
    { name: 'Fri', alerts: 22 },
    { name: 'Sat', alerts: 5 },
    { name: 'Sun', alerts: 3 },
  ]

  const getRiskColor = (score: number) => {
    if (score >= 90) return '#ef4444'
    if (score >= 80) return '#f97316'
    if (score >= 60) return '#eab308'
    return '#22c55e'
  }

  const renderDashboard = () => (
    <div>
      <h2 className="section-title">Dashboard</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Open Alerts</h3>
          <div className="value">{stats.open}</div>
        </div>
        <div className="stat-card">
          <h3>Investigating</h3>
          <div className="value medium">{stats.investigating}</div>
        </div>
        <div className="stat-card">
          <h3>Critical Risk</h3>
          <div className="value critical">{stats.critical}</div>
        </div>
        <div className="stat-card">
          <h3>High Risk</h3>
          <div className="value high">{stats.high}</div>
        </div>
      </div>
      
      <div className="section-title">Alert Trend</div>
      <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '0.75rem', marginBottom: '1.5rem' }}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ background: '#334155', border: 'none' }} />
            <Bar dataKey="alerts" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="section-title">Recent Alerts</div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Risk Score</th>
              <th>Account</th>
              <th>SHAP Summary</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.slice(0, 5).map(alert => (
              <tr key={alert.id}>
                <td>{alert.id}</td>
                <td>
                  <span className={`badge ${alert.risk_score >= 90 ? 'critical' : alert.risk_score >= 80 ? 'high' : 'medium'}`}>
                    {alert.risk_score}
                  </span>
                </td>
                <td>{alert.account_id}</td>
                <td>{alert.shap_top3?.join(', ') || '-'}</td>
                <td>
                  <span className={`badge ${alert.status.toLowerCase()}`}>{alert.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderAlerts = () => (
    <div>
      <h2 className="section-title">Alert Inbox</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Risk Score</th>
              <th>Account</th>
              <th>Risk Level</th>
              <th>Rule Flags</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(alert => (
              <tr key={alert.id}>
                <td>{alert.id}</td>
                <td>
                  <span className={`badge ${alert.risk_score >= 90 ? 'critical' : alert.risk_score >= 80 ? 'high' : 'medium'}`}>
                    {alert.risk_score}
                  </span>
                </td>
                <td>{alert.account_id}</td>
                <td>{alert.risk_level}</td>
                <td>{alert.rule_flags?.join(', ') || '-'}</td>
                <td>
                  <span className={`badge ${alert.status.toLowerCase()}`}>{alert.status}</span>
                </td>
                <td>{alert.created_at ? new Date(alert.created_at).toLocaleDateString() : '-'}</td>
                <td>
                  <button className="btn btn-primary" style={{ marginRight: '0.5rem' }} onClick={() => { setSelectedAccount(alert.account_id); setView('graph'); }}>
                    View Graph
                  </button>
                  <button className="btn btn-secondary" onClick={() => generateSTR(alert.id)} disabled={strGenerating === alert.id}>
                    {strGenerating === alert.id ? 'Generating...' : 'Generate STR'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {generatedStr && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: '#1e293b', borderRadius: '0.75rem' }}>
          <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>Generated STR</h3>
          <pre style={{ color: '#94a3b8', whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{generatedStr}</pre>
        </div>
      )}
    </div>
  )

  const renderGraph = () => (
    <div>
      <h2 className="section-title">Graph Explorer</h2>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem' }}>
        <input 
          type="text" 
          placeholder="Enter account ID (e.g., ACC-LAYER-001)" 
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          style={{ padding: '0.5rem', background: '#1e293b', border: '1px solid #334155', color: '#fff', borderRadius: '0.375rem', flex: 1 }}
        />
        <button className="btn btn-primary" onClick={() => fetchGraph(selectedAccount)}>Load Graph</button>
      </div>
      <div className="graph-container">
        {loading ? (
          <div style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem' }}>Loading graph...</div>
        ) : graphData.nodes.length > 0 ? (
          <CytoscapeComponent
            elements={graphData}
            style={{ width: '100%', height: '500px' }}
            layout={{ name: 'dagre', rankDir: 'LR' }}
            stylesheet={[
              {
                selector: 'node',
                style: {
                  'background-color': '#3b82f6',
                  'label': 'data(label)',
                  'color': '#fff',
                  'font-size': '12px',
                }
              },
              {
                selector: 'edge',
                style: {
                  'width': 2,
                  'line-color': '#94a3b8',
                  'target-arrow-color': '#94a3b8',
                  'target-arrow-shape': 'triangle',
                  'label': 'data(label)',
                  'font-size': '10px',
                  'color': '#94a3b8',
                }
              }
            ]}
          />
        ) : (
          <div style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem' }}>
            Enter an account ID and click "Load Graph" to visualize the fraud network
          </div>
        )}
      </div>
    </div>
  )

  const renderCases = () => (
    <div>
      <h2 className="section-title">Cases</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Title</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {cases.map(c => (
              <tr key={c.case_id}>
                <td>{c.case_id}</td>
                <td>{c.title}</td>
                <td>
                  <span className={`badge ${c.priority.toLowerCase()}`}>{c.priority}</span>
                </td>
                <td>
                  <span className={`badge ${c.status.toLowerCase()}`}>{c.status}</span>
                </td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
                <td>
                  <button className="btn btn-primary">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="logo">UniGRAPH</div>
        <div className={`nav-item ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>
          Dashboard
        </div>
        <div className={`nav-item ${view === 'alerts' ? 'active' : ''}`} onClick={() => setView('alerts')}>
          Alerts
        </div>
        <div className={`nav-item ${view === 'graph' ? 'active' : ''}`} onClick={() => setView('graph')}>
          Graph Explorer
        </div>
        <div className={`nav-item ${view === 'cases' ? 'active' : ''}`} onClick={() => setView('cases')}>
          Cases
        </div>
      </div>
      <div className="main-content">
        {view === 'dashboard' && renderDashboard()}
        {view === 'alerts' && renderAlerts()}
        {view === 'graph' && renderGraph()}
        {view === 'cases' && renderCases()}
      </div>
    </div>
  )
}