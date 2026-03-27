import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BarChart3, 
  PieChart as PieIcon, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  DollarSign,
  Calendar,
  Filter,
  Download,
  Eye,
  Zap,
  Brain,
  ShieldCheck,
  Target,
  ArrowUpRight,
  ChevronRight,
  Info,
  Activity
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { AdvancedLineChart } from '@/components/charts/AdvancedLineChart';
import { AdvancedPieChart } from '@/components/charts/AdvancedPieChart';

interface ExpenseData {
  category: string;
  budget: number;
  spent: number;
  alert: 'normal' | 'medium' | 'high';
  transactions: number;
  avgTransaction: number;
  color: string;
}

interface AnomalyAlert {
  type: 'unusual_spend' | 'category_spike' | 'frequency_change';
  category: string;
  amount: number;
  confidence: number;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

const mockExpenseData: ExpenseData[] = [
  { category: 'Food & Dining', budget: 15000, spent: 18200, alert: 'high', transactions: 45, avgTransaction: 404, color: '#ef4444' },
  { category: 'Transportation', budget: 8000, spent: 6500, alert: 'normal', transactions: 28, avgTransaction: 232, color: '#10b981' },
  { category: 'Entertainment', budget: 5000, spent: 7800, alert: 'medium', transactions: 12, avgTransaction: 650, color: '#f59e0b' },
  { category: 'Shopping', budget: 12000, spent: 10200, alert: 'normal', transactions: 18, avgTransaction: 567, color: '#3b82f6' },
  { category: 'Healthcare', budget: 3000, spent: 4500, alert: 'medium', transactions: 6, avgTransaction: 750, color: '#8b5cf6' },
  { category: 'Utilities & Bills', budget: 6000, spent: 5800, alert: 'normal', transactions: 8, avgTransaction: 725, color: '#06b6d4' }
];

const mockAnomalies: AnomalyAlert[] = [
  { type: 'unusual_spend', category: 'Food & Dining', amount: 3200, confidence: 0.89, description: 'Restaurant spending 60% higher than usual pattern', severity: 'high' },
  { type: 'category_spike', category: 'Entertainment', amount: 2800, confidence: 0.76, description: 'Entertainment expenses spiked this weekend', severity: 'medium' }
];

const monthlyTrendData = [
  { name: 'Jan', value: 58400, target: 60000 },
  { name: 'Feb', value: 62100, target: 60000 },
  { name: 'Mar', value: 59200, target: 60000 },
  { name: 'Apr', value: 57800, target: 60000 },  
  { name: 'May', value: 64300, target: 60000 },
  { name: 'Jun', value: 61200, target: 60000 }
];

const ExpenseAnalytics: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('current-month');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const totalBudget = mockExpenseData.reduce((sum, item) => sum + item.budget, 0);
  const totalSpent = mockExpenseData.reduce((sum, item) => sum + item.spent, 0);
  const totalSavings = totalBudget - totalSpent;
  const budgetUtilization = (totalSpent / totalBudget) * 100;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getAlertColorClass = (alert: string) => {
    switch (alert) {
      case 'high': return 'text-rose-500';
      case 'medium': return 'text-amber-500';
      default: return 'text-emerald-500';
    }
  };

  const pieChartData = mockExpenseData.map(item => ({
    name: item.category,
    value: item.spent
  }));

  return (
    <div className="container mx-auto p-6 lg:p-10 space-y-8 min-h-screen bg-background">
      {/* Structural Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-border pb-8">
        <div className="space-y-1">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-primary" />
            <span className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground/60">Live Expense Monitoring</span>
          </div>
          <h1 className="text-4xl font-black tracking-tighter">Expense <span className="text-primary">Analytics</span></h1>
          <p className="text-sm text-muted-foreground font-medium">Real-time spend patterns & AI-driven anomaly detection</p>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <SelectTrigger className="w-44 h-12 rounded-xl border-none bg-card shadow-xl font-bold">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-xl border-none bg-card shadow-2xl">
              <SelectItem value="current-month">This Month</SelectItem>
              <SelectItem value="last-month">Last Month</SelectItem>
              <SelectItem value="quarter">Fiscal Quarter</SelectItem>
              <SelectItem value="year">Fiscal Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="h-12 px-6 rounded-xl border-none bg-card shadow-xl font-bold hover:bg-muted">
            <Download className="w-4 h-4 mr-2" /> Export
          </Button>
        </div>
      </div>

      {/* Insight Hub Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Calculated Budget', val: totalBudget, status: 'Total', color: 'text-primary' },
          { label: 'Current Expenditure', val: totalSpent, status: `${budgetUtilization.toFixed(0)}% Utilized`, color: 'text-rose-500' },
          { label: 'Delta Variance', val: Math.abs(totalSavings), status: totalSavings >= 0 ? 'Surplus' : 'Deficit', color: totalSavings >= 0 ? 'text-emerald-500' : 'text-rose-500' },
          { label: 'Anomaly Count', val: mockAnomalies.length, status: 'Critical Fixes', color: 'text-amber-500' },
        ].map((item, idx) => (
          <Card key={idx} className="border-none bg-card shadow-xl p-6 hover:shadow-2xl transition-all group">
            <div className="flex flex-col space-y-1">
              <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 mb-2">{item.label}</span>
              <div className="text-3xl font-black tracking-tighter group-hover:scale-[1.02] transition-transform origin-left">
                {typeof item.val === 'number' && item.label !== 'Anomaly Count' ? formatCurrency(item.val) : item.val}
              </div>
              <div className={`text-[10px] font-bold uppercase tracking-widest mt-2 ${item.color} flex items-center gap-1.5`}>
                <span className={`w-1.5 h-1.5 rounded-full ${item.color.replace('text', 'bg')} animate-pulse`} />
                {item.status}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="overview" className="w-full space-y-8">
        <TabsList className="bg-card shadow-xl p-1 h-14 rounded-2xl border-none grid w-full grid-cols-4 max-w-2xl mx-auto">
          <TabsTrigger value="overview" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-xs transition-all">Overview</TabsTrigger>
          <TabsTrigger value="categories" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-xs transition-all">Categories</TabsTrigger>
          <TabsTrigger value="trends" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-xs transition-all">History</TabsTrigger>
          <TabsTrigger value="anomalies" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-xs transition-all">Anomalies</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-8 animate-in fade-in duration-500 outline-none">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="border-none bg-card shadow-xl p-8">
              <CardTitle className="text-lg font-black tracking-tight mb-8 px-1">Spending Composition</CardTitle>
              <AdvancedPieChart data={pieChartData} height={350} noCard />
            </Card>

            <Card className="border-none bg-card shadow-xl p-8">
              <CardTitle className="text-lg font-black tracking-tight mb-8 px-1">Budget Optimization Status</CardTitle>
              <div className="space-y-6">
                {mockExpenseData.map((item, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex justify-between items-center text-xs font-bold">
                        <span className="text-muted-foreground">{item.category}</span>
                        <div className="flex items-center gap-3">
                            <Badge variant="outline" className={`border-none font-black text-[9px] uppercase px-2 ${item.alert === 'high' ? 'bg-rose-500/10 text-rose-500' : 'bg-muted text-muted-foreground/60'}`}>{item.alert}</Badge>
                            <span className={`font-black tracking-tighter ${getAlertColorClass(item.alert)}`}>{formatCurrency(item.spent)}</span>
                        </div>
                    </div>
                    <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                        <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${Math.min((item.spent / item.budget) * 100, 100)}%` }}
                            className={`h-full rounded-full ${item.alert === 'high' ? 'bg-rose-500' : 'bg-primary'}`}
                        />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="categories" className="animate-in fade-in duration-500 outline-none">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {mockExpenseData.map((cat, idx) => (
                    <Card key={idx} className="border-none bg-card shadow-xl p-6 hover:shadow-2xl transition-all cursor-default">
                        <div className="flex justify-between items-start mb-6">
                            <div className="space-y-0.5">
                                <h3 className="text-md font-black tracking-tight">{cat.category}</h3>
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">Category Node</p>
                            </div>
                            <div className={`p-2 rounded-xl ${cat.alert === 'high' ? 'bg-rose-500/10 text-rose-500' : 'bg-muted/50 text-muted-foreground'}`}>
                                <Zap className="w-4 h-4" />
                            </div>
                        </div>
                        <div className="space-y-4">
                            <div className="flex justify-between items-end">
                                <div className="space-y-1">
                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Expenditure</span>
                                    <div className="text-2xl font-black tracking-tighter">{formatCurrency(cat.spent)}</div>
                                </div>
                                <div className="text-right space-y-1">
                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Utilization</span>
                                    <div className={`text-md font-black tracking-tighter ${getAlertColorClass(cat.alert)}`}>{((cat.spent/cat.budget)*100).toFixed(0)}%</div>
                                </div>
                            </div>
                            <Progress value={Math.min((cat.spent/cat.budget)*100, 100)} className={`h-1.5 ${cat.alert === 'high' ? 'bg-rose-500' : ''}`} />
                            <div className="pt-4 border-t border-border/40 grid grid-cols-2 gap-4">
                                <div className="space-y-0.5">
                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Tx Count</span>
                                    <div className="text-sm font-black tracking-tight">{cat.transactions}</div>
                                </div>
                                <div className="space-y-0.5">
                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Avg Amount</span>
                                    <div className="text-sm font-black tracking-tight">₹{cat.avgTransaction}</div>
                                </div>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
        </TabsContent>

        <TabsContent value="trends" className="animate-in fade-in duration-500 outline-none space-y-8">
            <Card className="border-none bg-card shadow-xl p-8">
                <div className="flex items-center justify-between mb-8">
                    <h3 className="text-lg font-black tracking-tight">Spending Trajectory</h3>
                    <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-primary" /> Spent</div>
                        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-muted border border-border" /> Target</div>
                    </div>
                </div>
                <AdvancedLineChart data={monthlyTrendData} height={350} noCard />
            </Card>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <Card className="border-none bg-card shadow-xl p-8 space-y-6">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60 border-b border-border pb-4">Dynamic Spending Insights</h3>
                    <div className="space-y-4">
                        {[
                            { label: 'Weekend Logic', val: '40% delta detected', icon: Calendar },
                            { label: 'System Efficiency', val: '12% reduction in utilities', icon: ShieldCheck },
                            { label: 'Predictive Spike', val: 'Month-end pattern active', icon: TrendingUp },
                        ].map((item, idx) => (
                            <div key={idx} className="flex items-center justify-between p-4 bg-muted/20 rounded-2xl group cursor-default">
                                <div className="flex items-center gap-4">
                                    <div className="p-2.5 bg-background rounded-xl group-hover:bg-primary group-hover:text-white transition-all">
                                        <item.icon className="w-4 h-4" />
                                    </div>
                                    <span className="text-xs font-black tracking-tight">{item.label}</span>
                                </div>
                                <span className="text-[10px] font-bold text-muted-foreground uppercase">{item.val}</span>
                            </div>
                        ))}
                    </div>
                </Card>

                <Card className="border-none bg-card shadow-xl p-8 space-y-6">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60 border-b border-border pb-4">Optimization Recommendation</h3>
                    <div className="space-y-5">
                        <p className="text-sm font-medium leading-relaxed italic">"Calibrating your <span className="text-primary font-bold">Dining Module</span> could recapture ₹5,200 monthly, accelerating your primary goal timeline by 15%."</p>
                        <Button className="w-full h-12 bg-primary text-white font-black rounded-xl shadow-lg shadow-primary/20 hover:scale-[1.02] transition-all">
                            Enable Auto-Optimization
                        </Button>
                    </div>
                </Card>
            </div>
        </TabsContent>

        <TabsContent value="anomalies" className="animate-in fade-in duration-500 outline-none space-y-8">
            <div className="grid grid-cols-1 gap-6">
                {mockAnomalies.map((anom, idx) => (
                    <Card key={idx} className="border-none bg-card shadow-xl p-8 flex flex-col md:flex-row items-center gap-8 group">
                        <div className={`w-16 h-16 rounded-[1.5rem] flex items-center justify-center text-white shadow-lg ${anom.severity === 'high' ? 'bg-rose-500 shadow-rose-500/20' : 'bg-amber-500 shadow-amber-500/20'}`}>
                            {anom.type === 'unusual_spend' ? <TrendingUp className="w-8 h-8" /> : <Zap className="w-8 h-8" />}
                        </div>
                        <div className="flex-1 space-y-2 text-center md:text-left">
                            <div className="flex flex-col md:flex-row md:items-center gap-3">
                                <h4 className="text-lg font-black tracking-tight capitalize">{anom.type.replace('_', ' ')} : {anom.category}</h4>
                                <Badge className={`${anom.severity === 'high' ? 'bg-rose-500' : 'bg-amber-500'} text-white border-none font-black text-[9px]`}>{anom.severity.toUpperCase()}</Badge>
                            </div>
                            <p className="text-sm text-muted-foreground font-medium leading-relaxed">{anom.description}</p>
                            <div className="pt-4 flex flex-col md:flex-row justify-between items-center gap-4">
                                <div className="text-[10px] font-black uppercase tracking-widest opacity-40">Impact Amount: <span className="text-foreground text-sm tracking-tighter opacity-100 ml-2">{formatCurrency(anom.amount)}</span></div>
                                <Button variant="ghost" className="text-primary font-black text-xs hover:bg-primary/5 uppercase tracking-widest">Resolve Context <ChevronRight className="w-4 h-4 ml-1" /></Button>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            <Card className="border-none bg-card shadow-xl p-10 overflow-hidden relative">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                    <Brain className="w-40 h-40" />
                </div>
                <div className="flex flex-col items-center text-center space-y-6 relative z-10">
                    <div className="p-4 bg-primary/10 rounded-[2rem]">
                        <Activity className="w-10 h-10 text-primary" />
                    </div>
                    <div className="space-y-2">
                        <h3 className="text-3xl font-black tracking-tighter">AI Node Monitoring</h3>
                        <p className="text-muted-foreground max-w-2xl font-medium">Deep learning analysis is processing your expenditure stream with 97.3% accuracy.</p>
                    </div>
                    <div className="grid grid-cols-3 gap-12 w-full max-w-2xl pt-4">
                        <div className="space-y-1">
                            <span className="text-4xl font-black tracking-tighter text-primary">24/7</span>
                            <p className="text-[9px] font-black uppercase tracking-widest opacity-40">Live Watch</p>
                        </div>
                        <div className="space-y-1 border-x border-border/40">
                            <span className="text-4xl font-black tracking-tighter text-emerald-500">97%</span>
                            <p className="text-[9px] font-black uppercase tracking-widest opacity-40">Precision</p>
                        </div>
                        <div className="space-y-1">
                            <span className="text-4xl font-black tracking-tighter text-amber-500">3hr</span>
                            <p className="text-[9px] font-black uppercase tracking-widest opacity-40">Response</p>
                        </div>
                    </div>
                </div>
            </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ExpenseAnalytics;