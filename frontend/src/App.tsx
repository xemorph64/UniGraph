import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import Dashboard from "@/pages/Dashboard";
import AlertsQueue from "@/pages/AlertsQueue";
import GraphExplorer from "@/pages/GraphExplorer";
import TransactionMonitor from "@/pages/TransactionMonitor";
import STRGenerator from "@/pages/STRGenerator";
import CopilotPage from "@/pages/CopilotPage";
import SettingsPage from "@/pages/SettingsPage";
import TestCasesPage from "@/pages/TestCasesPage";
import NotFound from "@/pages/NotFound";

import { ThemeProvider } from "@/components/theme-provider";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider defaultTheme="dark" storageKey="unigraph-theme">
      <TooltipProvider>
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/alerts" element={<AlertsQueue />} />
              <Route path="/graph" element={<GraphExplorer />} />
              <Route path="/transactions" element={<TransactionMonitor />} />
              <Route path="/str-generator" element={<STRGenerator />} />
              <Route path="/copilot" element={<CopilotPage />} />
              <Route path="/pipeline-status" element={<TestCasesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
