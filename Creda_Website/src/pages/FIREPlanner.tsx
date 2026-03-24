import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Flame, TrendingUp, Calendar, DollarSign, Target, Zap, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ApiService, FIRERequest } from '@/services/api';
import { useUser } from '@clerk/clerk-react';

interface FIREResult {
  fire_number?: number;
  years_to_fire?: number;
  monthly_required?: number;
  current_gap?: number;
  current_monthly_investment?: number;
  inflation_adjusted_fire_number?: number;
  [key: string]: any;
}

export default function FIREPlanner() {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FIREResult | null>(null);

  const [form, setForm] = useState({
    monthly_expenses: 50000,
    current_savings: 500000,
    monthly_investment: 25000,
    expected_return: 12,
    inflation_rate: 6,
  });

  const handleChange = (key: string, value: string) => {
    setForm(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const handleCalculate = async () => {
    setLoading(true);
    const req: FIRERequest = {
      user_id: user?.id || 'guest',
      ...form,
    };
    const data = await ApiService.firePlanner(req);
    setResult(data);
    setLoading(false);
  };

  const fmt = (n?: number) =>
    n !== undefined ? `₹${(n / 100000).toFixed(1)}L` : '—';

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
            <Flame className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">FIRE Planner</h1>
            <p className="text-muted-foreground text-sm">Financial Independence, Retire Early</p>
          </div>
          <Badge variant="outline" className="ml-auto">AI Powered</Badge>
        </div>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Input Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Your Financial Profile</CardTitle>
            <CardDescription>Enter your current numbers for a personalised FIRE roadmap</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { key: 'monthly_expenses',    label: 'Monthly Expenses (₹)',    placeholder: '50000' },
              { key: 'current_savings',     label: 'Current Savings / Corpus (₹)', placeholder: '500000' },
              { key: 'monthly_investment',  label: 'Monthly Investment (₹)',  placeholder: '25000' },
              { key: 'expected_return',     label: 'Expected Return (% p.a.)', placeholder: '12' },
              { key: 'inflation_rate',      label: 'Inflation Rate (% p.a.)',  placeholder: '6'  },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <Label>{label}</Label>
                <Input
                  type="number"
                  placeholder={placeholder}
                  value={form[key as keyof typeof form]}
                  onChange={e => handleChange(key, e.target.value)}
                  className="mt-1"
                />
              </div>
            ))}

            <Button
              className="w-full mt-2"
              onClick={handleCalculate}
              disabled={loading}
            >
              {loading ? (
                <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Calculating...</>
              ) : (
                <><Zap className="w-4 h-4 mr-2" /> Calculate FIRE Number</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Panel */}
        <div className="space-y-4">
          {result ? (
            <>
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <Card className="border-primary/30 bg-gradient-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Your FIRE Number</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold text-gradient">{fmt(result.fire_number)}</p>
                    {result.inflation_adjusted_fire_number && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Inflation-adjusted: {fmt(result.inflation_adjusted_fire_number)}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <div className="grid grid-cols-2 gap-3">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar className="w-4 h-4 text-accent" />
                      <span className="text-xs text-muted-foreground">Years to FIRE</span>
                    </div>
                    <p className="text-xl font-bold">{result.years_to_fire ?? '—'}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp className="w-4 h-4 text-accent" />
                      <span className="text-xs text-muted-foreground">Monthly Needed</span>
                    </div>
                    <p className="text-xl font-bold">{fmt(result.monthly_required)}</p>
                  </CardContent>
                </Card>
              </div>

              {result.current_gap !== undefined && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Monthly Gap</span>
                      <span className={`text-sm font-semibold ${result.current_gap <= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {result.current_gap <= 0
                          ? '✅ On track!'
                          : `₹${result.current_gap.toLocaleString('en-IN')} to close`}
                      </span>
                    </div>
                    <Progress
                      value={result.current_gap <= 0 ? 100 : Math.min(
                        100,
                        ((result.monthly_required || 0) - result.current_gap) /
                        (result.monthly_required || 1) * 100
                      )}
                      className="h-2"
                    />
                  </CardContent>
                </Card>
              )}

              {result.roadmap && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Roadmap</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground whitespace-pre-line">{result.roadmap}</p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground">
                <Target className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Fill in your details and click<br /><strong>Calculate FIRE Number</strong></p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
