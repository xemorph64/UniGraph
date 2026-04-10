import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Dashboard from "./pages/Dashboard";
import GraphExplorer from "./pages/GraphExplorer";
import Alerts from "./pages/Alerts";
import STRReports from "./pages/STRReports";

export default function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-surface-dim text-on-surface">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen ml-64">
          <Header />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/graph-explorer" element={<GraphExplorer />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/str-reports" element={<STRReports />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}
