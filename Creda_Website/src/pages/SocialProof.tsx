import React, { useState, useEffect } from 'react';
import { Users, Loader2, TrendingUp, PiggyBank, BarChart3, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ApiService } from '@/services/api';

const SocialProof: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setData(await ApiService.socialProof()); }
      catch { setData(null); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Peer Comparison</h1>
          <p className="text-sm text-muted-foreground mt-1">See how your finances compare with people in your age and income group.</p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
        ) : !data ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">Complete onboarding to see peer comparisons.</CardContent></Card>
        ) : (
          <div className="space-y-6">
            {data.peer_group && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Users className="w-5 h-5" />Your Peer Group</CardTitle>
                  <CardDescription>{data.peer_group}</CardDescription>
                </CardHeader>
              </Card>
            )}

            {data.comparisons && Array.isArray(data.comparisons) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.comparisons.map((c: any, i: number) => (
                  <Card key={i}>
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium">{c.metric}</span>
                        <span className={`text-xs font-bold ${c.status === 'above' ? 'text-green-600' : c.status === 'below' ? 'text-red-500' : 'text-yellow-500'}`}>
                          {c.status === 'above' ? 'Above Average' : c.status === 'below' ? 'Below Average' : 'On Par'}
                        </span>
                      </div>
                      <div className="flex items-end gap-4 mb-2">
                        <div><span className="text-xs text-muted-foreground">You</span><div className="text-lg font-bold">{c.your_value}</div></div>
                        <ArrowRight className="w-4 h-4 text-muted-foreground mb-1" />
                        <div><span className="text-xs text-muted-foreground">Peers</span><div className="text-lg font-bold text-muted-foreground">{c.peer_value}</div></div>
                      </div>
                      {typeof c.percentile === 'number' && <Progress value={c.percentile} className="h-2" />}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {(data.narrative || data.response) && (
              <Card>
                <CardHeader><CardTitle>Insights</CardTitle></CardHeader>
                <CardContent><div className="whitespace-pre-wrap text-sm leading-relaxed">{data.narrative || data.response}</div></CardContent>
              </Card>
            )}

            {!data.comparisons && !data.narrative && (
              <Card><CardContent className="py-6"><div className="whitespace-pre-wrap text-sm">{typeof data === 'string' ? data : JSON.stringify(data, null, 2)}</div></CardContent></Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SocialProof;
