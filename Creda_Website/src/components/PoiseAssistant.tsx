import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Loader2, Sparkles, X, BrainCircuit, Command, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type PoiseState = 'idle' | 'listening' | 'thinking' | 'responding';

export function PoiseAssistant() {
  const [state, setState] = useState<PoiseState>('idle');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const navigate = useNavigate();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const commands = [
    { text: 'Open the dashboard', response: 'Accessing your financial overview.', path: '/dashboard' },
    { text: 'Check my portfolio', response: 'Retrieving latest performance data.', path: '/portfolio' },
    { text: 'Analyze my budget', response: 'Calculating spending trends.', path: '/budget' },
    { text: 'Check my financial health', response: 'Assessing your resilience score.', path: '/health' },
    { text: 'Check my goals', response: 'Loading your strategic milestones.', path: '/goals' }
  ];

  const startInteraction = () => {
    if (state !== 'idle') return;
    const command = commands[Math.floor(Math.random() * commands.length)];
    setState('listening');
    setTranscript('Listening...');
    timerRef.current = setTimeout(() => {
      setState('thinking');
      setTranscript(command.text);
      timerRef.current = setTimeout(() => {
        setState('responding');
        setResponse(command.response);
        timerRef.current = setTimeout(() => {
          navigate(command.path);
          setState('idle');
          setTranscript('');
          setResponse('');
        }, 2200);
      }, 1500);
    }, 2000);
  };

  const cancelInteraction = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (timerRef.current) clearTimeout(timerRef.current);
    setState('idle');
    setTranscript('');
    setResponse('');
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div className="fixed bottom-10 right-10 flex flex-col items-end gap-5 z-[100]">
      <AnimatePresence mode="wait">
        {state !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 15, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 15, scale: 0.98 }}
            className="w-[340px] bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-[2rem] p-6 shadow-2xl overflow-hidden ring-1 ring-black/5"
          >
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-400">System Intelligence</span>
              </div>
              <button 
                onClick={cancelInteraction} 
                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
              >
                <X className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

            <div className="space-y-6">
              {state === 'listening' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-1.5 h-8">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <motion.div
                        key={i}
                        animate={{ height: [8, 24, 8] }}
                        transition={{ duration: 1, repeat: Infinity, delay: i * 0.1 }}
                        className="w-1 bg-blue-500/40 rounded-full"
                      />
                    ))}
                  </div>
                  <p className="text-slate-900 dark:text-white text-base font-medium text-center">{transcript}</p>
                </div>
              )}

              {state === 'thinking' && (
                <div className="space-y-4">
                   <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 dark:bg-slate-800/30 rounded-2xl border border-slate-100 dark:border-slate-800">
                    <Command className="w-3.5 h-3.5 text-blue-500" />
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">"{transcript}"</p>
                  </div>
                  <div className="flex items-center gap-2 justify-center">
                    <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
                    <span className="text-[9px] font-bold text-blue-500 uppercase tracking-widest">Processing</span>
                  </div>
                </div>
              )}

              {state === 'responding' && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-5"
                >
                  <div className="bg-blue-500/5 p-4 rounded-2xl border border-blue-500/10">
                    <p className="text-slate-900 dark:text-white font-medium text-base leading-relaxed">
                      {response}
                    </p>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-blue-500 opacity-50">
                    <span className="text-[9px] font-bold uppercase tracking-widest">Redirecting</span>
                    <ArrowRight className="w-3 h-3" />
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={startInteraction}
        className={cn(
          'relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300',
          'shadow-xl border border-slate-200 dark:border-slate-800',
          state === 'idle' 
            ? 'bg-white dark:bg-slate-900 hover:shadow-blue-500/10' 
            : 'bg-slate-900 dark:bg-white'
        )}
      >
        <AnimatePresence mode="wait">
          {state === 'idle' ? (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              <Sparkles className="text-blue-500 w-5 h-5" />
            </motion.div>
          ) : (
            <motion.div
              key="active"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              {state === 'listening' ? (
                <Mic className="text-white dark:text-slate-900 w-5 h-5" />
              ) : (
                <Loader2 className="text-white dark:text-slate-900 w-5 h-5 animate-spin" />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}
