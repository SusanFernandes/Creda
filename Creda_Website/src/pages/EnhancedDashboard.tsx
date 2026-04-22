import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  DollarSign, 
  PiggyBank, 
  Target,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Mic,
  RefreshCw,
  Bell,
  Eye,
  MoreVertical,
  Plus,
  Filter,
  Download,
  Share,
  Settings,
  Brain
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useLanguage } from '@/contexts/LanguageContext';
import { ApiService, UserProfile } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import MetricCard from '@/components/charts/MetricCard';
import AdvancedLineChart from '@/components/charts/AdvancedLineChart';
import AdvancedPieChart from '@/components/charts/AdvancedPieChart';

const EnhancedDashboard: React.FC = () => {
  const { t } = useLanguage();
  const { toast } = useToast();
  
  const [isLoading, setIsLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [budgetData, setBudgetData] = useState<any>(null);
  const [healthScore, setHealthScore] = useState<any>(null);
  const [timeframe, setTimeframe] = useState<'1M' | '3M' | '6M' | '1Y' | 'ALL'>('3M');

  // Mock user profile - in real app this would come from auth
  const userProfile: UserProfile = {
    age: 32,
    income: 800000,
    savings: 250000,
    dependents: 1,
    risk_tolerance: 3,
    goal_type: "retirement",
    time_horizon: 25
  };

  // Enhanced mock data for charts
  const portfolioPerformanceData = [
    { name: 'Jan', value: 240000, target: 245000 },
    { name: 'Feb', value: 242000, target: 250000 },
    { name: 'Mar', value: 255000, target: 255000 },
    { name: 'Apr', value: 248000, target: 260000 },
    { name: 'May', value: 263000, target: 265000 },
    { name: 'Jun', value: 270000, target: 270000 },
  ];

  const allocationData = [
    { name: 'Large Cap Equity', value: 108000, percentage: 40 },
    { name: 'Government Bonds', value: 67500, percentage: 25 },
    { name: 'Mid Cap Equity', value: 40500, percentage: 15 },
    { name: 'Gold', value: 27000, percentage: 10 },
    { name: 'Corporate Bonds', value: 27000, percentage: 10 },
  ];

  const monthlyFlowData = [
    { name: 'Jan', income: 80000, expenses: 45000, savings: 35000 },
    { name: 'Feb', income: 80000, expenses: 48000, savings: 32000 },
    { name: 'Mar', income: 85000, expenses: 47000, savings: 38000 },
    { name: 'Apr', income: 80000, expenses: 44000, savings: 36000 },
    { name: 'May', income: 80000, expenses: 46000, savings: 34000 },
    { name: 'Jun', income: 90000, expenses: 45000, savings: 45000 },
  ];

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const [portfolio, health] = await Promise.all([
        ApiService.getPortfolioAllocation(userProfile),
        ApiService.getHealthScore(userProfile)
      ]);
      
      setPortfolioData(portfolio);
      // setBudgetData(budget); // ApiService.optimizeBudget missing
      setHealthScore(health);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast({
        title: "Synchronization Warning",
        description: "Operating in high-availability offline mode.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const topMetrics = [
    {
      title: "Total Wealth",
      value: 270000,
      change: 8.2,
      trend: 'up' as const,
      icon: <TrendingUp className="w-5 h-5" />,
      prefix: "₹",
      gradient: "from-blue-500/20 to-cyan-500/20",
      iconBg: "bg-blue-500"
    },
    {
      title: "Monthly Returns",
      value: "12.5",
      change: 2.1,
      trend: 'up' as const,
      icon: <DollarSign className="w-5 h-5" />,
      suffix: "%",
      gradient: "from-emerald-500/20 to-teal-500/20",
      iconBg: "bg-emerald-500"
    },
    {
      title: "Emergency Fund",
      value: 4.2,
      change: 0.3,
      trend: 'up' as const,
      icon: <PiggyBank className="w-5 h-5" />,
      suffix: " mths",
      gradient: "from-amber-500/20 to-orange-500/20",
      iconBg: "bg-amber-500"
    },
    {
      title: "Goal Progress",
      value: "68",
      change: 5.0,
      trend: 'up' as const,
      icon: <Target className="w-5 h-5" />,
      suffix: "%",
      gradient: "from-purple-500/20 to-pink-500/20",
      iconBg: "bg-purple-500"
    }
  ] as Array<{
    title: string;
    value: any;
    change: number;
    trend: 'up' | 'down';
    icon: React.ReactNode;
    prefix?: string;
    suffix?: string;
    gradient: string;
    iconBg: string;
  }>;

  const recentAlerts = [
    {
      type: "opportunity",
      title: "Rebalancing Opportunity",
      description: "Your portfolio has drifted 6% from target allocation",
      action: "Fix Calibration",
      priority: "high",
      timestamp: "2h ago"
    },
    {
      type: "achievement",
      title: "Goal Milestone Reached",
      description: "Emergency fund target of ₹75,000 achieved!",
      action: "Set New Target",
      priority: "low",
      timestamp: "1d ago"
    },
    {
      type: "market",
      title: "Neural Market Update",
      description: "Large cap funds showing strong performance this quarter",
      action: "Optimize",
      priority: "medium",
      timestamp: "3d ago"
    }
  ];

  const quickActions = [
    { label: "Add Capital", icon: Plus, action: () => {} },
    { label: "SIP Engine", icon: Calendar, action: () => {} },
    { label: "Tax Wizard", icon: AlertTriangle, action: () => {} },
    { label: "Goal Monitor", icon: Target, action: () => {} },
  ];

  if (isLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
        <div className="text-center space-y-6 relative z-10">
          <RefreshCw className="w-16 h-16 animate-spin mx-auto text-primary/40" />
          <div className="space-y-2">
            <h3 className="text-2xl font-black tracking-tight text-foreground/80">Calibrating Analytics</h3>
            <p className="text-muted-foreground animate-pulse text-sm">Processing multi-source financial streams...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-12 relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[140px] -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[120px] translate-y-1/2 -translate-x-1/2" />

      <div className="container mx-auto p-4 md:p-8 space-y-10 relative z-10 max-w-7xl">
        {/* Superior Header */}
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-end gap-6 pb-6 border-b border-border/40">
          <div className="space-y-3">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 w-fit"
            >
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-600">Enhanced Logic v2.4</span>
            </motion.div>
            <motion.h1 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-4xl md:text-6xl font-black tracking-tighter"
            >
              System <span className="text-gradient">Intelligence</span>
            </motion.h1>
            <p className="text-muted-foreground text-sm font-medium flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Synced: {new Date().toLocaleDateString('en-IN', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
          
          <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto">
            <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-xl backdrop-blur-sm border border-border/40">
              {['1M', '3M', '6M', '1Y', 'ALL'].map((period) => (
                <button
                  key={period}
                  onClick={() => setTimeframe(period as any)}
                  className={`px-4 py-1.5 rounded-lg text-[10px] font-black tracking-widest transition-all ${
                    timeframe === period 
                      ? 'bg-primary text-primary-foreground shadow-lg' 
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {period}
                </button>
              ))}
            </div>
            
            <div className="flex items-center gap-2 flex-1 md:flex-none">
              <Button 
                variant="outline" 
                size="lg" 
                className="h-12 rounded-xl group relative overflow-hidden bg-primary text-primary-foreground border-none shadow-xl shadow-primary/20"
                onClick={() => window.location.href = '/voice'}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
                <Mic className="mr-3 h-5 w-5" />
                <span className="font-bold">Command Bot</span>
              </Button>
              <Button 
                variant="outline" 
                size="icon" 
                className="h-12 w-12 rounded-xl border-border/60 hover:bg-muted/40 transition-all"
                onClick={fetchDashboardData}
              >
                <RefreshCw className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          </div>
        </div>

        {/* Real-time Metric Layer */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {topMetrics.map((metric, index) => (
            <motion.div
              key={metric.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -5 }}
              className="group"
            >
              <Card className="h-full relative overflow-hidden border-border/50 bg-card/40 backdrop-blur-xl group-hover:border-primary/30 transition-all duration-500 shadow-sm hover:shadow-xl hover:shadow-primary/5">
                <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${metric.gradient} blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:opacity-100 transition-opacity opacity-50`} />
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60">{metric.title}</span>
                  <div className={`p-2.5 ${metric.iconBg} rounded-xl text-white shadow-lg transition-transform group-hover:scale-110`}>
                    {metric.icon}
                  </div>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="text-3xl font-black tracking-tighter">
                    {metric.prefix}{metric.value}{metric.suffix}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[11px] font-black tracking-tight ${metric.trend === 'up' ? 'text-success' : 'text-error'}`}>
                      {metric.trend === 'up' ? '+' : '-'}{metric.change}%
                    </span>
                    <span className="text-[10px] font-bold text-muted-foreground/30 uppercase tracking-widest">Calibrated</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Cognitive Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <motion.div
            className="lg:col-span-2"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="border-none bg-card shadow-xl overflow-hidden group h-full">
              <div className="p-6 border-b border-border/40 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-black tracking-tight">Growth Projection</h3>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-black tracking-tighter">₹{(portfolioPerformanceData[portfolioPerformanceData.length-1].value).toLocaleString()}</span>
                    <Badge variant="outline" className="text-[10px] font-black border-none bg-emerald-500/10 text-emerald-500">+12.5%</Badge>
                  </div>
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest mt-1">Portfolio delta over 6 months</p>
                </div>
                <div className="p-2.5 bg-primary/10 rounded-xl text-primary shadow-lg shadow-primary/5">
                  <TrendingUp className="w-6 h-6" />
                </div>
              </div>
              <div className="p-8">
                <AdvancedLineChart
                  data={portfolioPerformanceData}
                  title=""
                  description=""
                  valuePrefix="₹"
                  showTarget={true}
                  showTrend={true}
                  height={320}
                  noCard
                />
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="h-full border-none bg-card shadow-xl overflow-hidden">
              <div className="p-6 border-b border-border/40">
                <h3 className="text-lg font-black tracking-tight">Structural Allocation</h3>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-black tracking-tighter">₹2,70,000</span>
                  <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">Total Assets</span>
                </div>
              </div>
              <div className="p-8 flex flex-col justify-center h-full">
                <AdvancedPieChart
                  data={allocationData}
                  title=""
                  description=""
                  valuePrefix="₹"
                  showPercentages={true}
                  showLegend={true}
                  height={320}
                  noCard
                />
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Functional Integration Layer */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="border-border/50 bg-card/40 backdrop-blur-xl relative overflow-hidden h-full">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-600">
                    <PiggyBank className="w-5 h-5" />
                  </div>
                  Savings DNA
                </CardTitle>
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Historical retention trends</p>
              </CardHeader>
              <CardContent className="p-6">
                <AdvancedLineChart
                  data={monthlyFlowData.map(item => ({ 
                    name: item.name, 
                    value: item.savings,
                    target: 40000 
                  }))}
                  title=""
                  description=""
                  valuePrefix="₹"
                  showTarget={true}
                  color="hsl(var(--chart-2))"
                  height={250}
                  noCard
                />
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card className="glass-effect h-full border-border/50 bg-card/40 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    <Target className="w-5 h-5" />
                  </div>
                  Action Parameters
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="grid grid-cols-2 gap-4">
                  {quickActions.map((action, index) => (
                    <Button
                      key={action.label}
                      variant="outline"
                      className="h-auto p-4 flex flex-col items-center justify-center gap-3 rounded-2xl bg-muted/20 border-border/40 hover:bg-primary/5 hover:border-primary/30 transition-all group"
                      onClick={action.action}
                    >
                      <div className="p-3 bg-card rounded-xl shadow-sm group-hover:scale-110 transition-transform">
                        <action.icon className="h-5 w-5 text-primary" />
                      </div>
                      <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground group-hover:text-primary transition-colors">{action.label}</span>
                    </Button>
                  ))}
                </div>

                <div className="space-y-4">
                  <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60 px-1">Neural Insights</h4>
                  <div className="grid grid-cols-1 gap-3">
                    <div className="p-4 bg-emerald-500/5 rounded-2xl border border-emerald-500/10 flex items-start gap-4 group/insight">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 animate-pulse" />
                      <div>
                        <p className="text-xs font-bold text-foreground group-hover:text-emerald-600 transition-colors">Efficiency Boost 🎉</p>
                        <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">Savings rate improved by <span className="text-emerald-500 font-bold">15.4%</span> this quarter. Maintain current trajectory.</p>
                      </div>
                    </div>
                    <div className="p-4 bg-primary/5 rounded-2xl border border-primary/10 flex items-start gap-4 group/insight">
                      <div className="w-2 h-2 rounded-full bg-primary mt-1.5 animate-pulse" />
                      <div>
                        <p className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">Retirement Calibration 💡</p>
                        <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">Increasing SIP by <span className="text-primary font-bold">₹2,000</span> will reduce FIRE age by 18 months.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Information Architecture (Tabs) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Tabs defaultValue="activity" className="w-full">
            <TabsList className="w-full h-14 bg-muted/30 p-1.5 rounded-2xl backdrop-blur-xl border border-border/40 grid grid-cols-3">
              <TabsTrigger value="activity" className="rounded-xl font-black text-[10px] uppercase tracking-[0.2em] data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg transition-all">Event Log</TabsTrigger>
              <TabsTrigger value="alerts" className="rounded-xl font-black text-[10px] uppercase tracking-[0.2em] data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg transition-all">Alert Stack</TabsTrigger>
              <TabsTrigger value="insights" className="rounded-xl font-black text-[10px] uppercase tracking-[0.2em] data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg transition-all">Neural Core</TabsTrigger>
            </TabsList>

            <TabsContent value="activity" className="mt-8">
              <Card className="border-border/50 bg-card/20 backdrop-blur-xl">
                <CardHeader>
                  <CardTitle className="text-lg font-black tracking-tighter">Verified Transactions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[
                      { type: 'SIP', desc: 'Tech Alpha Large Cap', amount: '+₹5,000', time: '2h ago', status: 'success' },
                      { type: 'EXP', desc: 'Hardware Acquisition', amount: '-₹1,200', time: '1d ago', status: 'expense' },
                      { type: 'DIV', desc: 'HDFC Global Equity', amount: '+₹850', time: '3d ago', status: 'income' },
                      { type: 'MLT', desc: 'Vault Threshold Reached', amount: '₹75,000', time: '1w ago', status: 'milestone' }
                    ].map((activity, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-muted/10 border border-transparent hover:border-primary/20 hover:bg-primary/5 rounded-2xl transition-all duration-300 group">
                        <div className="flex items-center gap-4">
                          <div className={`
                            w-12 h-12 flex items-center justify-center rounded-xl font-black text-[9px] tracking-tighter shadow-sm
                            ${activity.status === 'success' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' :
                              activity.status === 'expense' ? 'bg-rose-500/10 text-rose-500 border border-rose-500/20' :
                              activity.status === 'income' ? 'bg-primary/10 text-primary border border-primary/20' : 
                              'bg-amber-500/10 text-amber-500 border border-amber-500/20'}
                          `}>
                            {activity.type}
                          </div>
                          <div>
                            <p className="text-sm font-bold tracking-tight">{activity.desc}</p>
                            <p className="text-[10px] font-black uppercase text-muted-foreground/50 tracking-widest mt-0.5">{activity.time} • Local Node Synchronized</p>
                          </div>
                        </div>
                        <span className={`text-sm font-black tracking-tighter ${
                          activity.amount.includes('+') ? 'text-emerald-500' :
                          activity.amount.includes('-') ? 'text-rose-500' : 'text-foreground'
                        }`}>
                          {activity.amount}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="alerts" className="mt-8">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {recentAlerts.map((alert, index) => (
                  <Card key={index} className="border-border/50 bg-card/20 backdrop-blur-xl group hover:border-primary/30 transition-all">
                    <CardHeader className="pb-4">
                      <div className="flex justify-between items-start mb-2">
                        <Badge variant="outline" className={`text-[8px] font-black uppercase tracking-widest ${
                          alert.priority === 'high' ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' : 
                          alert.priority === 'medium' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 
                          'bg-primary/10 text-primary border-primary/20'
                        }`}>
                          Priority: {alert.priority}
                        </Badge>
                        <span className="text-[9px] font-black text-muted-foreground/40">{alert.timestamp}</span>
                      </div>
                      <CardTitle className="text-base font-black tracking-tight">{alert.title}</CardTitle>
                      <p className="text-xs text-muted-foreground leading-relaxed mt-1">{alert.description}</p>
                    </CardHeader>
                    <CardContent>
                      <Button variant="outline" className="w-full h-10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-primary hover:text-primary-foreground border-border/40 transition-all">
                        {alert.action}
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="insights" className="mt-8">
              <Card className="border-border/50 bg-card/20 backdrop-blur-xl overflow-hidden relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,rgba(var(--primary),0.05),transparent)] pointer-events-none" />
                <CardHeader>
                  <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                    <Brain className="w-5 h-5 text-primary" />
                    Neural Strategy Core
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 pb-8">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="p-6 bg-gradient-to-br from-primary/10 to-transparent border border-primary/20 rounded-2xl group hover:shadow-xl hover:shadow-primary/5 transition-all">
                      <h4 className="text-xs font-black uppercase tracking-widest text-primary mb-3">Investment Logic</h4>
                      <p className="text-sm text-foreground/80 leading-relaxed mb-6 font-medium">
                        Based on your risk profile, we recommend shifting 5% capital into mid-cap volatility segments to optimize CAGR by ~2.4%.
                      </p>
                      <Button variant="outline" className="h-10 rounded-xl px-6 text-[10px] font-black uppercase tracking-widest">Execute Strategy</Button>
                    </div>
                    <div className="p-6 bg-gradient-to-br from-secondary/10 to-transparent border border-secondary/20 rounded-2xl group hover:shadow-xl hover:shadow-secondary/5 transition-all">
                      <h4 className="text-xs font-black uppercase tracking-widest text-secondary mb-3">Tax Optimization</h4>
                      <p className="text-sm text-foreground/80 leading-relaxed mb-6 font-medium">
                        Unrealized tax potential detected: ₹46,800. deploying ₹1.5L in ELSS segments will calibrate your liability to zero.
                      </p>
                      <Button variant="outline" className="h-10 rounded-xl px-6 text-[10px] font-black uppercase tracking-widest">View Report</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
};

export default EnhancedDashboard;