import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  TrendingUp, 
  PieChart as PieIcon, 
  RotateCcw, 
  Target,
  AlertCircle,
  RefreshCw,
  Mic,
  Download,
  Settings,
  Brain
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useLanguage } from '@/contexts/LanguageContext';
import { ApiService, UserProfile } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { AdvancedPieChart } from '@/components/charts/AdvancedPieChart';

const Portfolio: React.FC = () => {
  const { t } = useLanguage();
  const { toast } = useToast();
  
  const [isLoading, setIsLoading] = useState(false);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [rebalanceData, setRebalanceData] = useState<any>(null);
  const [showOptimization, setShowOptimization] = useState(false);

  // Mock user profile
  const userProfile: UserProfile = {
    age: 32,
    income: 800000,
    savings: 250000,
    dependents: 1,
    risk_tolerance: 3,
    goal_type: "retirement",
    time_horizon: 25
  };

  const currentHoldingsMap = {
    large_cap_equity: 0.35,
    mid_cap_equity: 0.20,
    government_bonds: 0.25,
    corporate_bonds: 0.15,
    gold: 0.05
  };

  const currentHoldingsData = [
    { name: 'Large Cap Equity', value: 87500 },
    { name: 'Mid Cap Equity', value: 50000 },
    { name: 'Government Bonds', value: 62500 },
    { name: 'Corporate Bonds', value: 37500 },
    { name: 'Gold', value: 12500 }
  ];

  useEffect(() => {
    fetchPortfolioData();
    checkRebalancing();
  }, []);

  const fetchPortfolioData = async () => {
    setIsLoading(true);
    try {
      const portfolio = await ApiService.getPortfolioAllocation(userProfile);
      setPortfolioData(portfolio);
    } catch (error) {
      toast({
        title: "Portfolio Error",
        description: "Using offline data",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const checkRebalancing = async () => {
    try {
      const rebalance = await ApiService.checkRebalancing({
        profile: userProfile,
        current_allocation: currentHoldingsMap,
        threshold: 0.05
      });
      setRebalanceData(rebalance);
    } catch (error) {
      console.warn('Rebalancing check failed');
    }
  };

  const handleOptimize = async () => {
    setIsLoading(true);
    setShowOptimization(true);
    
    try {
      const optimizedPortfolio = await ApiService.portfolioOptimization({
        profile: userProfile,
        goals: ["retirement", "wealth_creation"],
        time_horizon_years: userProfile.time_horizon || 25
      });
      
      setPortfolioData(optimizedPortfolio);
      
      toast({
        title: "Portfolio Optimized! 🎯",
        description: "Your portfolio has been optimized using advanced AI algorithms."
      });
    } catch (error) {
      toast({
        title: "Optimization Error",
        description: "Please try again later",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceQuery = () => {
    toast({
      title: "Voice Assistant Activated",
      description: "Ask me anything about your portfolio!"
    });
  };

  const allocationComparison = Object.entries(portfolioData?.allocation || {}).map(([asset, recommended]) => {
    const current = currentHoldingsMap[asset as keyof typeof currentHoldingsMap] || 0;
    const recommendedVal = typeof recommended === 'number' ? recommended : 0;
    const difference = recommendedVal - current;
    
    return {
      asset,
      current,
      recommended: recommendedVal,
      difference,
      status: Math.abs(difference) > 0.05 ? 'rebalance' : 'good'
    };
  });

  const portfolioMetrics = [
    {
      label: "Expected Return",
      value: `${((portfolioData?.expected_return || 0.12) * 100).toFixed(1)}%`,
      trend: "up",
      description: "Annual expected return"
    },
    {
      label: "Risk Score", 
      value: `${portfolioData?.risk_score || 6.5}/10`,
      trend: "stable",
      description: "Portfolio volatility measure"
    },
    {
      label: "Diversification",
      value: "85%",
      trend: "up", 
      description: "Asset class spread"
    },
    {
      label: "Rebalancing Alert",
      value: rebalanceData?.needs_rebalancing ? "Yes" : "No",
      trend: rebalanceData?.needs_rebalancing ? "warning" : "good",
      description: "Portfolio drift analysis"
    }
  ];

  const recommendedData = portfolioData?.allocation ? Object.entries(portfolioData.allocation).map(([name, val]) => ({
    name: name.replace(/_/g, ' '),
    value: Math.floor((val as number) * 250000)
  })) : currentHoldingsData;

  return (
    <div className="container mx-auto p-6 lg:p-10 space-y-10 group/portfolio">
      {/* Header - Restored Original Layout */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 mb-1"
          >
            <div className="p-1.5 bg-primary/10 rounded-lg">
                <Brain className="w-4 h-4 text-primary" />
            </div>
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary/60">Portfolio Intelligence</span>
          </motion.div>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-4xl lg:text-5xl font-black tracking-tighter text-foreground"
          >
            Smart Portfolio <span className="text-muted-foreground/40">Manager</span> 📊
          </motion.h1>
          <p className="text-muted-foreground font-medium mt-2">
            AI-powered investment optimization using Markowitz theory
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="h-12 px-6 rounded-2xl border-none bg-card shadow-xl hover:bg-muted font-bold tracking-tight" onClick={handleVoiceQuery}>
            <Mic className="mr-2 w-4 h-4" /> Ask Creda
          </Button>
          <Button className="h-12 px-8 rounded-2xl bg-primary text-white shadow-xl shadow-primary/20 hover:scale-[1.02] transition-transform font-bold tracking-tight" onClick={fetchPortfolioData}>
            <RefreshCw className={`mr-2 w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* Rebalancing Alert - Restored Original Placement */}
      {rebalanceData?.needs_rebalancing && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Alert className="border-none bg-amber-500/10 p-6 rounded-[2rem] shadow-xl shadow-amber-500/5">
            <AlertCircle className="h-5 w-5 text-amber-500 mt-1" />
            <AlertDescription className="text-foreground ml-2">
              <strong className="font-black tracking-tight text-amber-500 uppercase text-xs">Rebalancing Recommended:</strong>
              <p className="mt-1 text-sm font-medium opacity-80">
                Your portfolio has drifted <span className="font-black">{rebalanceData.drift_percentage}%</span> from the target allocation.
                Consider rebalancing to maintain optimal risk-return profile.
              </p>
            </AlertDescription>
          </Alert>
        </motion.div>
      )}

      {/* Portfolio Metrics - Grid-4 Restored */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {portfolioMetrics.map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="border-none bg-card shadow-xl hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60">
                  {metric.label}
                </CardTitle>
                <div className={`p-1.5 rounded-lg ${
                  metric.trend === 'up' ? 'bg-emerald-500/10 text-emerald-500' : 
                  metric.trend === 'warning' ? 'bg-amber-500/10 text-amber-500' : 'bg-muted text-muted-foreground'
                }`}>
                  {metric.trend === 'up' ? <TrendingUp className="w-3.5 h-3.5" /> : 
                   metric.trend === 'warning' ? <AlertCircle className="w-3.5 h-3.5" /> : <PieIcon className="w-3.5 h-3.5" />}
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-black tracking-tighter">{metric.value}</div>
                <p className="text-[10px] font-bold text-muted-foreground/60 mt-2 uppercase tracking-widest">
                  {metric.description}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Tabs System - Restored Original Structure */}
      <Tabs defaultValue="allocation" className="w-full space-y-8">
        <TabsList className="bg-card shadow-xl p-1.5 h-16 rounded-[1.2rem] border-none grid w-full grid-cols-4 max-w-3xl mx-auto">
          <TabsTrigger value="allocation" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-sm lg:text-base transition-all">Current Allocation</TabsTrigger>
          <TabsTrigger value="optimization" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-sm lg:text-base transition-all">AI Optimization</TabsTrigger>
          <TabsTrigger value="rebalancing" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-sm lg:text-base transition-all">Rebalancing</TabsTrigger>
          <TabsTrigger value="performance" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-white data-[state=active]:shadow-lg font-bold tracking-tight text-sm lg:text-base transition-all">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="allocation" className="space-y-8 outline-none animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="border-none bg-card shadow-xl overflow-hidden">
              <CardHeader className="p-8 border-b border-border/40">
                <CardTitle className="flex items-center gap-3 text-xl font-black tracking-tight">
                  <div className="p-2 bg-primary/10 rounded-xl">
                    <PieIcon className="w-5 h-5 text-primary" />
                  </div>
                  Current Portfolio
                </CardTitle>
                <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Your actual global baseline holdings</CardDescription>
              </CardHeader>
              <CardContent className="p-8">
                <AdvancedPieChart
                  data={currentHoldingsData}
                  title=""
                  height={320}
                  noCard
                />
                <div className="pt-8 mt-4 border-t border-border/40 text-center">
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/40">
                    Total Portfolio Value: <span className="text-foreground text-sm tracking-tighter ml-1 font-black">₹2,50,000</span>
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-none bg-card shadow-xl overflow-hidden">
              <CardHeader className="p-8 border-b border-border/40">
                <CardTitle className="flex items-center gap-3 text-xl font-black tracking-tight text-emerald-500">
                  <div className="p-2 bg-emerald-500/10 rounded-xl">
                    <Target className="w-5 h-5 text-emerald-500" />
                  </div>
                  Recommended Allocation
                </CardTitle>
                <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">
                  AI-optimized for your {portfolioData?.persona || "Aggressive Growth"} profile
                </CardDescription>
              </CardHeader>
              <CardContent className="p-8">
                <AdvancedPieChart
                  data={recommendedData}
                  title=""
                  height={320}
                  noCard
                />
                <div className="pt-8 mt-4 border-t border-border/40 grid grid-cols-2 gap-4">
                  <div className="flex flex-col items-center">
                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Expected ROI</span>
                    <span className="text-lg font-black tracking-tighter text-emerald-500">
                      {((portfolioData?.expected_return || 0.12) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Risk Score</span>
                    <span className="text-lg font-black tracking-tighter">{portfolioData?.risk_score || 6.5}/10</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="optimization" className="space-y-6 outline-none animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="border-none bg-card shadow-xl overflow-hidden">
            <CardHeader className="p-8">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-3 text-xl font-black tracking-tight">
                    <TrendingUp className="w-6 h-6 text-primary" />
                    Portfolio Optimization Engine
                  </CardTitle>
                  <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">
                    Advanced AI using Markowitz Modern Portfolio Theory
                  </CardDescription>
                </div>
                <Badge className="bg-primary/10 text-primary border-none font-black text-[10px] tracking-widest uppercase py-1">Optimized Execution</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-8 pt-0 space-y-10">
              <div className="text-center space-y-6">
                <div className="p-10 bg-muted/20 border border-border/40 rounded-[2.5rem] relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-8 opacity-5">
                    <Brain className="w-32 h-32" />
                  </div>
                  <h3 className="text-3xl font-black tracking-tighter mb-4 relative z-10 transition-transform group-hover:scale-[1.01]">
                    Nobel Prize-Winning Mathematics
                  </h3>
                  <p className="text-muted-foreground font-medium max-w-2xl mx-auto text-lg leading-relaxed relative z-10">
                    Our AI implements Harry Markowitz's Modern Portfolio Theory, 
                    adapted for Indian markets with real-time data from NSE, BSE, and bond markets.
                  </p>
                </div>
                
                <Button 
                   onClick={handleOptimize}
                  disabled={isLoading}
                   className="h-16 px-12 rounded-2xl bg-primary text-white shadow-2xl shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all font-black text-xl tracking-tighter mx-auto flex"
                >
                  {isLoading ? (
                    <RefreshCw className="mr-3 w-6 h-6 animate-spin" />
                  ) : (
                    <TrendingUp className="mr-3 w-6 h-6" />
                  )}
                  Optimize Portfolio with AI
                </Button>
              </div>

              {showOptimization && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-8 p-8 bg-emerald-500/10 rounded-[2rem] border border-emerald-500/20"
                >
                  <h4 className="font-black text-emerald-500 uppercase text-[10px] tracking-[0.3em] mb-6 text-center">Optimization Matrix Calibrated</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="text-center space-y-1">
                      <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Expected Improvement</p>
                      <p className="text-3xl font-black tracking-tighter text-emerald-500">+2.3%</p>
                    </div>
                    <div className="text-center space-y-1">
                      <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Risk Reduction</p>
                      <p className="text-3xl font-black tracking-tighter text-emerald-500">-15%</p>
                    </div>
                    <div className="text-center space-y-1">
                      <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Processing Time</p>
                      <p className="text-3xl font-black tracking-tighter text-primary">0.08s</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rebalancing" className="space-y-6 outline-none animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="border-none bg-card shadow-xl overflow-hidden">
            <CardHeader className="p-8 border-b border-border/40">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-3 text-xl font-black tracking-tight">
                    <RotateCcw className="w-6 h-6 text-amber-500" />
                    Portfolio Rebalancing Analysis
                  </CardTitle>
                  <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">
                    Compare current vs recommended allocations
                  </CardDescription>
                </div>
                <Badge variant="outline" className="border-amber-500/20 text-amber-500 bg-amber-500/5 font-black text-[10px] tracking-widest px-3 py-1">DRIFT DETECTED</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {allocationComparison.map((item) => (
                    <div key={item.asset} className={`p-6 rounded-3xl border ${item.status === 'rebalance' ? 'bg-amber-500/5 border-amber-500/20' : 'bg-muted/10 border-border/10'} space-y-4`}>
                      <div className="flex justify-between items-center">
                        <span className="capitalize font-black text-sm tracking-tight text-foreground/80">
                          {item.asset.replace('_', ' ')}
                        </span>
                        <Badge className={`${item.status === 'rebalance' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'} border-none font-black text-[9px] px-2 py-0.5`}>
                          {item.status === 'rebalance' ? 'REBALANCE' : 'TARGET'}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Current</p>
                          <p className="font-black text-lg tracking-tighter">{(item.current * 100).toFixed(1)}%</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Target</p>
                          <p className="font-black text-lg tracking-tighter">{(item.recommended * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                      <div className="pt-3 border-t border-border/20 flex justify-between items-center">
                        <div className="text-[10px] font-black uppercase tracking-widest opacity-40">Delta</div>
                        <div className={`text-xl font-black tracking-tighter ${item.difference > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {item.difference > 0 ? '+' : ''}{(item.difference * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="pt-8 mt-4 border-t border-border/40 flex flex-col items-center">
                  <Button className="h-16 px-16 rounded-[1.2rem] bg-primary text-white shadow-2xl shadow-primary/20 hover:scale-[1.02] transition-all font-black text-xl tracking-tighter">
                    <RotateCcw className="mr-3 w-6 h-6" />
                    Execute Sync Logic
                  </Button>
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 mt-4">
                    Estimated transaction cost: <span className="text-foreground">₹250</span> | Tax impact: <span className="text-foreground">MINIMAL</span>
                  </p>
                </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-8 outline-none animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="border-none bg-card shadow-xl overflow-hidden h-full">
              <CardHeader className="p-8">
                <CardTitle className="text-xl font-black tracking-tight">Systemic Performance</CardTitle>
                <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Holistic risk-adjusted metrics</CardDescription>
              </CardHeader>
              <CardContent className="px-8 pb-8 space-y-8">
                <div className="grid grid-cols-2 gap-6">
                  <div className="text-center p-6 bg-emerald-500/5 rounded-[2rem] border border-emerald-500/10">
                    <p className="text-4xl font-black tracking-tighter text-emerald-500">+12.5%</p>
                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 mt-1">YTD Return</p>
                  </div>
                  <div className="text-center p-6 bg-primary/5 rounded-[2rem] border border-primary/10">
                    <p className="text-4xl font-black tracking-tighter text-primary">+8.7%</p>
                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 mt-1">3Y CAGR</p>
                  </div>
                </div>
                
                <div className="space-y-4 pt-4">
                  {[
                    { label: 'Sharpe Ratio', val: '1.24', sub: 'High Stability', color: 'text-foreground' },
                    { label: 'Max Drawdown', val: '-8.5%', sub: 'Sector Aligned', color: 'text-rose-500' },
                    { label: 'Alpha vs Index', val: '+2.1%', sub: 'Outperforming', color: 'text-emerald-500' },
                    { label: 'System Beta', val: '0.89', sub: 'Conservative', color: 'text-foreground' },
                  ].map(item => (
                    <div key={item.label} className="flex justify-between items-end py-3 border-b border-border/20 last:border-none group hover:px-2 transition-all">
                      <div className="space-y-0.5">
                        <span className="text-xs font-black tracking-tight text-foreground/80">{item.label}</span>
                        <div className="text-[9px] font-black text-muted-foreground/40 uppercase tracking-widest">{item.sub}</div>
                      </div>
                      <span className={`text-xl font-black tracking-tighter ${item.color}`}>{item.val}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="border-none bg-card shadow-xl overflow-hidden h-full">
              <CardHeader className="p-8 border-b border-border/40">
                <CardTitle className="text-xl font-black tracking-tight">Benchmark Calibrations</CardTitle>
                <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Comparative market intelligence</CardDescription>
              </CardHeader>
              <CardContent className="p-8 space-y-10">
                <div className="space-y-8">
                  {[
                    { name: 'Your Neural Portfolio', val: 75, badge: '+12.5%', color: 'bg-primary' },
                    { name: 'NSE Nifty 50', val: 61, badge: '+10.2%', color: 'bg-muted' },
                    { name: 'NSE Nifty 500', val: 71, badge: '+11.8%', color: 'bg-muted' },
                  ].map(item => (
                    <div key={item.name} className="space-y-3 group">
                      <div className="flex justify-between items-center px-1">
                        <span className="text-xs font-black tracking-tight text-foreground/80">{item.name}</span>
                        <Badge variant="outline" className={`font-black tracking-widest text-[10px] border-none px-3 ${item.color === 'bg-primary' ? 'bg-primary/10 text-primary' : 'bg-muted/50 text-muted-foreground'}`}>
                            {item.badge}
                        </Badge>
                      </div>
                      <div className="h-2.5 bg-muted/30 rounded-full overflow-hidden p-[2px]">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${item.val}%` }}
                          transition={{ duration: 1, delay: 0.5 }}
                          className={`h-full rounded-full ${item.color}`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="pt-8 border-t border-border/40 bg-emerald-500/5 -mx-8 -mb-8 p-8 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-black tracking-tight text-emerald-500">Benchmark Outperformance</p>
                    <p className="text-xs font-medium text-emerald-500/60">Portfolio exhibits +2.3% alpha vs primary index</p>
                  </div>
                  <div className="p-3 bg-emerald-500/10 rounded-2xl text-emerald-500">
                    <TrendingUp className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Portfolio;