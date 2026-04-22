import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Target, 
  Plus, 
  ChevronRight,
  TrendingUp,
  BrainCircuit,
  Calendar,
  DollarSign,
  ArrowUpRight,
  LayoutGrid
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import AdvancedLineChart from '@/components/charts/AdvancedLineChart';

interface Goal {
  id: string;
  name: string;
  target: number;
  current: number;
  deadline: Date;
  status: 'on_track' | 'ahead' | 'behind';
}

const mockGoals: Goal[] = [
  { id: '1', name: 'Apartment Purchase', target: 2500000, current: 850000, deadline: new Date('2026-12-31'), status: 'on_track' },
  { id: '2', name: 'Emergency Safety Net', target: 600000, current: 450000, deadline: new Date('2024-06-30'), status: 'ahead' },
  { id: '3', name: 'SUV Upgrade', target: 800000, current: 120000, deadline: new Date('2025-12-31'), status: 'behind' }
];

const Goals: React.FC = () => {
  const [goals] = useState<Goal[]>(mockGoals);
  const [showAddDialog, setShowAddDialog] = useState(false);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const calculateProgress = (current: number, target: number) => Math.min((current / target) * 100, 100);

  const topMetrics = [
    { title: "Total Target Value", value: formatCurrency(goals.reduce((sum, g) => sum + g.target, 0)), icon: Target, color: "text-blue-600" },
    { title: "Current Savings", value: formatCurrency(goals.reduce((sum, g) => sum + g.current, 0)), icon: DollarSign, color: "text-slate-600" },
    { title: "Probability Score", value: "82%", icon: BrainCircuit, color: "text-slate-600" },
    { title: "Portfolio Health", value: "Optimal", icon: TrendingUp, color: "text-emerald-600" }
  ];

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-6xl mx-auto space-y-12">
        {/* Simple Minimal Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-slate-200 dark:border-slate-800 pb-10">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">Financial Goals</h1>
            <p className="text-slate-500 text-sm font-medium">Track and optimize your long-term capital objectives.</p>
          </div>
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button className="rounded-xl h-11 px-6 bg-slate-900 dark:bg-slate-50 text-white dark:text-slate-900 hover:opacity-90 transition-all font-medium">
                  <Plus className="mr-2 h-4 w-4" /> New Goal
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-[1.5rem] bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold">Define New Goal</DialogTitle>
                  <DialogDescription>Set a target and timeline for your next financial milestone.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 pt-4">
                  <div className="space-y-1.5 font-medium">
                    <Label className="text-xs text-slate-500 uppercase tracking-wider">Goal Name</Label>
                    <Input placeholder="e.g. Retirement Fund" className="h-11 rounded-xl" />
                  </div>
                  <div className="space-y-1.5 font-medium">
                    <Label className="text-xs text-slate-500 uppercase tracking-wider">Target Amount (₹)</Label>
                    <Input type="number" placeholder="500,000" className="h-11 rounded-xl" />
                  </div>
                  <Button className="w-full h-11 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium">Create Goal</Button>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="outline" className="h-11 w-11 rounded-xl border-slate-200 dark:border-slate-800">
               <LayoutGrid className="w-4 h-4 text-slate-500" />
            </Button>
          </div>
        </div>

        {/* Minimal Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {topMetrics.map((metric) => (
            <Card key={metric.title} className="border-none shadow-sm dark:bg-slate-900/50 bg-white">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{metric.title}</span>
                  <metric.icon className={cn("w-4 h-4", metric.color)} />
                </div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{metric.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          <div className="lg:col-span-2 space-y-6">
             <div className="flex items-center justify-between px-2">
                <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Active Progress</h3>
                <span className="text-xs font-semibold text-blue-600">3 Nodes Live</span>
             </div>
             
             <div className="grid grid-cols-1 gap-4">
               {goals.map((goal) => (
                 <motion.div key={goal.id} whileHover={{ y: -2 }}>
                    <Card className="border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:shadow-md transition-all group overflow-hidden">
                       <CardContent className="p-6">
                          <div className="flex items-center justify-between mb-5">
                             <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-800 flex items-center justify-center border border-slate-100 dark:border-slate-700 font-bold group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                   <Target className="w-4 h-4" />
                                </div>
                                <div className="space-y-0.5">
                                   <h4 className="font-semibold text-slate-900 dark:text-slate-50">{goal.name}</h4>
                                   <p className="text-xs text-slate-500">Targeting {goal.deadline.toLocaleDateString()}</p>
                                </div>
                             </div>
                             <div className="text-right">
                                <span className={cn(
                                  "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full",
                                  goal.status === 'ahead' ? "bg-emerald-50 text-emerald-600" :
                                  goal.status === 'on_track' ? "bg-blue-50 text-blue-600" :
                                  "bg-amber-50 text-amber-600"
                                )}>
                                  {goal.status.replace('_', ' ')}
                                </span>
                             </div>
                          </div>
                          
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs font-semibold text-slate-600 dark:text-slate-400">
                               <span>{formatCurrency(goal.current)} of {formatCurrency(goal.target)}</span>
                               <span>{calculateProgress(goal.current, goal.target).toFixed(0)}%</span>
                            </div>
                            <Progress value={calculateProgress(goal.current, goal.target)} className="h-1.5" />
                          </div>
                       </CardContent>
                    </Card>
                 </motion.div>
               ))}
             </div>

             <Card className="border-none bg-white dark:bg-slate-900 shadow-sm p-6 overflow-hidden relative">
                <div className="flex justify-between items-center mb-8">
                   <h3 className="text-sm font-bold tracking-widest uppercase text-slate-400">Projected Trajectory</h3>
                   <Badge variant="outline" className="text-[10px] font-bold text-slate-500 border-slate-200">Aggregate Scan</Badge>
                </div>
                <AdvancedLineChart
                  data={[
                    { name: 'Jan', value: 30, target: 35 },
                    { name: 'Feb', value: 45, target: 40 },
                    { name: 'Mar', value: 50, target: 55 },
                    { name: 'Apr', value: 62, target: 60 },
                    { name: 'May', value: 68, target: 70 },
                  ]}
                  title="" description="" valueSuffix="%" height={240} noCard showTarget
                />
             </Card>
          </div>

          <div className="space-y-6">
            <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-2">Core Insights</h3>
            <Card className="border-none bg-blue-600 p-8 text-white rounded-[2rem] shadow-xl shadow-blue-500/10 relative overflow-hidden group">
               <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 blur-[60px] rounded-full translate-x-1/2 -translate-y-1/2" />
               <BrainCircuit className="w-8 h-8 mb-6 opacity-80" />
               <h4 className="text-2xl font-bold leading-tight mb-4 tracking-tight italic">Calibration Suggestion</h4>
               <p className="text-white/80 text-sm font-medium leading-relaxed mb-8">
                 Increasing your savings by <span className="text-white font-bold italic">₹5,000</span> will reduce your "Apartment Purchase" timeline by <span className="text-white font-bold italic">4.2 months</span>.
               </p>
               <Button className="w-full h-12 bg-white text-blue-600 hover:bg-slate-100 font-bold rounded-xl flex items-center justify-center gap-2 group">
                 Apply Optimization <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
               </Button>
            </Card>

            <Card className="border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-6">
               <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  <Calendar className="w-3 h-3" /> Upcoming Milestone
               </div>
               <div className="space-y-1">
                  <div className="text-xl font-bold italic tracking-tight text-slate-900 dark:text-slate-50 italic">Emergency Safety Net</div>
                  <p className="text-xs text-slate-500 font-medium italic">Target completion: June 2024</p>
               </div>
               <div className="pt-4 border-t border-slate-50 dark:border-slate-800">
                  <div className="flex justify-between mb-1 text-[10px] font-bold text-slate-400 uppercase italic">Current Confidence</div>
                  <div className="text-2xl font-black text-emerald-500 italic uppercase">92.4%</div>
               </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Goals;