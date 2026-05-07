'use client';

import React, { useState, useEffect } from 'react';
import { Award, Loader2, TrendingUp, Shield, PiggyBank, Target, BarChart3, Download } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const ReportCard: React.FC = () => {
  const [data, setData] = useState<{ health: any; portfolio: any; tax: any } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [health, portfolio, tax] = await Promise.all([
          ApiService.moneyHealth(),
          ApiService.portfolioSummary(),
          ApiService.taxWizard(),
        ]);
        setData({ health, portfolio, tax });
      } catch { /* offline */ }
      finally { setLoading(false); }
    })();
  }, []);

  const score = data?.health?.score ?? 0;
  const grade = score >= 80 ? 'A' : score >= 60 ? 'B' : score >= 40 ? 'C' : 'D';
  const gradeColor = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-blue-600' : score >= 40 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex justify-between items-start border-b border-slate-200 dark:border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Financial Report Card</h1>
            <p className="text-sm text-muted-foreground mt-1">Your comprehensive financial health summary.</p>
          </div>
          <Button variant="outline" className="rounded-xl" onClick={() => ApiService.exportPdf('portfolio').then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'report-card.pdf'; a.click();
          }).catch(() => {})}>
            <Download className="w-4 h-4 mr-2" />Export PDF
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="space-y-6">
            {/* Overall Grade */}
            <Card className="text-center">
              <CardContent className="py-10">
                <div className="mx-auto p-4 bg-primary/10 rounded-2xl w-fit mb-4"><Award className="w-12 h-12 text-primary" /></div>
                <div className={`text-6xl font-bold ${gradeColor}`}>{grade}</div>
                <div className="text-2xl font-semibold mt-2">{score}/100</div>
                <p className="text-sm text-muted-foreground mt-1">Overall Financial Health Score</p>
                <Progress value={score} className="max-w-xs mx-auto mt-4 h-3" />
              </CardContent>
            </Card>

            {/* Section Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2"><Shield className="w-4 h-4" />Health Dimensions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data?.health?.dimensions ? Object.entries(data.health.dimensions).map(([key, val]) => (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="font-bold">{String(val)}</span>
                      </div>
                      <Progress value={Number(val) || 0} className="h-1.5" />
                    </div>
                  )) : <p className="text-xs text-muted-foreground">Run health check first.</p>}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2"><TrendingUp className="w-4 h-4" />Portfolio</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">Invested</span><span className="font-medium">₹{(data?.portfolio?.total_invested ?? 0).toLocaleString('en-IN')}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Current Value</span><span className="font-medium">₹{(data?.portfolio?.current_value ?? 0).toLocaleString('en-IN')}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">XIRR</span><span className="font-medium">{data?.portfolio?.xirr ?? 0}%</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Funds</span><span className="font-medium">{data?.portfolio?.funds_count ?? 0}</span></div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2"><PiggyBank className="w-4 h-4" />Tax</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">Old Regime</span><span className="font-medium">₹{(data?.tax?.old_regime_tax ?? 0).toLocaleString('en-IN')}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">New Regime</span><span className="font-medium">₹{(data?.tax?.new_regime_tax ?? 0).toLocaleString('en-IN')}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Recommended</span><Badge>{data?.tax?.recommended || '—'}</Badge></div>
                </CardContent>
              </Card>
            </div>

            {/* Recommendations */}
            {data?.health?.recommendations && (
              <Card>
                <CardHeader><CardTitle className="text-lg">Top Recommendations</CardTitle></CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {(Array.isArray(data.health.recommendations) ? data.health.recommendations : []).map((r: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm"><Target className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />{r}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportCard;
