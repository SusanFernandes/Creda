'use client';

import React, { useState } from 'react';
import { Brain, Loader2, Sparkles, UserCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const MoneyPersonality: React.FC = () => {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const analyse = async () => {
    setLoading(true);
    try { setResult(await ApiService.moneyPersonality()); }
    catch { setResult(null); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Money Personality</h1>
          <p className="text-sm text-muted-foreground mt-1">Discover your financial behaviour profile based on your spending and saving patterns.</p>
        </div>

        {!result ? (
          <Card className="text-center">
            <CardContent className="py-16 space-y-6">
              <div className="mx-auto p-4 bg-primary/10 rounded-2xl w-fit"><Brain className="w-12 h-12 text-primary" /></div>
              <div>
                <h2 className="text-xl font-semibold mb-2">What's Your Money Personality?</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Our AI analyses your income, expenses, investments, and goals to determine your unique financial behaviour type.
                </p>
              </div>
              <Button onClick={analyse} disabled={loading} size="lg" className="rounded-xl">
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Analysing...</> : <><Sparkles className="w-4 h-4 mr-2" />Discover My Personality</>}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {result.personality_type && (
              <Card>
                <CardContent className="p-8 text-center">
                  <div className="mx-auto p-3 bg-primary/10 rounded-2xl w-fit mb-4"><UserCircle className="w-10 h-10 text-primary" /></div>
                  <Badge className="text-lg px-4 py-1 mb-3">{result.personality_type}</Badge>
                  {result.description && <p className="text-sm text-muted-foreground max-w-md mx-auto">{result.description}</p>}
                </CardContent>
              </Card>
            )}

            {(result.narrative || result.response) && (
              <Card>
                <CardHeader><CardTitle>Detailed Analysis</CardTitle></CardHeader>
                <CardContent><div className="whitespace-pre-wrap text-sm leading-relaxed">{result.narrative || result.response}</div></CardContent>
              </Card>
            )}

            {result.traits && Array.isArray(result.traits) && (
              <Card>
                <CardHeader><CardTitle>Key Traits</CardTitle></CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {result.traits.map((t: string, i: number) => <Badge key={i} variant="outline">{t}</Badge>)}
                </CardContent>
              </Card>
            )}

            {!result.personality_type && !result.narrative && (
              <Card><CardContent className="py-6"><div className="whitespace-pre-wrap text-sm">{JSON.stringify(result, null, 2)}</div></CardContent></Card>
            )}

            <Button variant="outline" onClick={() => setResult(null)} className="rounded-xl">Retake Analysis</Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MoneyPersonality;
