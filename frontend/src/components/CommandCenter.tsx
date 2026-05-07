import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Activity, Search, LogOut, Clock, User as UserIcon,
  Lock, Loader2, FileSearch, List, RefreshCw, TrendingUp,
  TrendingDown, AlertTriangle, CheckCircle2, Server,
  Upload, Wifi, Zap, Terminal, Brain, Cpu, Globe, Database
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from './ui/GlassCard';
import { NeonButton } from './ui/NeonButton';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Toaster, toast } from 'sonner';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import AICommandTerminal from './AICommandTerminal';

const API_Base = import.meta.env.VITE_API_URL || '/api';

interface StatsData {
  total_scans: number;
  completed_scans: number;
  failed_scans: number;
  compliance_score: number;
  active_risks: number;
  total_findings: number;
}

export default function CommandCenter() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsData>({
    total_scans: 128,
    completed_scans: 124,
    failed_scans: 4,
    compliance_score: 94,
    active_risks: 12,
    total_findings: 452
  });
  const [loading, setLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <div className="min-h-screen bg-cyber-navy text-slate-50 p-6 font-sans selection:bg-cyber-cyan/30">
      <Toaster position="top-right" theme="dark" />
      
      {/* Background Animated Mesh */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyber-cyan/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyber-purple/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-[1600px] mx-auto space-y-8 relative z-10"
      >
        {/* Header HUD */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/10 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Shield className="w-8 h-8 text-cyber-cyan animate-glow-pulse" />
              <h1 className="text-3xl font-black tracking-tighter uppercase italic">
                RALPH <span className="text-cyber-cyan">LOOP</span> v2.0
              </h1>
            </div>
            <p className="text-slate-400 text-sm font-mono tracking-widest flex items-center gap-2">
              <Activity className="w-3 h-3 text-emerald-500" /> SYSTEM ONLINE // {currentTime.toLocaleTimeString()}
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden lg:flex gap-6 mr-6 border-r border-white/10 pr-6">
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-tighter text-slate-500 font-bold">AI Node Alpha</p>
                <p className="text-xs font-mono text-cyber-cyan">ACTIVE // 12ms LATENCY</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-tighter text-slate-500 font-bold">Compliance Sync</p>
                <p className="text-xs font-mono text-emerald-500">OPTIMAL // 94%</p>
              </div>
            </div>
            <NeonButton variant="outline" size="sm" className="gap-2">
              <RefreshCw className="w-4 h-4" /> REFRESH
            </NeonButton>
            <NeonButton variant="purple" size="sm" className="gap-2">
              <LogOut className="w-4 h-4" /> DISCONNECT
            </NeonButton>
          </div>
        </header>

        {/* Top Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <motion.div variants={itemVariants}>
            <GlassCard className="group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-cyber-cyan/10 rounded-lg group-hover:bg-cyber-cyan/20 transition-colors">
                  <Globe className="w-6 h-6 text-cyber-cyan" />
                </div>
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/20">+12%</Badge>
              </div>
              <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">Total Scans</p>
              <h3 className="text-3xl font-bold mt-1 text-white">{stats.total_scans}</h3>
            </GlassCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <GlassCard className="group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-cyber-purple/10 rounded-lg group-hover:bg-cyber-purple/20 transition-colors">
                  <AlertTriangle className="w-6 h-6 text-cyber-purple" />
                </div>
                <Badge className="bg-red-500/20 text-red-400 border-red-500/20">HIGH RISK</Badge>
              </div>
              <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">Active Risks</p>
              <h3 className="text-3xl font-bold mt-1 text-white">{stats.active_risks}</h3>
            </GlassCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <GlassCard className="group border-cyber-cyan/30">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-cyber-cyan/10 rounded-lg">
                  <CheckCircle2 className="w-6 h-6 text-cyber-cyan" />
                </div>
              </div>
              <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">Compliance Score</p>
              <h3 className="text-3xl font-bold mt-1 text-cyber-cyan">{stats.compliance_score}%</h3>
              <Progress value={stats.compliance_score} className="h-1 mt-4 bg-white/5" indicatorClassName="bg-cyber-cyan neon-glow-cyan" />
            </GlassCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <GlassCard className="group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-slate-500/10 rounded-lg">
                  <Terminal className="w-6 h-6 text-slate-400" />
                </div>
              </div>
              <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">Total Findings</p>
              <h3 className="text-3xl font-bold mt-1 text-white">{stats.total_findings}</h3>
            </GlassCard>
          </motion.div>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* 3D Visualization Placeholder & Chart */}
          <motion.div variants={itemVariants} className="lg:col-span-8 space-y-6">
            <GlassCard className="h-[450px] flex flex-col justify-center items-center relative overflow-hidden group perspective-1000">
              {/* 3D Scene Background Gradient */}
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyber-blue/20 via-transparent to-transparent opacity-50" />
              
              {/* Animated 3D Grid */}
              <div className="absolute inset-0 opacity-20 pointer-events-none origin-center rotate-x-[45deg]" 
                   style={{ 
                     backgroundImage: 'linear-gradient(to right, #3D5AFE 2px, transparent 1px), linear-gradient(to bottom, #3D5AFE 2px, transparent 1px)', 
                     backgroundSize: '60px 60px',
                     transform: 'perspective(1000px) rotateX(60deg) translateY(-100px) translateZ(-100px)'
                   }} />

              {/* Floating 3D Node Representation */}
              <div className="relative group-hover:scale-110 transition-transform duration-700">
                 <div className="absolute inset-0 bg-cyber-cyan/20 blur-3xl rounded-full animate-pulse" />
                 <Cpu className="w-32 h-32 text-cyber-cyan/40 animate-float relative z-10 filter drop-shadow-[0_0_20px_rgba(0,242,255,0.8)]" />
                 <Shield className="absolute top-0 right-0 w-12 h-12 text-cyber-purple animate-ping opacity-50" />
              </div>

              <div className="text-center z-10 mt-12">
                <h3 className="text-2xl font-black text-white uppercase tracking-[0.2em] italic">3D CORE TOPOLOGY</h3>
                <div className="flex gap-2 justify-center mt-2">
                   <span className="h-1 w-8 bg-cyber-cyan rounded-full animate-pulse" />
                   <span className="h-1 w-8 bg-cyber-purple rounded-full animate-pulse" style={{ animationDelay: '0.3s' }} />
                </div>
                <p className="text-slate-500 text-[10px] font-mono mt-4 uppercase tracking-[0.3em] font-bold">[ ANALYZING TRAFFIC // SECURITY SCAN ACTIVE ]</p>
              </div>
              
              <div className="absolute bottom-6 left-6 right-6 flex justify-between items-end">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-cyber-cyan rounded-full animate-ping" />
                  <div className="w-2 h-2 bg-cyber-purple rounded-full animate-ping" style={{ animationDelay: '0.5s' }} />
                  <div className="w-2 h-2 bg-cyber-blue rounded-full animate-ping" style={{ animationDelay: '1s' }} />
                </div>
                <div className="flex gap-4">
                   <div className="text-right">
                      <p className="text-[10px] text-slate-500 uppercase font-bold">Packets processed</p>
                      <p className="text-xs font-mono text-white">1.2M / SEC</p>
                   </div>
                   <div className="text-right">
                      <p className="text-[10px] text-slate-500 uppercase font-bold">Threat level</p>
                      <p className="text-xs font-mono text-red-400">NOMINAL</p>
                   </div>
                </div>
              </div>
            </GlassCard>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <GlassCard className="h-[250px]">
                  <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyber-cyan" /> Scan Frequency (Last 7 Days)
                  </h3>
                  <div className="h-[150px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={[
                        { name: 'Mon', value: 12 },
                        { name: 'Tue', value: 18 },
                        { name: 'Wed', value: 15 },
                        { name: 'Thu', value: 25 },
                        { name: 'Fri', value: 20 },
                        { name: 'Sat', value: 10 },
                        { name: 'Sun', value: 30 },
                      ]}>
                        <defs>
                          <linearGradient id="colorCyan" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00F2FF" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#00F2FF" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <Area type="monotone" dataKey="value" stroke="#00F2FF" fillOpacity={1} fill="url(#colorCyan)" />
                        <XAxis dataKey="name" hide />
                        <YAxis hide />
                        <Tooltip 
                          contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                          itemStyle={{ color: '#00F2FF' }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
               </GlassCard>

               <GlassCard className="h-[250px]">
                  <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                    <Database className="w-4 h-4 text-cyber-purple" /> Database Health
                  </h3>
                  <div className="space-y-4">
                     <div>
                        <div className="flex justify-between text-xs mb-1">
                           <span className="text-slate-400">STORAGE UTILIZATION</span>
                           <span className="text-white">42%</span>
                        </div>
                        <Progress value={42} className="h-1 bg-white/5" indicatorClassName="bg-cyber-purple" />
                     </div>
                     <div>
                        <div className="flex justify-between text-xs mb-1">
                           <span className="text-slate-400">QUERY PERFORMANCE</span>
                           <span className="text-white">98%</span>
                        </div>
                        <Progress value={98} className="h-1 bg-white/5" indicatorClassName="bg-cyber-cyan" />
                     </div>
                     <div className="pt-2 flex gap-4">
                        <div className="flex-1 p-2 bg-white/5 rounded border border-white/5">
                           <p className="text-[10px] text-slate-500 uppercase">Uptime</p>
                           <p className="text-sm font-mono text-emerald-400">100.0%</p>
                        </div>
                        <div className="flex-1 p-2 bg-white/5 rounded border border-white/5">
                           <p className="text-[10px] text-slate-500 uppercase">Backup</p>
                           <p className="text-sm font-mono text-cyber-cyan">SYNCED</p>
                        </div>
                     </div>
                  </div>
               </GlassCard>
            </div>
          </motion.div>

          {/* Right Panel: Controls & Terminal */}
          <motion.div variants={itemVariants} className="lg:col-span-4 space-y-6">
            <GlassCard className="border-cyber-cyan/20">
              <h3 className="text-sm font-bold uppercase tracking-widest text-cyber-cyan mb-6 flex items-center gap-2">
                <Brain className="w-4 h-4" /> AI Orchestrator
              </h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Target Host / IP</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input 
                      type="text" 
                      placeholder="e.g. 192.168.1.1 or example.com"
                      className="w-full bg-white/5 border border-white/10 rounded-lg py-3 pl-10 pr-4 text-sm focus:outline-none focus:border-cyber-cyan transition-all placeholder:text-slate-600"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                   <NeonButton variant="outline" className="w-full text-[10px] font-bold tracking-widest uppercase">
                     Nmap Scan
                   </NeonButton>
                   <NeonButton variant="outline" className="w-full text-[10px] font-bold tracking-widest uppercase">
                     ZAP Audit
                   </NeonButton>
                </div>

                <NeonButton className="w-full py-6 text-sm font-black uppercase tracking-widest">
                  INITIATE FULL COMPLIANCE RUN
                </NeonButton>

                <div className="pt-4 border-t border-white/10">
                   <div className="flex items-center gap-2 text-xs text-slate-400 mb-4">
                     <Upload className="w-3 h-3" /> SharkTap PCAP Analysis
                   </div>
                   <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-cyber-purple/50 transition-colors cursor-pointer bg-cyber-purple/5">
                      <FileSearch className="w-8 h-8 text-cyber-purple mx-auto mb-2 opacity-50" />
                      <p className="text-xs text-slate-400 uppercase font-bold tracking-tighter">Drop capture file here</p>
                   </div>
                </div>
              </div>
            </GlassCard>

            <GlassCard className="p-0 overflow-hidden h-[400px] border-white/10">
               <div className="bg-white/5 px-4 py-2 border-b border-white/10 flex justify-between items-center">
                  <div className="flex items-center gap-2">
                     <Terminal className="w-3 h-3 text-cyber-cyan" />
                     <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Orchestrator Logs</span>
                  </div>
                  <div className="flex gap-1">
                     <div className="w-2 h-2 rounded-full bg-red-500/50" />
                     <div className="w-2 h-2 rounded-full bg-yellow-500/50" />
                     <div className="w-2 h-2 rounded-full bg-emerald-500/50" />
                  </div>
               </div>
               <div className="p-4 font-mono text-xs space-y-2 h-[calc(400px-33px)] overflow-y-auto bg-black/20">
                  <p className="text-slate-500">[08:24:12] INITIALIZING AI AGENTS...</p>
                  <p className="text-cyber-cyan">[08:24:13] NODE_ALPHA: ONLINE</p>
                  <p className="text-cyber-cyan">[08:24:13] NODE_BETA: ONLINE</p>
                  <p className="text-slate-500">[08:24:15] LOADING HIPAA RULES... DONE</p>
                  <p className="text-slate-500">[08:24:16] LOADING SOC2 CONTROLS... DONE</p>
                  <p className="text-emerald-400">[08:25:01] SYSTEM READY FOR COMMAND.</p>
                  <div className="animate-pulse inline-block w-2 h-4 bg-cyber-cyan ml-1 align-middle" />
               </div>
            </GlassCard>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
