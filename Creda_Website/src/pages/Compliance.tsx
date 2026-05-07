import React, { useState, useEffect } from 'react';
import { ShieldCheck, Loader2, FileText, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiService } from '@/services/api';

const Compliance: React.FC = () => {
  const [disclosure, setDisclosure] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [loadingD, setLoadingD] = useState(true);
  const [loadingR, setLoadingR] = useState(false);

  useEffect(() => {
    (async () => {
      try { setDisclosure(await ApiService.aiDisclosure()); }
      catch { /* offline */ }
      finally { setLoadingD(false); }
    })();
  }, []);

  const fetchReport = async () => {
    setLoadingR(true);
    try { setReport(await ApiService.complianceReport()); }
    catch { setReport({ error: 'Failed to generate report.' }); }
    finally { setLoadingR(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">SEBI Compliance</h1>
          <p className="text-sm text-muted-foreground mt-1">AI disclosure and regulatory compliance for all financial advice.</p>
        </div>

        <Tabs defaultValue="disclosure">
          <TabsList className="rounded-xl">
            <TabsTrigger value="disclosure">AI Disclosure</TabsTrigger>
            <TabsTrigger value="report">Compliance Report</TabsTrigger>
          </TabsList>

          <TabsContent value="disclosure" className="mt-6">
            {loadingD ? (
              <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Info className="w-5 h-5 text-blue-500" />AI-Powered Advisory Disclosure</CardTitle>
                  <CardDescription>SEBI requires disclosure when AI is used in financial advisory.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {disclosure ? (
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">
                      {typeof disclosure === 'string' ? disclosure : disclosure.disclosure_text || disclosure.text || JSON.stringify(disclosure, null, 2)}
                    </div>
                  ) : (
                    <div className="space-y-3 text-sm">
                      <p><strong>CREDA uses artificial intelligence</strong> to provide financial insights and suggestions. This is not a replacement for certified financial advisors.</p>
                      <p>All advice is AI-generated using LLM models (Groq LLaMA) and mathematical calculations. No SEBI-registered advisor has reviewed individual recommendations.</p>
                      <p>Tax calculations use published Income Tax Act rules. Investment projections assume historical average returns and don't guarantee future performance.</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="report" className="mt-6 space-y-4">
            <Button onClick={fetchReport} disabled={loadingR} className="rounded-xl">
              {loadingR ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</> : <><FileText className="w-4 h-4 mr-2" />Generate Report</>}
            </Button>

            {report && (
              <Card>
                <CardHeader><CardTitle>Compliance Report</CardTitle></CardHeader>
                <CardContent>
                  {report.error ? (
                    <p className="text-red-500">{report.error}</p>
                  ) : (
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">
                      {report.report || report.response || JSON.stringify(report, null, 2)}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Compliance;
