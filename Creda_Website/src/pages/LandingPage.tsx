import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Link } from 'react-router-dom';
import { 
  ArrowRight, 
  CheckCircle, 
  Zap, 
  Brain, 
  Shield, 
  BarChart4, 
  Globe, 
  Cpu, 
  LayoutDashboard,
  Sparkles,
  ChevronRight,
  Mic,
  ArrowUpRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import ReliableVoiceAssistant from '@/components/ReliableVoiceAssistant';
import LandingNavbar from '@/components/layout/LandingNavbar';
import LandingFooter from '@/components/layout/LandingFooter';
import { cn } from '@/lib/utils';

const LandingPage: React.FC = () => {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, -100]);

  const features = [
    { icon: <Brain className="w-5 h-5" />, title: "Neural Portfolio Core", description: "Nobel Prize-winning Markowitz theory adapted for local markets. Get personalized strategies instantly.", stats: "0.1s Latency" },
    { icon: <Zap className="w-5 h-5" />, title: "Linguistic Intelligence", description: "Voice processing across 11+ Indian languages. Our AI understands every nuance of your dialect.", stats: "11+ Dialects" },
    { icon: <Shield className="w-5 h-5" />, title: "Regulatory Sentinel", description: "Cross-referenced with official RBI and SEBI guidelines for total governance and compliance.", stats: "100% Compliant" }
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 font-sans selection:bg-blue-600/10 transition-colors duration-500">
      <LandingNavbar />
      
      {/* Refined Hero */}
      <section className="relative min-h-[90vh] flex items-center justify-center pt-28 pb-20 px-6 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full max-w-7xl">
           <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-blue-100/50 dark:bg-blue-900/10 rounded-full blur-[140px] mix-blend-multiply dark:mix-blend-screen animate-pulse" />
           <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-slate-100 dark:bg-slate-800/10 rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 container mx-auto text-center max-w-5xl">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <Badge variant="outline" className="mb-10 px-5 py-2 rounded-full border-slate-200 dark:border-slate-800 font-bold uppercase tracking-[0.2em] text-[10px] bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl transition-all hover:bg-white dark:hover:bg-slate-800">
              <Sparkles className="w-3 h-3 mr-2" /> Financial Intelligence Matrix v4.2
            </Badge>
            
            <h1 className="text-6xl md:text-9xl font-bold tracking-tight text-slate-900 dark:text-slate-50 italic mb-10 leading-[0.9]">
              System <br/> <span className="text-blue-600 italic">Optimization</span>
            </h1>
            
            <p className="text-xl md:text-2xl text-slate-500 max-w-3xl mx-auto leading-relaxed mb-16 font-medium italic">
              Experience the core of financial logic. Nobel-prize winning mathematics integrated with neural linguistic processing.
            </p>

            <div className="flex flex-col sm:flex-row gap-8 justify-center items-center">
              <Button size="xl" className="h-16 px-12 rounded-2xl bg-slate-900 dark:bg-slate-50 text-white dark:text-slate-900 font-bold uppercase tracking-widest text-sm hover:opacity-90 transition-all shadow-xl shadow-slate-200 dark:shadow-none" asChild>
                <Link to="/auth/sign-up" className="flex items-center gap-3">
                  Initialize Core <ArrowRight className="w-5 h-5" />
                </Link>
              </Button>
              <Button size="xl" variant="outline" className="h-16 px-12 rounded-2xl border-slate-200 dark:border-slate-800 font-bold uppercase tracking-widest text-sm hover:bg-slate-50 dark:hover:bg-slate-900" asChild>
                <Link to="/voice">Execute Demo</Link>
              </Button>
            </div>

            <div className="mt-20 flex flex-wrap items-center justify-center gap-12 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
               <span className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-500 font-bold" /> SEBI Compliant</span>
               <span className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-500 font-bold" /> AES-256 Encrypted</span>
               <span className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-500 font-bold" /> Zero Mic Protocol</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Latency Metrics */}
      <section className="py-40 bg-slate-50/50 dark:bg-slate-900/30 px-6 border-y border-slate-100 dark:border-slate-800">
        <div className="container mx-auto max-w-7xl">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            <motion.div initial={{ opacity: 0, x: -30 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }}>
              <Badge className="mb-6 bg-blue-600 text-white uppercase font-bold tracking-widest italic h-7">Latency Threshold</Badge>
              <h2 className="text-4xl md:text-7xl font-bold tracking-tighter mb-10 italic uppercase font-black">Neural <br/>Performance</h2>
              <div className="space-y-16">
                {[
                  { label: "Execution Speed", value: "< 0.1s", desc: "Markowitz optimization core latency across 10,000 iterations." },
                  { label: "Sync Protocol", value: "Sub 2s", desc: "Multilingual transcription and intent mapping across dialects." },
                  { label: "Network Security", value: "Real-time", desc: "Continuous end-to-end cryptographic verification." },
                ].map((stat, i) => (
                  <div key={i} className="group border-l-2 border-slate-200 dark:border-slate-800 pl-10 hover:border-blue-600 transition-colors">
                     <div className="flex justify-between items-baseline mb-3">
                        <span className="text-lg font-bold tracking-tight uppercase italic text-slate-400">{stat.label}</span>
                        <span className="text-4xl font-bold tracking-tighter text-slate-900 dark:text-slate-50 italic">{stat.value}</span>
                     </div>
                     <p className="text-slate-500 text-sm font-medium italic">{stat.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.98 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} className="relative">
               <Card className="border-none bg-white dark:bg-slate-900 shadow-2xl rounded-[3rem] overflow-hidden group">
                  <div className="p-10 border-b border-slate-50 dark:border-slate-800 flex items-center justify-between">
                     <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center text-white">
                           <LayoutDashboard className="w-6 h-6" />
                        </div>
                        <span className="text-sm font-bold uppercase tracking-widest text-slate-500">Instance Node Stream</span>
                     </div>
                     <Badge variant="outline" className="text-emerald-500 border-emerald-500/20 bg-emerald-50 text-[10px] font-bold">ACTIVE</Badge>
                  </div>
                  <CardContent className="p-10 space-y-8">
                     <div className="space-y-3">
                        <div className="flex justify-between text-[11px] font-bold uppercase tracking-widest text-slate-400">
                           <span>Optimization Volume</span>
                           <span>82%</span>
                        </div>
                        <Progress value={82} className="h-2 bg-slate-100 dark:bg-slate-800" />
                     </div>
                     <div className="space-y-4 pt-6">
                        {[1, 2, 3].map(i => (
                          <div key={i} className="flex items-center justify-between p-5 bg-slate-50/50 dark:bg-slate-800/50 rounded-2xl border border-slate-200/50 dark:border-slate-800 group hover:border-blue-500/30 transition-all">
                             <div className="flex items-center gap-4">
                                <div className="w-2 h-2 rounded-full bg-blue-500 group-hover:scale-150 transition-transform" />
                                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 italic">Node {i * 14} deployed and verified</span>
                             </div>
                             <ArrowRight className="w-4 h-4 text-slate-300" />
                          </div>
                        ))}
                     </div>
                  </CardContent>
               </Card>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Feature Architecture */}
      <section className="py-40 px-6">
        <div className="container mx-auto max-w-7xl">
          <div className="text-center mb-28 space-y-4">
             <h2 className="text-5xl font-bold tracking-tighter text-slate-900 dark:text-slate-50 italic">System <span className="text-blue-600">Architecture</span></h2>
             <p className="text-slate-500 text-lg font-medium italic">Modular deconstruction of the optimization engine.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {features.map((feature, i) => (
              <Card key={i} className="border-none shadow-sm bg-white dark:bg-slate-900 p-10 rounded-[2.5rem] hover:shadow-xl transition-all duration-500 group border border-transparent hover:border-slate-100 dark:hover:border-slate-800">
                 <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-blue-600 mb-8 group-hover:bg-blue-600 group-hover:text-white transition-all duration-500">
                    {feature.icon}
                 </div>
                 <h3 className="text-2xl font-bold tracking-tight mb-4 text-slate-900 dark:text-slate-50 italic uppercase italic">{feature.title}</h3>
                 <p className="text-slate-500 font-medium leading-relaxed italic mb-8">{feature.description}</p>
                 <Badge variant="outline" className="text-[11px] font-bold text-slate-400 border-slate-200 dark:border-slate-800 uppercase tracking-widest">{feature.stats}</Badge>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* AI Simulation Gateway */}
      <section className="py-40 px-6 bg-slate-900 text-white relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-blue-500/10 blur-[150px]" />
        <div className="container mx-auto max-w-4xl relative z-10 flex flex-col items-center">
           <div className="text-center mb-20 space-y-5">
              <Badge className="bg-white/10 text-white backdrop-blur-xl border border-white/20 font-bold uppercase tracking-widest">Simulation Interface</Badge>
              <h2 className="text-4xl md:text-6xl font-black italic tracking-tighter">Gateway to <span className="text-blue-500 italic">Core Intelligence</span></h2>
              <p className="text-slate-400 font-medium italic text-lg">Initialize a neural handshake with the Poise AI engine.</p>
           </div>
           
           <div className="w-full bg-slate-950/40 p-16 rounded-[4rem] border border-white/5 backdrop-blur-2xl shadow-3xl">
              <ReliableVoiceAssistant isCompact={false} />
           </div>
        </div>
      </section>

      {/* Final Deployment CTA */}
      <section className="py-48 px-6 text-center">
         <div className="container mx-auto max-w-4xl">
            <h2 className="text-6xl md:text-9xl font-bold tracking-tighter mb-16 italic text-slate-900 dark:text-slate-50 leading-[0.85]">
               Initialize Your <br/><span className="text-blue-600 italic underline">Optimization.</span>
            </h2>
            <p className="text-2xl text-slate-500 font-medium mb-20 italic">
              Stop monitoring. Start scaling. Deploy the neural core today.
            </p>
            <div className="flex flex-col sm:flex-row gap-10 justify-center items-center">
              <Button size="xl" className="h-20 px-16 rounded-full bg-slate-900 dark:bg-slate-50 text-white dark:text-slate-900 font-bold uppercase tracking-widest text-base hover:scale-105 transition-all shadow-2xl shadow-slate-200 dark:shadow-none" asChild>
                 <Link to="/auth/sign-up">Deploy Nodes</Link>
              </Button>
              <Button size="xl" variant="ghost" className="h-20 px-16 rounded-full font-bold uppercase tracking-widest text-base group italic" asChild>
                 <Link to="/help" className="flex items-center gap-3">Technical Logs <ArrowUpRight className="w-6 h-6 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" /></Link>
              </Button>
            </div>
         </div>
      </section>
      
      <LandingFooter />
    </div>
  );
};

export default LandingPage;