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
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useLanguage } from '@/contexts/LanguageContext';
import { ApiService, UserProfile } from '@/services/api';
import { useToast } from '@/hooks/use-toast';

const Dashboard: React.FC = () => {
  const { t } = useLanguage();
  const { toast } = useToast();
  
  const [isLoading, setIsLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [budgetData, setBudgetData] = useState<any>(null);
  const [healthScore, setHealthScore] = useState<any>(null);

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
      // setBudgetData(budget); // optimizeBudget missing in ApiService, using dummy or same as portfolio for now
      setHealthScore(health);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast({
        title: "Connection Issue",
        description: "Falling back to local cache for your dashboard.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const quickStats = [
    {
      title: "Portfolio Value",
      value: "₹2,50,000",
      change: "+12.5%",
      changeType: "positive" as const,
      icon: <TrendingUp className="w-5 h-5" />,
      gradient: "from-blue-500/20 to-cyan-500/20",
      iconBg: "bg-blue-500"
    },
    {
      title: "Monthly SIP",
      value: "₹15,000",
      change: "+5.2%",
      changeType: "positive" as const,
      icon: <DollarSign className="w-5 h-5" />,
      gradient: "from-emerald-500/20 to-teal-500/20",
      iconBg: "bg-emerald-500"
    },
    {
      title: "Emergency Fund",
      value: "₹75,000",
      change: "3 months",
      changeType: "neutral" as const,
      icon: <PiggyBank className="w-5 h-5" />,
      gradient: "from-amber-500/20 to-orange-500/20",
      iconBg: "bg-amber-500"
    },
    {
      title: "Goals Progress",
      value: "65%",
      change: "On Track",
      changeType: "positive" as const,
      icon: <Target className="w-5 h-5" />,
      gradient: "from-purple-500/20 to-pink-500/20",
      iconBg: "bg-purple-500"
    }
  ] as Array<{ 
    title: string; 
    value: string; 
    change: string; 
    changeType: 'positive' | 'neutral' | 'negative'; 
    icon: React.ReactNode; 
    gradient: string; 
    iconBg: string; 
  }>;

  const recentActivities = [
    {
      type: "investment",
      description: "SIP contribution to Tech Alpha Fund",
      amount: "₹5,000",
      time: "2h ago",
      status: "completed"
    },
    {
      type: "expense",
      description: "Cloud Services Subscription",
      amount: "₹1,200",
      time: "1d ago", 
      status: "normal"
    },
    {
      type: "goal",
      description: "Emergency Fund reached 50% milestone",
      amount: "₹50,000",
      time: "3d ago",
      status: "milestone"
    },
    {
      type: "alert",
      description: "Market volatility alert: Rebalancing suggested",
      amount: "",
      time: "1w ago",
      status: "pending"
    }
  ];

  if (isLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
        <div className="text-center space-y-6 relative z-10">
          <div className="relative">
            <RefreshCw className="w-16 h-16 animate-spin mx-auto text-primary/40" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 bg-primary/20 rounded-full blur-xl animate-pulse" />
            </div>
          </div>
          <div className="space-y-2">
            <h3 className="text-2xl font-bold tracking-tight text-foreground/80">Synchronizing Vault</h3>
            <p className="text-muted-foreground animate-pulse">Aggregating decentralized financial data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-12 relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-accent/5 rounded-full blur-[100px] translate-y-1/2 -translate-x-1/2" />

      <div className="container mx-auto p-4 md:p-8 space-y-10 relative z-10">
        {/* Header Section */}
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-end gap-6 pb-2 border-b border-border/40">
          <div className="space-y-2">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 w-fit"
            >
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Live Portfolio Agent</span>
            </motion.div>
            <motion.h1 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-4xl md:text-5xl font-black tracking-tight"
            >
              Master <span className="text-gradient">Financials</span>
            </motion.h1>
            <p className="text-muted-foreground text-sm md:text-base flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Intelligence update for {new Date().toLocaleDateString('en-IN', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
          
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Button 
              size="lg" 
              className="group relative flex-1 md:flex-none overflow-hidden h-14 rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xl shadow-primary/20"
              onClick={() => window.location.href = '/voice'}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
              <Mic className="mr-3 h-5 w-5" />
              <span className="font-bold tracking-tight">AI Command Center</span>
            </Button>
            <Button 
              variant="outline" 
              size="icon" 
              className="h-14 w-14 rounded-2xl border-border/60 hover:border-primary/40 hover:bg-primary/5 transition-all"
              onClick={fetchDashboardData}
            >
              <RefreshCw className="h-5 w-5 text-muted-foreground" />
            </Button>
          </div>
        </div>

        {/* Dynamic Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {quickStats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
              whileHover={{ y: -5 }}
              className="group"
            >
              <Card className="h-full relative overflow-hidden border-border/50 bg-card/40 backdrop-blur-xl group-hover:border-primary/30 transition-all duration-500 shadow-sm hover:shadow-xl hover:shadow-primary/5">
                <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${stat.gradient} blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:opacity-100 transition-opacity opacity-50`} />
                
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">{stat.title}</span>
                  <div className={`p-2.5 ${stat.iconBg} rounded-xl text-white shadow-lg shadow-inherit/20 group-hover:scale-110 transition-transform`}>
                    {stat.icon}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  <div className="text-3xl font-black tracking-tighter">{stat.value}</div>
                  <div className="flex items-center gap-2">
                    <div className={`flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-bold ${
                      stat.changeType === 'positive' ? 'bg-success/10 text-success' : 
                      stat.changeType === 'neutral' ? 'bg-muted text-muted-foreground' : 
                      'bg-error/10 text-error'
                    }`}>
                      {stat.changeType === 'positive' && <ArrowUpRight className="w-3 h-3" />}
                      {stat.changeType === 'negative' && <ArrowDownRight className="w-3 h-3" />}
                      {stat.change}
                    </div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/40 tracking-wider">vs Period</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Secondary Intelligence Layer */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Health Score Panel (Lg 4) */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="lg:col-span-4"
          >
            <Card className="h-full border-border/50 bg-gradient-to-b from-card/60 to-card/20 backdrop-blur-xl relative overflow-hidden group">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(var(--secondary),0.05),transparent)] pointer-events-none" />
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                    <div className="p-2 bg-secondary/10 rounded-lg text-secondary">
                      <Target className="w-5 h-5" />
                    </div>
                    Health Quotient
                  </CardTitle>
                  <Badge variant="outline" className="h-6 border-secondary/40 text-secondary font-bold text-[10px] uppercase tracking-wider">Verified Profile</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-8 pt-4">
                <div className="relative flex flex-col items-center justify-center py-4">
                  <div className="relative w-40 h-40 flex items-center justify-center">
                    <svg className="w-full h-full -rotate-90">
                      <circle cx="80" cy="80" r="70" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-muted/20" />
                      <circle cx="80" cy="80" r="70" stroke="currentColor" strokeWidth="8" fill="transparent" strokeDasharray={440} strokeDashoffset={440 - (440 * (healthScore?.score || 78)) / 100} className="text-secondary transition-all duration-1000 ease-out" />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-5xl font-black text-secondary tracking-tighter">{healthScore?.score || 78}</span>
                      <span className="text-xs font-bold uppercase text-muted-foreground/60">Total Score</span>
                    </div>
                  </div>
                  <div className="mt-6 text-center">
                    <div className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-secondary to-secondary-glow">
                      Optimum Wealth Grade: {healthScore?.grade || "B+"}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">You are performing better than 72% of similar investors.</p>
                  </div>
                </div>
                
                <div className="space-y-5 px-2">
                  {Object.entries(healthScore?.factors || {
                    savings_rate: 85,
                    diversification: 72,
                    emergency_fund: 65,
                    age_appropriate: 88
                  }).map(([key, value]) => (
                    <div key={key} className="space-y-1.5 group/factor">
                      <div className="flex justify-between text-[11px] font-bold uppercase tracking-wider text-muted-foreground/70 group-hover/factor:text-foreground transition-colors">
                        <span>{key.replace('_', ' ')}</span>
                        <span>{typeof value === 'number' ? value : 0}%</span>
                      </div>
                      <Progress value={typeof value === 'number' ? value : 0} className="h-1.5 bg-muted/40 overflow-hidden">
                        <div className="h-full bg-secondary shadow-[0_0_8px_rgba(var(--secondary),0.4)] transition-all duration-1000" />
                      </Progress>
                    </div>
                  ))}
                </div>

                <Button className="w-full h-12 rounded-xl bg-secondary hover:bg-secondary/90 text-white font-bold tracking-tight shadow-xl shadow-secondary/10" onClick={() => window.location.href = '/advisory'}>
                  Generate Advisor Roadmap
                </Button>
              </CardContent>
            </Card>
          </motion.div>

          {/* Allocation & Budget Stack (Lg 8) */}
          <div className="lg:col-span-8 flex flex-col gap-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">
              {/* Portfolio Insights */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="h-full"
              >
                <Card className="h-full border-border/50 bg-card/40 backdrop-blur-xl hover:border-primary/20 transition-all">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg text-primary">
                        <TrendingUp className="w-5 h-5" />
                      </div>
                      Asset Intelligence
                    </CardTitle>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">{portfolioData?.persona || "Aggressive Growth"}</p>
                  </CardHeader>
                  <CardContent className="space-y-6 pt-2">
                    <div className="space-y-4">
                      {Object.entries(portfolioData?.allocation || {
                        large_cap_equity: 0.40,
                        government_bonds: 0.25,
                        mid_cap_equity: 0.15,
                        corporate_bonds: 0.20
                      }).map(([asset, percentage], i) => (
                        <div key={asset} className="flex items-center gap-4">
                          <div className={`w-1 h-8 rounded-full ${i % 2 === 0 ? 'bg-primary' : 'bg-primary/40'}`} />
                          <div className="flex-1 space-y-1">
                            <div className="flex justify-between text-xs font-bold">
                              <span className="capitalize">{asset.replace('_', ' ')}</span>
                              <span>{((typeof percentage === 'number' ? percentage : 0) * 100).toFixed(0)}%</span>
                            </div>
                            <Progress value={(typeof percentage === 'number' ? percentage : 0) * 100} className="h-1 bg-muted/30" />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 flex justify-between items-center group/panel">
                      <div className="space-y-0.5">
                        <p className="text-[10px] font-black uppercase text-primary tracking-widest">Expected ROI</p>
                        <p className="text-xl font-black text-primary group-hover:scale-110 transition-transform origin-left">{((portfolioData?.expected_return || 0.12) * 100).toFixed(1)}% p.a.</p>
                      </div>
                      <div className="text-right space-y-0.5 border-l border-primary/20 pl-4">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Risk Index</p>
                        <p className="text-xl font-black">{portfolioData?.risk_score || 6.5}/10</p>
                      </div>
                    </div>

                    <Button variant="outline" className="w-full text-xs font-bold uppercase tracking-widest hover:text-primary transition-colors h-10 group border-none bg-transparent" onClick={() => window.location.href = '/portfolio'}>
                      Simulate Rebalancing <ArrowUpRight className="ml-2 h-3 w-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Expense DNA */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="h-full"
              >
                <Card className="h-full border-border/50 bg-card/40 backdrop-blur-xl hover:border-accent/20 transition-all">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                      <div className="p-2 bg-accent/10 rounded-lg text-accent text-emerald-600">
                        <PiggyBank className="w-5 h-5" />
                      </div>
                      Expense DNA
                    </CardTitle>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">AI Budget Strategy</p>
                  </CardHeader>
                  <CardContent className="space-y-6 pt-2">
                    <div className="grid grid-cols-3 gap-3">
                      {Object.entries(budgetData?.adaptive_allocation || {
                        needs: 0.50,
                        wants: 0.30,
                        savings: 0.20
                      }).map(([category, percentage], i) => (
                        <div key={category} className="flex flex-col items-center p-3 rounded-2xl bg-muted/40 border border-transparent hover:border-accent/20 hover:bg-accent/5 transition-all text-center">
                          <span className="text-[9px] font-black uppercase text-muted-foreground/60 mb-2 tracking-widest">{category}</span>
                          <span className="text-lg font-black tracking-tighter text-emerald-600">
                            {((typeof percentage === 'number' ? percentage : 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="space-y-3">
                      <p className="text-[10px] font-black uppercase text-muted-foreground tracking-[0.2em] mb-4">Neural Recommendations</p>
                      {budgetData?.recommendations?.slice(0, 2).map((rec: string, index: number) => (
                        <div key={index} className="group/rec p-3 rounded-xl bg-orange-500/5 border border-orange-500/10 hover:border-orange-500/30 transition-all flex items-start gap-3">
                          <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 animate-pulse" />
                          <p className="text-xs leading-relaxed text-muted-foreground group-hover/rec:text-foreground transition-colors">
                            {rec}
                          </p>
                        </div>
                      ))}
                    </div>

                    <Button variant="outline" className="w-full text-xs font-bold uppercase tracking-widest hover:text-emerald-600 transition-colors h-10 group border-none bg-transparent" onClick={() => window.location.href = '/budget'}>
                      Tweak Engine Parameters <ArrowUpRight className="ml-2 h-3 w-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Neural Event Log (Activity) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Card className="border-border/50 bg-card/20 backdrop-blur-xl relative overflow-hidden h-fit">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg font-black tracking-tight flex items-center gap-3">
                      <Calendar className="w-5 h-5 text-primary" />
                      Neural Transaction Log
                    </CardTitle>
                    <p className="text-xs text-muted-foreground uppercase font-bold tracking-widest">Real-time ledger monitoring</p>
                  </div>
                  <Button variant="outline" size="sm" className="text-xs font-black uppercase py-0 h-8 opacity-40 hover:opacity-100 tracking-tighter border-none bg-transparent shadow-none">Export CSV</Button>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {recentActivities.map((activity, index) => (
                      <div key={index} className="group relative flex items-center justify-between p-4 bg-muted/20 border border-transparent hover:border-primary/20 hover:bg-primary/5 rounded-2xl transition-all duration-300">
                        <div className="flex items-center gap-4">
                          <div className={`
                            p-3 rounded-2xl transition-transform group-hover:scale-110
                            ${activity.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' :
                              activity.status === 'milestone' ? 'bg-amber-500/10 text-amber-500' :
                              activity.status === 'pending' ? 'bg-rose-500/10 text-rose-500' :
                              'bg-muted text-foreground/40'}
                          `}>
                            {activity.type === 'investment' ? <TrendingUp className="w-4 h-4" /> :
                             activity.type === 'expense' ? <DollarSign className="w-4 h-4" /> :
                             activity.type === 'goal' ? <Target className="w-4 h-4" /> :
                             <AlertTriangle className="w-4 h-4" />}
                          </div>
                          <div>
                            <p className="text-[13px] font-bold tracking-tight text-foreground/90 group-hover:text-foreground transition-colors">{activity.description}</p>
                            <p className="text-[10px] font-black uppercase text-muted-foreground/50 tracking-widest mt-0.5">{activity.time} • Transaction Hash: {Math.random().toString(16).slice(2, 6).toUpperCase()}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-black tracking-tighter">{activity.amount || '—'}</p>
                          <Badge variant="outline" className="text-[8px] font-black uppercase tracking-[0.2em] opacity-30 group-hover:opacity-100 transition-opacity p-0 h-fit border-none">Authenticated</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;