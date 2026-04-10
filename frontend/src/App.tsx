import { useState } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from './services/api'
import { useAuthStore } from './store/authStore'

cytoscape.use(dagre)

interface Alert {
  alert_id: string
  risk_score: number
  account_id: string
  status: string
  shap_summary: string
  created_at: string
}

interface Case {
  case_id: string
  title: string
  priority: string
  status: string
  created_at: string
}

export default function App() {
  const [view, setView] = useState<'dashboard' | 'alerts' | 'graph' | 'cases'>('dashboard')
  const { token } = useAuthStore()
  
  const [alerts, setAlerts] = useState<Alert[]>([
    { alert_id: 'ALT-2026-00123', risk_score: 87, account_id: 'UBI30100012345678', status: 'OPEN', shap_summary: 'High velocity + shared device', created_at: '2026-04-10T14:23:01Z' },
    { alert_id: 'ALT-2026-00122', risk_score: 92, account_id: 'UBI30100087654321', status: 'INVESTIGATING', shap_summary: 'Round trip pattern detected', created_at: '2026-04-10T12:45:00Z' },
    { alert_id: 'ALT-2026-00121', risk_score: 65, account_id: 'UBI30100011223344', status: 'CLOSED', shap_summary: 'False positive', created_at: '2026-04-09T18:30:00Z' },
  ])
  
  const [cases, setCases] = useState<Case[]>([
    { case_id: 'CASE-2026-00456', title: 'Rapid Layering Investigation', priority: 'HIGH', status: 'OPEN', created_at: '2026-04-10T14:30:00Z' },
    { case_id: 'CASE-2026-00455', title: 'Mule Network Detection', priority: 'CRITICAL', status: 'INVESTIGATING', created_at: '2026-04-10T11:00:00Z' },
  ])

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

  const sampleGraph = {
    nodes: [
      { data: { id: 'ACC-001', label: 'ACC-001', risk: 0 } },
      { data: { id: 'ACC-002', label: 'ACC-002', risk: 85 } },
      { data: { id: 'ACC-003', label: 'ACC-003', risk: 92 } },
      { data: { id: 'ACC-004', label: 'ACC-004', risk: 45 } },
    ],
    edges: [
      { data: { source: 'ACC-001', target: 'ACC-002', label: '₹75K' } },
      { data: { source: 'ACC-002', target: 'ACC-003', label: '₹74K' } },
      { data: { source: 'ACC-003', target: 'ACC-004', label: '₹73K' } },
    ],
  }

  const nodeStyle = {
    width: 60,
    height: 60,
    backgroundColor: '#3b82f6',
    borderWidth: 2,
    borderColor: '#fff',
    label: 'data(label)',
  }

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
              <th>Summary</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.slice(0, 5).map(alert => (
              <tr key={alert.alert_id}>
                <td>{alert.alert_id}</td>
                <td>
                  <span className={`badge ${alert.risk_score >= 90 ? 'critical' : alert.risk_score >= 80 ? 'high' : 'medium'}`}>
                    {alert.risk_score}
                  </span>
                </td>
                <td>{alert.account_id}</td>
                <td>{alert.shap_summary}</td>
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
              <th>SHAP Summary</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(alert => (
              <tr key={alert.alert_id}>
                <td>{alert.alert_id}</td>
                <td>
                  <span className={`badge ${alert.risk_score >= 90 ? 'critical' : alert.risk_score >= 80 ? 'high' : 'medium'}`}>
                    {alert.risk_score}
                  </span>
                </td>
                <td>{alert.account_id}</td>
                <td>{alert.shap_summary}</td>
                <td>
                  <span className={`badge ${alert.status.toLowerCase()}`}>{alert.status}</span>
                </td>
                <td>{new Date(alert.created_at).toLocaleDateString()}</td>
                <td>
                  <button className="btn btn-primary" style={{ marginRight: '0.5rem' }}>View</button>
                  <button className="btn btn-secondary">Investigate</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderGraph = () => (
    <div>
      <h2 className="section-title">Graph Explorer</h2>
      <div className="graph-container">
        <CytoscapeComponent
          elements={sampleGraph}
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