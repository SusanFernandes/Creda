import React, { useState } from 'react';
import { Search, Loader2, Newspaper, ExternalLink, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const Research: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try { setResult(await ApiService.etResearch({ message: query })); }
    catch { setResult({ error: 'Research service unavailable.' }); }
    finally { setLoading(false); }
  };

  const TOPICS = ['Nifty 50 analysis', 'Best mutual funds 2025', 'RBI policy impact', 'Gold vs equity', 'Small cap outlook', 'IT sector performance'];

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Research Hub</h1>
          <p className="text-sm text-muted-foreground mt-1">AI-powered financial research and market analysis.</p>
        </div>

        <div className="flex gap-2">
          <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search any financial topic..."
            className="flex-1 rounded-xl" onKeyDown={e => e.key === 'Enter' && search()} />
          <Button onClick={search} disabled={loading || !query.trim()} className="rounded-xl">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
        </div>

        {!result && (
          <div className="flex flex-wrap gap-2">
            {TOPICS.map(t => (
              <Button key={t} variant="outline" size="sm" className="rounded-full text-xs" onClick={() => { setQuery(t); }}>
                <Sparkles className="w-3 h-3 mr-1" />{t}
              </Button>
            ))}
          </div>
        )}

        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Newspaper className="w-5 h-5" />Research Results</CardTitle>
            </CardHeader>
            <CardContent>
              {result.error ? (
                <p className="text-red-500">{result.error}</p>
              ) : (
                <div className="space-y-4">
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {result.narrative || result.response || (typeof result === 'string' ? result : JSON.stringify(result, null, 2))}
                  </div>
                  {result.sources && Array.isArray(result.sources) && result.sources.length > 0 && (
                    <div className="pt-4 border-t">
                      <h4 className="text-xs font-semibold text-muted-foreground mb-2">SOURCES</h4>
                      <div className="flex flex-wrap gap-2">
                        {result.sources.map((s: any, i: number) => (
                          <Badge key={i} variant="outline" className="text-xs">{typeof s === 'string' ? s : s.title || s.name || `Source ${i + 1}`}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Research;
