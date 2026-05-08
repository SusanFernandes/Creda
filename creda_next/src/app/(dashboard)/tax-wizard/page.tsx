'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Receipt, IndianRupee, TrendingDown, CheckCircle, RefreshCw, Zap, AlertCircle, MessageSquare, Send, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { ApiService } from '@/services/api';
import { useUser } from '@clerk/nextjs';

interface TaxResult {
  old_regime_tax?: number;
  new_regime_tax?: number;
  recommended?: string;
  savings?: number;
  missed_deductions?: string[];
  effective_rate_old?: number;
  effective_rate_new?: number;
  [key: string]: any;
}

export default function TaxWizard() {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaxResult | null>(null);
  const [copilotQuery, setCopilotQuery] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotAnswer, setCopilotAnswer] = useState<string | null>(null);

  const handleCopilotAsk = async () => {
    if (!copilotQuery.trim()) return;
    setCopilotLoading(true);
    try {
      const data = await ApiService.taxCopilot({ query: copilotQuery } as any);
      setCopilotAnswer(data?.response || data?.answer || JSON.stringify(data));
    } catch { setCopilotAnswer('Unable to reach Tax Copilot. Please try again.'); }
    finally { setCopilotLoading(false); }
  };

  const [form, setForm] = useState({
    annual_income: 1200000,
    investments_80c: 150000,
    nps_contribution: 50000,
    health_insurance_premium: 25000,
    hra: 0,
    home_loan_interest: 0,
  });

  const handleChange = (key: string, value: string) => {
    setForm(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const handleCalculate = async () => {
    setLoading(true);
    const req = { user_id: user?.id || 'guest', ...form };
    const data = await ApiService.taxWizard(req as any);
    setResult(data);
    setLoading(false);
  };

  const fmtTax = (n?: number) =>
    n !== undefined ? `₹${n.toLocaleString('en-IN')}` : '—';

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
            <Receipt className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">Tax Wizard</h1>
            <p className="text-muted-foreground text-sm">Old regime vs New regime — find the best fit</p>
          </div>
          <Badge variant="outline" className="ml-auto">FY 2024-25</Badge>
        </div>
      </motion.div>

      <Tabs defaultValue="compare" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="compare" className="flex-1">Compare Regimes</TabsTrigger>
          <TabsTrigger value="copilot" className="flex-1"><MessageSquare className="w-4 h-4 mr-1" /> Tax Copilot</TabsTrigger>
        </TabsList>

        <TabsContent value="compare">
      <div className="grid md:grid-cols-2 gap-6">
        {/* Input */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Income & Deductions</CardTitle>
            <CardDescription>All figures in ₹ per year</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { key: 'annual_income',            label: 'Annual Income (CTC / Gross)',    placeholder: '1200000' },
              { key: 'investments_80c',           label: '80C Investments (max ₹1.5L)',    placeholder: '150000'  },
              { key: 'nps_contribution',          label: 'NPS Employer 80CCD(2) / 80CCD(1B)', placeholder: '50000' },
              { key: 'health_insurance_premium',  label: '80D Health Insurance Premium',  placeholder: '25000'   },
              { key: 'hra',                       label: 'HRA Exemption Claimed',          placeholder: '0'       },
              { key: 'home_loan_interest',        label: '24(b) Home Loan Interest',       placeholder: '0'       },
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

            <Button className="w-full mt-2" onClick={handleCalculate} disabled={loading}>
              {loading
                ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Analysing...</>
                : <><Zap className="w-4 h-4 mr-2" /> Compare Regimes</>}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Recommendation */}
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <Card className={`border-2 ${result.recommended === 'new' ? 'border-green-500/40' : 'border-blue-500/40'} bg-gradient-card`}>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle className="w-5 h-5 text-green-500" />
                      <span className="font-semibold">
                        {result.recommended === 'new' ? 'New Regime Recommended' : 'Old Regime Recommended'}
                      </span>
                    </div>
                    <p className="text-2xl font-bold text-green-500">
                      Save {fmtTax(result.savings)}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Side-by-side comparison */}
              <Tabs defaultValue={result.recommended || 'new'}>
                <TabsList className="w-full">
                  <TabsTrigger value="old" className="flex-1">Old Regime</TabsTrigger>
                  <TabsTrigger value="new" className="flex-1">New Regime</TabsTrigger>
                </TabsList>
                <TabsContent value="old">
                  <Card>
                    <CardContent className="pt-4 space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Tax Payable</span>
                        <span className="font-bold text-red-400">{fmtTax(result.old_regime_tax)}</span>
                      </div>
                      {result.effective_rate_old !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Effective Tax Rate</span>
                          <span className="font-semibold">{result.effective_rate_old.toFixed(1)}%</span>
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">Allows deductions under 80C, 80D, HRA, etc.</p>
                    </CardContent>
                  </Card>
                </TabsContent>
                <TabsContent value="new">
                  <Card>
                    <CardContent className="pt-4 space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Tax Payable</span>
                        <span className="font-bold text-green-500">{fmtTax(result.new_regime_tax)}</span>
                      </div>
                      {result.effective_rate_new !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Effective Tax Rate</span>
                          <span className="font-semibold">{result.effective_rate_new.toFixed(1)}%</span>
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">Lower slab rates; most deductions not allowed.</p>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>

              {/* Missed deductions */}
              {result.missed_deductions && result.missed_deductions.length > 0 && (
                <Card className="border-yellow-500/30">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-yellow-500" />
                      Missed Deductions
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.missed_deductions.map((d: string, i: number) => (
                        <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                          <TrendingDown className="w-3 h-3 mt-0.5 text-yellow-500 shrink-0" />
                          {d}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground">
                <IndianRupee className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Enter your income details and click<br /><strong>Compare Regimes</strong></p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
        </TabsContent>

        <TabsContent value="copilot">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                Tax Copilot
              </CardTitle>
              <CardDescription>Ask any tax-related question and get AI-powered advice</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="e.g. Should I invest more in ELSS or PPF? What about NPS for additional 50k deduction?"
                value={copilotQuery}
                onChange={e => setCopilotQuery(e.target.value)}
                rows={3}
              />
              <Button onClick={handleCopilotAsk} disabled={copilotLoading || !copilotQuery.trim()} className="w-full">
                {copilotLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Thinking...</> : <><Send className="w-4 h-4 mr-2" /> Ask Copilot</>}
              </Button>
              {copilotAnswer && (
                <Card className="bg-muted/50">
                  <CardContent className="pt-4 whitespace-pre-wrap text-sm">{copilotAnswer}</CardContent>
                </Card>
              )}
              <div className="flex flex-wrap gap-2">
                {['How to save tax on capital gains?', 'Old vs new regime for 15L salary?', 'Best 80C investments for 2024?'].map(q => (
                  <Badge key={q} variant="outline" className="cursor-pointer hover:bg-primary/10" onClick={() => setCopilotQuery(q)}>{q}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
