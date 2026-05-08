import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Loader2, RefreshCw, Globe, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const MarketPulse: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    setLoading(true);
    try { setData(await ApiService.marketPulse()); }
    catch { setData(null); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex justify-between items-start border-b border-slate-200 dark:border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Market Pulse</h1>
            <p className="text-sm text-muted-foreground mt-1">Real-time market insights personalised for your portfolio.</p>
          </div>
          <Button variant="outline" onClick={fetch} disabled={loading} className="rounded-xl">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />Refresh
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
        ) : !data ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">Unable to load market data. Start the backend to get live insights.</CardContent></Card>
        ) : (
          <div className="space-y-6">
            {data.indices && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {Object.entries(data.indices as Record<string, any>).map(([name, info]: [string, any]) => {
                  const positive = (info?.change ?? 0) >= 0;
                  return (
                    <Card key={name}>
                      <CardContent className="p-5">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-muted-foreground uppercase">{name}</span>
                          {positive ? <ArrowUpRight className="w-4 h-4 text-green-500" /> : <ArrowDownRight className="w-4 h-4 text-red-500" />}
                        </div>
                        <div className="text-2xl font-bold">{typeof info?.value === 'number' ? info.value.toLocaleString('en-IN') : '—'}</div>
                        <Badge variant={positive ? 'default' : 'destructive'} className="mt-1 text-xs">
                          {positive ? '+' : ''}{info?.change_pct ?? 0}%
                        </Badge>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {data.narrative && (
              <Card>
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Globe className="w-5 h-5" />Market Analysis</CardTitle></CardHeader>
                <CardContent><div className="whitespace-pre-wrap text-sm leading-relaxed">{data.narrative || data.response}</div></CardContent>
              </Card>
            )}

            {data.portfolio_impact && (
              <Card>
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><BarChart3 className="w-5 h-5" />Impact on Your Portfolio</CardTitle></CardHeader>
                <CardContent><div className="whitespace-pre-wrap text-sm leading-relaxed">{data.portfolio_impact}</div></CardContent>
              </Card>
            )}

            {!data.indices && !data.narrative && (
              <Card><CardContent className="py-8"><div className="whitespace-pre-wrap text-sm">{typeof data === 'string' ? data : data.response || JSON.stringify(data, null, 2)}</div></CardContent></Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketPulse;
