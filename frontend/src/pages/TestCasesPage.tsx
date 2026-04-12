import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { testCaseSections } from "@/data/test-cases";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Play, Eye } from "lucide-react";
import { toast } from "sonner";
import ForceGraph from "@/components/ForceGraph";
import { ingestTransaction } from "@/lib/unigraph-api";

function mapFraudTypeToGraph(fraudType: string): string {
  const map: Record<string, string> = {
    "Rapid Layering": "Rapid Layering",
    "Round-Tripping": "Round-Tripping",
    "Structuring": "Structuring",
    "Dormant Activation": "Dormant Activation",
    "Profile Mismatch": "Profile Mismatch",
    "Mule Account": "Mule Account",
  };
  return map[fraudType] || "Rapid Layering";
}

export default function TestCasesPage() {
  const navigate = useNavigate();
  const [previewCase, setPreviewCase] = useState<any>(null);
  const [runningCaseId, setRunningCaseId] = useState<string | null>(null);

  const parseAmount = (value: string): number => {
    const numeric = Number(String(value).replace(/[^0-9.]/g, ""));
    return Number.isFinite(numeric) ? numeric : 0;
  };

  const buildSimulationPayload = (testCase: any) => {
    const amount = parseAmount(testCase.amount);
    const base = {
      txnId: `SIM-${testCase.id}-${Date.now()}`,
      fromAccount: `SIM-${testCase.id}-SRC`,
      toAccount: `SIM-${testCase.id}-DST`,
      amount,
      customerId: `SIM-CUST-${testCase.id}`,
      deviceId: `SIM-DEV-${testCase.id}`,
      description: `${testCase.fraudType} simulation ${testCase.id}`,
      isDormant: false,
      deviceAccountCount: 1,
      velocity1h: 1,
      velocity24h: 2,
      channel: "IMPS",
    };

    if (testCase.fraudType === "Rapid Layering") {
      return { ...base, channel: "UPI", velocity1h: 6, velocity24h: 14, deviceAccountCount: 4 };
    }
    if (testCase.fraudType === "Round-Tripping") {
      return { ...base, channel: "IMPS", velocity1h: 5, velocity24h: 10, description: `${base.description} ROUND_TRIP` };
    }
    if (testCase.fraudType === "Structuring") {
      return { ...base, channel: "CASH", amount: Math.min(amount, 980000), velocity1h: 4, velocity24h: 12 };
    }
    if (testCase.fraudType === "Dormant Activation") {
      return { ...base, channel: "RTGS", isDormant: true, velocity1h: 3, velocity24h: 5 };
    }
    if (testCase.fraudType === "Profile Mismatch") {
      return { ...base, channel: "NEFT", velocity1h: 4, velocity24h: 8, deviceAccountCount: 2 };
    }
    if (testCase.fraudType === "Mule Account") {
      return { ...base, channel: "SWIFT", velocity1h: 5, velocity24h: 11, deviceAccountCount: 5 };
    }

    return base;
  };

  const runSimulation = async (testCase: any) => {
    setRunningCaseId(testCase.id);
    try {
      const payload = buildSimulationPayload(testCase);
      const response = await ingestTransaction(payload);
      if (response.alert_id) {
        toast.success(`${testCase.id} generated live alert ${response.alert_id}`);
        navigate(`/graph?alert=${response.alert_id}`);
      } else {
        toast.info(`${testCase.id} ingested without alert (risk ${response.risk_score})`);
        navigate("/transactions");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setRunningCaseId(null);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-foreground">Test Cases & Fraud Simulations</h1>
      <p className="text-sm text-muted-foreground">30 built-in test cases across 6 fraud typologies. Run Simulation sends a real ingest request to backend.</p>

      {testCaseSections.map((section) => (
        <div key={section.title} className="space-y-3">
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
            <span>{section.icon}</span> {section.title}
            <Badge variant="outline" className="text-xs font-normal">{section.cases.length} cases</Badge>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {section.cases.map((tc) => (
              <Card key={tc.id} className="shadow-sm">
                <CardHeader className="pb-2 pt-4 px-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-primary">{tc.id}</span>
                    <Badge className={`${tc.fraudColor} text-[10px]`}>{tc.fraudType}</Badge>
                  </div>
                  <CardTitle className="text-sm mt-1">{tc.name}</CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-2">
                  <p className="text-[11px] text-muted-foreground line-clamp-3">{tc.description}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Amount: <span className="font-bold text-foreground">{tc.amount}</span></span>
                    <span className="text-muted-foreground">{tc.accountCount} accounts</span>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <Button
                      size="sm"
                      className="flex-1 text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground"
                      onClick={() => {
                        void runSimulation(tc);
                      }}
                      disabled={runningCaseId === tc.id}
                    >
                      <Play className="mr-1 h-3 w-3" /> {runningCaseId === tc.id ? "Running..." : "Run Simulation"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 text-xs h-8"
                      onClick={() => setPreviewCase(tc)}
                    >
                      <Eye className="mr-1 h-3 w-3" /> View Expected
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}

      <Dialog open={!!previewCase} onOpenChange={() => setPreviewCase(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          {previewCase && (
            <>
              <DialogHeader>
                <DialogTitle>{previewCase.id}: {previewCase.name}</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <Badge className={previewCase.fraudColor}>{previewCase.fraudType}</Badge>
                <p className="text-sm text-muted-foreground">{previewCase.description}</p>
                <div className="text-xs space-y-1">
                  <div><strong>Amount:</strong> {previewCase.amount}</div>
                  <div><strong>Accounts:</strong> {previewCase.accountCount}</div>
                </div>
                <ForceGraph fraudType={mapFraudTypeToGraph(previewCase.fraudType)} />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
