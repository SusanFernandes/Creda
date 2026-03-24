import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Calculator, TrendingUp, RefreshCw, BarChart3, Zap, PiggyBank } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { ApiService, SIPCalcRequest } from '@/services/api';

interface SIPResult {
  monthly_amount?: number;
  years?: number;
  expected_return?: number;
  total_invested?: number;
  expected_value?: number;
  wealth_gain?: number;
  step_up_value?: number;
  [key: string]: any;
}

export default function SIPCalculator() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SIPResult | null>(null);

  const [form, setForm] = useState({
    monthly_amount: 10000,
    expected_return: 12,
    years: 15,
    step_up_percent: 10,
  });

  const handleSlider = (key: string, value: number[]) => {
    setForm(prev => ({ ...prev, [key]: value[0] }));
  };

  const handleCalculate = async () => {
    setLoading(true);
    const req: SIPCalcRequest = { ...form };
    const data = await ApiService.calculateSIP(req);
    setResult(data);
    setLoading(false);
  };

  const fmt = (n?: number) =>
    n !== undefined
      ? n >= 10000000
        ? `₹${(n / 10000000).toFixed(2)} Cr`
        : `₹${(n / 100000).toFixed(2)} L`
      : '—';

  const wealthRatio = result
    ? ((result.wealth_gain || 0) / (result.total_invested || 1)) * 100
    : 0;

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
            <Calculator className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">SIP Calculator</h1>
            <p className="text-muted-foreground text-sm">Systematic Investment Plan — visualise your wealth</p>
          </div>
          <Badge variant="outline" className="ml-auto">Step-up Enabled</Badge>
        </div>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Sliders */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Adjust Parameters</CardTitle>
            <CardDescription>Drag sliders to see your wealth grow in real-time</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <Label>Monthly SIP Amount</Label>
                <span className="text-sm font-semibold text-accent">₹{form.monthly_amount.toLocaleString('en-IN')}</span>
              </div>
              <Slider
                min={500} max={100000} step={500}
                value={[form.monthly_amount]}
                onValueChange={v => handleSlider('monthly_amount', v)}
              />
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Expected Return (% p.a.)</Label>
                <span className="text-sm font-semibold text-accent">{form.expected_return}%</span>
              </div>
              <Slider
                min={6} max={30} step={0.5}
                value={[form.expected_return]}
                onValueChange={v => handleSlider('expected_return', v)}
              />
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Investment Tenure</Label>
                <span className="text-sm font-semibold text-accent">{form.years} yrs</span>
              </div>
              <Slider
                min={1} max={40} step={1}
                value={[form.years]}
                onValueChange={v => handleSlider('years', v)}
              />
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Annual Step-up (%)</Label>
                <span className="text-sm font-semibold text-accent">{form.step_up_percent}%</span>
              </div>
              <Slider
                min={0} max={25} step={1}
                value={[form.step_up_percent]}
                onValueChange={v => handleSlider('step_up_percent', v)}
              />
            </div>

            <Button className="w-full" onClick={handleCalculate} disabled={loading}>
              {loading
                ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Calculating...</>
                : <><Zap className="w-4 h-4 mr-2" /> Calculate</>}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <div className="space-y-4">
          {result ? (
            <>
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <Card className="border-primary/30 bg-gradient-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Expected Wealth</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold text-gradient">{fmt(result.expected_value)}</p>
                    {result.step_up_value && result.step_up_value !== result.expected_value && (
                      <p className="text-xs text-green-500 mt-1">
                        With step-up: {fmt(result.step_up_value)} 🚀
                      </p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <div className="grid grid-cols-2 gap-3">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <PiggyBank className="w-4 h-4 text-blue-500" />
                      <span className="text-xs text-muted-foreground">Total Invested</span>
                    </div>
                    <p className="text-lg font-bold">{fmt(result.total_invested)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp className="w-4 h-4 text-green-500" />
                      <span className="text-xs text-muted-foreground">Wealth Gain</span>
                    </div>
                    <p className="text-lg font-bold text-green-500">{fmt(result.wealth_gain)}</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardContent className="pt-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">Returns vs Invested</span>
                    <span className="text-sm font-semibold text-accent">{wealthRatio.toFixed(0)}%</span>
                  </div>
                  <div className="relative h-4 bg-muted rounded-full overflow-hidden">
                    <div
                      className="absolute left-0 top-0 h-full bg-blue-500/60 rounded-full"
                      style={{ width: `${100 / (1 + wealthRatio / 100)}%` }}
                    />
                    <div
                      className="absolute h-full bg-green-500/60 rounded-full"
                      style={{
                        left: `${100 / (1 + wealthRatio / 100)}%`,
                        right: 0,
                      }}
                    />
                  </div>
                  <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                    <span>Invested</span>
                    <span>Returns</span>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Adjust the sliders and click<br /><strong>Calculate</strong> to see results</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
