'use client';

import React, { useState } from 'react';
import { AlertTriangle, TrendingDown, Loader2, Activity, ShieldAlert, Baby, Home, Heart, Briefcase } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const SCENARIOS = [
  { id: 'market_crash_30', label: 'Market Crash (−30%)', icon: TrendingDown, color: 'text-red-500', desc: 'Simulate a 30% market correction' },
  { id: 'job_loss', label: 'Job Loss', icon: Briefcase, color: 'text-orange-500', desc: '6-month income disruption' },
  { id: 'medical_emergency', label: 'Medical Emergency', icon: ShieldAlert, color: 'text-yellow-500', desc: '₹10L+ medical expense' },
  { id: 'new_baby', label: 'New Baby', icon: Baby, color: 'text-pink-500', desc: 'Added family expenses & goals' },
  { id: 'home_purchase', label: 'Home Purchase', icon: Home, color: 'text-blue-500', desc: '₹50L+ home loan impact' },
  { id: 'marriage', label: 'Marriage', icon: Heart, color: 'text-purple-500', desc: '₹15–30L wedding expenses' },
];

const StressTest: React.FC = () => {
  const [selected, setSelected] = useState<string[]>(['market_crash_30']);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const toggle = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  const runTest = async () => {
    if (!selected.length) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await ApiService.stressTest({ events: selected });
      setResult(res);
    } catch { setResult({ error: 'Stress test failed. Try again.' }); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Portfolio Stress Test</h1>
          <p className="text-sm text-muted-foreground mt-1">Simulate life events and market shocks to evaluate your portfolio resilience.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SCENARIOS.map(s => (
            <Card key={s.id} className={`cursor-pointer transition-all hover:shadow-md ${selected.includes(s.id) ? 'ring-2 ring-primary' : ''}`}
              onClick={() => toggle(s.id)}>
              <CardContent className="p-5 flex items-start gap-3">
                <s.icon className={`w-6 h-6 mt-0.5 ${s.color}`} />
                <div>
                  <h3 className="font-medium text-sm">{s.label}</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">{s.desc}</p>
                </div>
                {selected.includes(s.id) && <Badge className="ml-auto">Selected</Badge>}
              </CardContent>
            </Card>
          ))}
        </div>

        <Button onClick={runTest} disabled={loading || !selected.length} className="rounded-xl">
          {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Running Simulation...</> : <><Activity className="w-4 h-4 mr-2" />Run Stress Test</>}
        </Button>

        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-yellow-500" />Stress Test Results</CardTitle>
              <CardDescription>Scenarios tested: {selected.map(s => SCENARIOS.find(sc => sc.id === s)?.label).join(', ')}</CardDescription>
            </CardHeader>
            <CardContent>
              {result.error ? (
                <p className="text-red-500">{result.error}</p>
              ) : (
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {typeof result === 'string' ? result : result.narrative || result.response || JSON.stringify(result, null, 2)}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default StressTest;
