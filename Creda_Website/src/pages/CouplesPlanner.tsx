import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, Users, Target, TrendingUp, RefreshCw, Zap, Link2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ApiService, CouplePlannerRequest } from '@/services/api';
import { useUser } from '@clerk/clerk-react';

interface CouplesResult {
  joint_monthly_surplus?: number;
  joint_corpus?: number;
  recommended_allocation?: Record<string, number>;
  goals?: { goal: string; timeline: string; amount: number }[];
  advice?: string;
  [key: string]: any;
}

export default function CouplesPlanner() {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CouplesResult | null>(null);

  const [form, setForm] = useState({
    partner1_user_id: user?.id || '',
    partner2_user_id: '',
    combined_goal: 'Home purchase in 5 years and retirement planning',
  });

  const handleCalculate = async () => {
    if (!form.partner1_user_id || !form.partner2_user_id) {
      return;
    }
    setLoading(true);
    const req: CouplePlannerRequest = { ...form };
    const data = await ApiService.couplesPlanner(req);
    setResult(data);
    setLoading(false);
  };

  const fmtL = (n?: number) =>
    n !== undefined ? `₹${(n / 100000).toFixed(1)}L` : '—';

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
            <Heart className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">Couples Planner</h1>
            <p className="text-muted-foreground text-sm">Joint financial goals for you and your partner</p>
          </div>
          <Badge variant="outline" className="ml-auto">Beta</Badge>
        </div>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Input Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Link Accounts</CardTitle>
            <CardDescription>Enter both Creda User IDs to create a joint financial plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Your User ID</Label>
              <Input
                placeholder="Your Creda user ID"
                value={form.partner1_user_id}
                onChange={e => setForm(prev => ({ ...prev, partner1_user_id: e.target.value }))}
                className="mt-1"
              />
            </div>

            <div className="flex items-center gap-2 my-1">
              <div className="flex-1 h-px bg-border" />
              <Link2 className="w-4 h-4 text-muted-foreground" />
              <div className="flex-1 h-px bg-border" />
            </div>

            <div>
              <Label>Partner's User ID</Label>
              <Input
                placeholder="Partner's Creda user ID"
                value={form.partner2_user_id}
                onChange={e => setForm(prev => ({ ...prev, partner2_user_id: e.target.value }))}
                className="mt-1"
              />
            </div>

            <div>
              <Label>Combined Goal</Label>
              <Input
                placeholder="e.g. Home purchase in 5 years"
                value={form.combined_goal}
                onChange={e => setForm(prev => ({ ...prev, combined_goal: e.target.value }))}
                className="mt-1"
              />
            </div>

            <Button
              className="w-full mt-2"
              onClick={handleCalculate}
              disabled={loading || !form.partner1_user_id || !form.partner2_user_id}
            >
              {loading
                ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Planning...</>
                : <><Zap className="w-4 h-4 mr-2" /> Create Joint Plan</>}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <div className="space-y-4">
          {result ? (
            <>
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <Card className="border-primary/30 bg-gradient-card">
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Joint Monthly Surplus</p>
                        <p className="text-xl font-bold text-green-500">{fmtL(result.joint_monthly_surplus)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Combined Corpus</p>
                        <p className="text-xl font-bold text-gradient">{fmtL(result.joint_corpus)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Recommended Allocation */}
              {result.recommended_allocation && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-accent" /> Recommended Allocation
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(result.recommended_allocation).map(([key, pct]) => (
                        <div key={key}>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm capitalize">{key.replace(/_/g, ' ')}</span>
                            <span className="text-sm font-semibold">{(Number(pct) * 100).toFixed(0)}%</span>
                          </div>
                          <div className="w-full bg-muted h-1.5 rounded-full">
                            <div className="h-1.5 bg-primary rounded-full" style={{ width: `${Number(pct) * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Goals */}
              {result.goals && result.goals.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Target className="w-4 h-4 text-accent" /> Joint Goals
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {result.goals.map((g: any, i: number) => (
                        <li key={i} className="flex justify-between text-sm">
                          <span>{g.goal}</span>
                          <div className="text-right">
                            <p className="font-semibold">{fmtL(g.amount)}</p>
                            <p className="text-xs text-muted-foreground">{g.timeline}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Advice */}
              {result.advice && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">AI Advice</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{result.advice}</p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Link both accounts and click<br /><strong>Create Joint Plan</strong></p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
