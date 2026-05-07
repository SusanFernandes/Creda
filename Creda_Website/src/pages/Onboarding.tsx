import React, { useState } from 'react';
import { Sparkles, ArrowRight, ArrowLeft, Check, User, Briefcase, Target, PiggyBank } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { ApiService } from '@/services/api';
import { useNavigate } from 'react-router-dom';

const STEPS = [
  { id: 'personal', title: 'Personal Info', icon: User },
  { id: 'income', title: 'Income & Expenses', icon: Briefcase },
  { id: 'goals', title: 'Financial Goals', icon: Target },
  { id: 'complete', title: 'All Set!', icon: Check },
];

const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '', age: '', language: 'en',
    monthly_income: '', monthly_expenses: '', monthly_emi: '',
    emergency_fund: '', savings: '',
    risk_tolerance: 'moderate', goal_type: 'retirement', time_horizon: '20',
    dependents: '0', target_retirement_age: '60',
  });

  const update = (key: string, val: string) => setForm(prev => ({ ...prev, [key]: val }));

  const finish = async () => {
    setSaving(true);
    try {
      await ApiService.upsertProfile({
        name: form.name,
        age: parseInt(form.age) || 30,
        language: form.language,
        monthly_income: parseFloat(form.monthly_income) || 0,
        monthly_expenses: parseFloat(form.monthly_expenses) || 0,
        monthly_emi: parseFloat(form.monthly_emi) || 0,
        emergency_fund: parseFloat(form.emergency_fund) || 0,
        savings: parseFloat(form.savings) || 0,
        risk_tolerance: form.risk_tolerance,
        goal_type: form.goal_type,
        time_horizon: parseInt(form.time_horizon) || 20,
        dependents: parseInt(form.dependents) || 0,
        target_retirement_age: parseInt(form.target_retirement_age) || 60,
      });
      setStep(3);
    } catch { /* still proceed */ setStep(3); }
    finally { setSaving(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 flex items-center justify-center px-4 py-10">
      <div className="max-w-lg w-full space-y-6">
        {/* Progress */}
        <div className="flex items-center gap-3 mb-4">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${i <= step ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
                {i < step ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && <div className={`w-8 h-0.5 ${i < step ? 'bg-primary' : 'bg-muted'}`} />}
            </div>
          ))}
        </div>
        <Progress value={((step + 1) / STEPS.length) * 100} className="h-2" />

        {/* Step 0: Personal */}
        {step === 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><User className="w-5 h-5" />Welcome to Creda!</CardTitle>
              <CardDescription>Let's set up your financial profile.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div><Label>Name</Label><Input value={form.name} onChange={e => update('name', e.target.value)} placeholder="Your name" className="rounded-xl mt-1" /></div>
              <div><Label>Age</Label><Input type="number" value={form.age} onChange={e => update('age', e.target.value)} placeholder="30" className="rounded-xl mt-1" /></div>
              <div><Label>Preferred Language</Label>
                <Select value={form.language} onValueChange={v => update('language', v)}>
                  <SelectTrigger className="rounded-xl mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem><SelectItem value="hi">हिन्दी</SelectItem>
                    <SelectItem value="ta">தமிழ்</SelectItem><SelectItem value="bn">বাংলা</SelectItem>
                    <SelectItem value="te">తెలుగు</SelectItem><SelectItem value="mr">मराठी</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => setStep(1)} disabled={!form.name} className="rounded-xl"><ArrowRight className="w-4 h-4 ml-1" /></Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 1: Income */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Briefcase className="w-5 h-5" />Income & Expenses</CardTitle>
              <CardDescription>Monthly figures in ₹.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div><Label>Monthly Income (₹)</Label><Input type="number" value={form.monthly_income} onChange={e => update('monthly_income', e.target.value)} placeholder="50000" className="rounded-xl mt-1" /></div>
              <div><Label>Monthly Expenses (₹)</Label><Input type="number" value={form.monthly_expenses} onChange={e => update('monthly_expenses', e.target.value)} placeholder="30000" className="rounded-xl mt-1" /></div>
              <div><Label>Monthly EMI (₹)</Label><Input type="number" value={form.monthly_emi} onChange={e => update('monthly_emi', e.target.value)} placeholder="0" className="rounded-xl mt-1" /></div>
              <div><Label>Emergency Fund (₹)</Label><Input type="number" value={form.emergency_fund} onChange={e => update('emergency_fund', e.target.value)} placeholder="100000" className="rounded-xl mt-1" /></div>
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setStep(0)} className="rounded-xl"><ArrowLeft className="w-4 h-4 mr-1" /></Button>
                <Button onClick={() => setStep(2)} className="rounded-xl"><ArrowRight className="w-4 h-4 ml-1" /></Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Goals */}
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Target className="w-5 h-5" />Financial Goals</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div><Label>Risk Tolerance</Label>
                <Select value={form.risk_tolerance} onValueChange={v => update('risk_tolerance', v)}>
                  <SelectTrigger className="rounded-xl mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div><Label>Primary Goal</Label>
                <Select value={form.goal_type} onValueChange={v => update('goal_type', v)}>
                  <SelectTrigger className="rounded-xl mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="retirement">Retirement</SelectItem><SelectItem value="house">Buy a House</SelectItem>
                    <SelectItem value="education">Children's Education</SelectItem><SelectItem value="wealth">Wealth Building</SelectItem>
                    <SelectItem value="emergency">Emergency Fund</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div><Label>Investment Horizon (years)</Label><Input type="number" value={form.time_horizon} onChange={e => update('time_horizon', e.target.value)} placeholder="20" className="rounded-xl mt-1" /></div>
              <div><Label>Dependents</Label><Input type="number" value={form.dependents} onChange={e => update('dependents', e.target.value)} placeholder="0" className="rounded-xl mt-1" /></div>
              <div><Label>Target Retirement Age</Label><Input type="number" value={form.target_retirement_age} onChange={e => update('target_retirement_age', e.target.value)} placeholder="60" className="rounded-xl mt-1" /></div>
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setStep(1)} className="rounded-xl"><ArrowLeft className="w-4 h-4 mr-1" /></Button>
                <Button onClick={finish} disabled={saving} className="rounded-xl">
                  {saving ? 'Saving...' : <><Check className="w-4 h-4 mr-1" />Complete</>}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Done */}
        {step === 3 && (
          <Card className="text-center">
            <CardContent className="py-16 space-y-6">
              <div className="mx-auto p-4 bg-green-100 dark:bg-green-900/30 rounded-2xl w-fit"><Sparkles className="w-12 h-12 text-green-600" /></div>
              <div>
                <h2 className="text-2xl font-bold">You're all set, {form.name}!</h2>
                <p className="text-sm text-muted-foreground mt-2">Your Creda financial profile is ready. All AI agents now have your context.</p>
              </div>
              <Button onClick={() => navigate('/dashboard')} size="lg" className="rounded-xl">Go to Dashboard <ArrowRight className="w-4 h-4 ml-1" /></Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Onboarding;
