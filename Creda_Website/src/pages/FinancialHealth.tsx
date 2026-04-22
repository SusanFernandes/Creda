import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Target, 
  TrendingUp, 
  Shield, 
  PiggyBank,
  ArrowRight,
  Activity,
  Brain,
  CheckCircle,
  AlertCircle,
  BarChart3,
  Calendar,
  Zap,
  Lock,
  ArrowUpRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import AdvancedPieChart from '@/components/charts/AdvancedPieChart';

interface HealthComponent {
  id: string;
  name: string;
  score: number;
  maxScore: number;
  status: 'excellent' | 'good' | 'needs_improvement' | 'poor';
  icon: React.ReactNode;
  recommendations: string[];
}

const healthComponents: HealthComponent[] = [
  { id: 'savings_rate', name: 'Savings Rate', score: 25, maxScore: 30, status: 'good', icon: <PiggyBank className="w-4 h-4" />, recommendations: ['Increase SIP by ₹5,000 monthly', 'Set up automatic savings transfer'] },
  { id: 'emergency_fund', name: 'Emergency Fund', score: 15, maxScore: 25, status: 'needs_improvement', icon: <Shield className="w-4 h-4" />, recommendations: ['Build to 6 months of expenses', 'Keep funds in liquid investments'] },
  { id: 'diversification', name: 'Portfolio Diversification', score: 18, maxScore: 20, status: 'excellent', icon: <BarChart3 className="w-4 h-4" />, recommendations: ['Maintain current asset allocation', 'Review sector focus quarterly'] },
  { id: 'age_allocation', name: 'Age-Appropriate Allocation', score: 14, maxScore: 25, status: 'poor', icon: <Target className="w-4 h-4" />, recommendations: ['Increase equity allocation to 70%', 'Reduce debt exposure for higher returns'] }
];

const FinancialHealth: React.FC = () => {
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);

  const totalScore = healthComponents.reduce((sum, comp) => sum + comp.score, 0);
  const maxTotalScore = healthComponents.reduce((sum, comp) => sum + comp.maxScore, 0);
  const healthPercentage = (totalScore / maxTotalScore) * 100;

  const getGrade = (percentage: number) => {
    if (percentage >= 90) return 'A+';
    if (percentage >= 80) return 'A';
    if (percentage >= 70) return 'B+';
    return 'B';
  };

  const topMetrics = [
    { title: "Current Resilience", value: `${totalScore}/${maxTotalScore}`, icon: Activity, trend: "+4.2%", color: "text-blue-600" },
    { title: "Global Percentile", value: "65th", icon: Activity, trend: "+2.1%", color: "text-slate-500" },
    { title: "Network Status", value: "Locked", icon: Lock, trend: "+1.3%", color: "text-slate-500" },
    { title: "Optimization Cap", value: "+33 pts", icon: Brain, trend: "+5.0%", color: "text-emerald-600" }
  ];

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6 font-sans">
      <div className="max-w-6xl mx-auto space-y-12">
        {/* Superior Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-slate-200 dark:border-slate-800 pb-10">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">System Integrity</h1>
            <p className="text-slate-500 text-sm font-medium italic">Deep scan analysis of your financial performance nodes.</p>
          </div>
          <div className="flex items-center gap-3">
             <Button className="rounded-xl h-11 px-6 bg-blue-600 text-white hover:bg-blue-700 font-medium">
               <Zap className="mr-2 h-4 w-4" /> Run Deep Scan
             </Button>
          </div>
        </div>

        {/* Minimal Metric Layer */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {topMetrics.map((metric) => (
            <Card key={metric.title} className="border-none shadow-sm dark:bg-slate-900/50 bg-white">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{metric.title}</span>
                  <metric.icon className={cn("w-3.5 h-3.5", metric.color)} />
                </div>
                <div className="flex items-baseline gap-2">
                   <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 uppercase italic">{metric.value}</div>
                   <span className="text-[10px] font-bold text-emerald-500">{metric.trend}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Cognitive Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          <Card className="lg:col-span-1 border-none shadow-sm bg-white dark:bg-slate-900 p-8 flex flex-col justify-center text-center space-y-8 rounded-[2rem]">
             <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Aggregate Integrity</span>
                <div className="text-9xl font-black italic tracking-tighter text-blue-600 dark:text-blue-500 opacity-90">{getGrade(healthPercentage)}</div>
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Verified System Rating</p>
             </div>
             <div className="space-y-3 pt-6 border-t border-slate-100 dark:border-slate-800">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase text-slate-400 tracking-widest">
                   <span>Score Node</span>
                   <span>{totalScore}/{maxTotalScore}</span>
                </div>
                <Progress value={healthPercentage} className="h-1.5" />
             </div>
          </Card>

          <Card className="lg:col-span-2 border-none shadow-sm bg-white dark:bg-slate-900 p-8 rounded-[2rem] overflow-hidden">
             <div className="flex items-center justify-between mb-8">
                <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Architecture Log</h3>
                <Badge variant="outline" className="text-[10px] uppercase font-bold text-slate-400">Component Stream</Badge>
             </div>
             <AdvancedPieChart
               data={healthComponents.map(c => ({
                 name: c.name,
                 value: (c.score / c.maxScore) * 100,
               }))}
               title="" description="" valueSuffix="%" height={260} noCard
             />
          </Card>
        </div>

        {/* Action Layer */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
           <div className="space-y-6">
              <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-2">Factor Calibration</h3>
              <div className="grid grid-cols-1 gap-4">
                 {healthComponents.map(component => (
                    <Card key={component.id} className="border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:border-blue-500/30 transition-all cursor-pointer group">
                       <CardContent className="p-6 space-y-4">
                          <div className="flex items-center justify-between">
                             <div className="flex items-center gap-4">
                                <div className="p-2.5 bg-slate-50 dark:bg-slate-800 rounded-xl text-blue-600 border border-slate-100 dark:border-slate-700 font-bold group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                   {component.icon}
                                </div>
                                <h4 className="font-semibold text-slate-900 dark:text-slate-50 italic uppercase italic">{component.name}</h4>
                             </div>
                             <div className="text-right">
                                <span className={cn(
                                  "text-[10px] font-bold uppercase tracking-widest italic",
                                  component.status === 'excellent' ? "text-emerald-500" :
                                  component.status === 'good' ? "text-blue-500" :
                                  "text-amber-500"
                                )}>{component.status.replace('_', ' ')}</span>
                             </div>
                          </div>
                          <Progress value={(component.score / component.maxScore) * 100} className="h-1" />
                       </CardContent>
                    </Card>
                 ))}
              </div>
           </div>

           <div className="space-y-6">
              <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-2">Optimization Matrix</h3>
              <Tabs defaultValue="actions" className="w-full">
                <TabsList className="w-full bg-slate-100 dark:bg-slate-900 p-1 rounded-xl h-11">
                   <TabsTrigger value="actions" className="flex-1 rounded-lg font-bold text-[10px] uppercase tracking-widest">Priority</TabsTrigger>
                   <TabsTrigger value="insights" className="flex-1 rounded-lg font-bold text-[10px] uppercase tracking-widest">Cognitive</TabsTrigger>
                </TabsList>
                <TabsContent value="actions" className="mt-6 space-y-4">
                   {[
                      { action: 'Build Emergency Fund', impact: '+12 pts', color: 'border-red-500' },
                      { action: 'Increase Equity SIP', impact: '+8 pts', color: 'border-amber-500' },
                   ].map((op, i) => (
                      <Card key={i} className={cn("p-6 border-l-4 bg-white dark:bg-slate-900 group hover:shadow-md transition-all rounded-r-2xl", op.color)}>
                         <div className="flex items-center justify-between">
                            <div>
                               <h4 className="text-lg font-bold italic tracking-tight text-slate-900 dark:text-slate-50 uppercase italic">{op.action}</h4>
                               <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Impact potential: <span className="text-blue-500">{op.impact}</span></p>
                            </div>
                            <Button variant="ghost" size="icon" className="hover:text-blue-600">
                               <ArrowUpRight className="w-5 h-5" />
                            </Button>
                         </div>
                      </Card>
                   ))}
                </TabsContent>
                <TabsContent value="insights" className="mt-6">
                   <Card className="border-none bg-slate-900 text-white p-10 rounded-[2.5rem] relative overflow-hidden group">
                      <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/20 blur-[60px] rounded-full translate-x-1/2 -translate-y-1/2" />
                      <Brain className="w-8 h-8 text-blue-500 mb-6" />
                      <p className="text-lg font-medium leading-relaxed italic border-l-2 border-blue-500 pl-6 text-slate-300">
                        "Your current diversification index is <span className="text-white font-bold">11% above</span> peer average. Focus shifting to liquidity nodes will maximize resilience."
                      </p>
                      <Button className="w-full h-12 bg-white text-slate-900 rounded-xl font-bold uppercase tracking-widest mt-10 hover:bg-white/90">
                        Execute Health Plan
                      </Button>
                   </Card>
                </TabsContent>
              </Tabs>
           </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialHealth;