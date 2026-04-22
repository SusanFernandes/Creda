import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  PieChart, 
  Wallet, 
  Brain, 
  Mic, 
  Settings, 
  HelpCircle,
  TrendingUp,
  Target,
  BarChart3,
  CreditCard,
  Shield,
  Bell,
  Flame,
  Calculator,
  Receipt,
  Heart,
} from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const mainNavItems = [
  { 
    title: 'Dashboard', 
    url: '/dashboard', 
    icon: LayoutDashboard,
    badge: '4'
  },
  { 
    title: 'Portfolio', 
    url: '/portfolio', 
    icon: PieChart,
    badge: 'New'
  },
  { 
    title: 'Budget', 
    url: '/budget', 
    icon: Wallet
  },
  { 
    title: 'Expenses', 
    url: '/expense-analytics', 
    icon: CreditCard
  },
  { 
    title: 'Goals', 
    url: '/goals', 
    icon: Target
  },
  { 
    title: 'Health Score', 
    url: '/health', 
    icon: Shield,
    badge: 'B+'
  },
];

const planningNavItems = [
  { title: 'FIRE Planner',     url: '/fire-planner',    icon: Flame,      badge: 'New' },
  { title: 'SIP Calculator',  url: '/sip-calculator',  icon: Calculator                },
  { title: 'Tax Wizard',      url: '/tax-wizard',      icon: Receipt,    badge: 'New' },
  { title: 'Couples Planner', url: '/couples-planner', icon: Heart                     },
];

const toolsNavItems = [
  { 
    title: 'Voice Assistant', 
    url: '/voice', 
    icon: Mic,
    badge: 'AI'
  },
  { 
    title: 'Knowledge Hub', 
    url: '/knowledge', 
    icon: Brain
  },
  { 
    title: 'Advisory', 
    url: '/advisory', 
    icon: HelpCircle
  },
];

const settingsNavItems = [
  { 
    title: 'Settings', 
    url: '/settings', 
    icon: Settings
  },
  { 
    title: 'Security', 
    url: '/security', 
    icon: Shield
  },
  { 
    title: 'Help', 
    url: '/help', 
    icon: HelpCircle
  },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const location = useLocation();
  const currentPath = location.pathname;
  const collapsed = state === 'collapsed';

  const isActive = (path: string) => currentPath === path;
  
  const getNavClassName = ({ isActive }: { isActive: boolean }) => 
    `flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300 group ${
      isActive 
        ? 'bg-primary/10 text-primary font-semibold shadow-[0_0_15px_rgba(var(--primary),0.1)]' 
        : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
    }`;

  return (
    <Sidebar 
      className={`border-r border-border/50 transition-all duration-500 ease-in-out ${collapsed ? "w-20" : "w-72"}`}
      collapsible="icon"
    >
      <SidebarHeader className="p-6">
        {!collapsed && (
          <div className="flex items-center gap-4 group cursor-pointer">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary-variant rounded-xl flex items-center justify-center shadow-lg group-hover:shadow-primary/30 transition-shadow duration-300">
                <TrendingUp className="w-6 h-6 text-primary-foreground" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-secondary rounded-full border-2 border-background animate-pulse" />
            </div>
            <div className="flex flex-col">
              <h2 className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                Creda
              </h2>
              <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground/60">
                AI Finance Hub
              </span>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary-variant rounded-xl flex items-center justify-center mx-auto shadow-lg hover:shadow-primary/30 transition-all duration-300">
            <TrendingUp className="w-6 h-6 text-primary-foreground" />
          </div>
        )}
      </SidebarHeader>

      <SidebarContent className="px-3 py-4">
        <SidebarGroup>
          <SidebarGroupLabel className={`px-4 text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-2 ${collapsed ? 'sr-only' : ''}`}>
            Main Terminal
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {mainNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild size="lg" className="h-11">
                    <NavLink to={item.url} className={getNavClassName}>
                      {({ isActive }) => (
                        <>
                          <div className={`relative flex items-center justify-center ${collapsed ? 'w-full' : ''}`}>
                            <item.icon className={`h-5 w-5 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                            {isActive && !collapsed && (
                              <div className="absolute -left-3 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_10px_rgba(var(--primary),0.5)]" />
                            )}
                          </div>
                          {!collapsed && (
                            <div className="flex items-center justify-between flex-1">
                              <span className="text-sm tracking-wide">{item.title}</span>
                              {item.badge && (
                                <Badge 
                                  variant="secondary"
                                  className={`text-[10px] font-bold px-1.5 h-5 min-w-[20px] justify-center transition-all duration-300 ${
                                    isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted/50 text-muted-foreground/70'
                                  }`}
                                >
                                  {item.badge}
                                </Badge>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className={`px-4 text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-2 mt-4 ${collapsed ? 'sr-only' : ''}`}>
            Wealth Planning
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {planningNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild size="lg" className="h-11">
                    <NavLink to={item.url} className={getNavClassName}>
                      {({ isActive }) => (
                        <>
                          <div className={`relative flex items-center justify-center ${collapsed ? 'w-full' : ''}`}>
                            <item.icon className={`h-5 w-5 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                            {isActive && !collapsed && (
                              <div className="absolute -left-3 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_10px_rgba(var(--primary),0.5)]" />
                            )}
                          </div>
                          {!collapsed && (
                            <div className="flex items-center justify-between flex-1">
                              <span className="text-sm tracking-wide">{item.title}</span>
                              {'badge' in item && item.badge && (
                                <Badge
                                  variant="secondary"
                                  className={`text-[10px] font-bold px-1.5 h-5 min-w-[20px] justify-center transition-all duration-300 ${
                                    isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted/50 text-muted-foreground/70'
                                  }`}
                                >
                                  {item.badge}
                                </Badge>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className={`px-4 text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-2 mt-4 ${collapsed ? 'sr-only' : ''}`}>
            Intelligent Tools
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {toolsNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild size="lg" className="h-11">
                    <NavLink to={item.url} className={getNavClassName}>
                      {({ isActive }) => (
                        <>
                          <div className={`relative flex items-center justify-center ${collapsed ? 'w-full' : ''}`}>
                            <item.icon className={`h-5 w-5 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                            {isActive && !collapsed && (
                              <div className="absolute -left-3 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_10px_rgba(var(--primary),0.5)]" />
                            )}
                          </div>
                          {!collapsed && (
                            <div className="flex items-center justify-between flex-1">
                              <span className="text-sm tracking-wide">{item.title}</span>
                              {item.badge && (
                                <Badge 
                                  variant="secondary"
                                  className={`text-[10px] font-bold px-1.5 h-5 min-w-[20px] justify-center transition-all duration-300 ${
                                    isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted/50 text-muted-foreground/70'
                                  }`}
                                >
                                  {item.badge}
                                </Badge>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className={`px-4 text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-2 mt-4 ${collapsed ? 'sr-only' : ''}`}>
            System
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {settingsNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild size="lg" className="h-11">
                    <NavLink to={item.url} className={getNavClassName}>
                      {({ isActive }) => (
                        <>
                          <div className={`relative flex items-center justify-center ${collapsed ? 'w-full' : ''}`}>
                            <item.icon className={`h-5 w-5 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                            {isActive && !collapsed && (
                              <div className="absolute -left-3 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_10px_rgba(var(--primary),0.5)]" />
                            )}
                          </div>
                          {!collapsed && <span className="text-sm tracking-wide">{item.title}</span>}
                        </>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-6 border-t border-border/40">
        {!collapsed && (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-gradient-to-br from-muted/50 to-muted/20 border border-border/50 relative overflow-hidden group/card shadow-sm">
              <div className="absolute top-0 right-0 p-3 opacity-10 group-hover/card:scale-110 transition-transform duration-500">
                <Brain className="h-12 w-12 text-primary" />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 bg-accent/20 rounded-lg">
                  <Bell className="h-3.5 w-3.5 text-accent" />
                </div>
                <span className="text-xs font-bold uppercase tracking-wider text-foreground/80">Pro Tips</span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                Say <span className="text-primary font-medium">"Hey Creda"</span> to activate voice commands and manage assets instantly!
              </p>
              <div className="mt-3 flex items-center gap-2">
                <div className="h-1 flex-1 bg-muted rounded-full overflow-hidden">
                  <div className="h-full w-2/3 bg-gradient-to-r from-primary to-primary-glow rounded-full" />
                </div>
                <span className="text-[10px] font-bold text-muted-foreground/60">65%</span>
              </div>
            </div>
            
            <Button size="lg" className="w-full h-12 bg-primary hover:bg-primary-dark text-primary-foreground shadow-lg shadow-primary/20 transition-all duration-300 rounded-xl group overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
              <Mic className="h-4 w-4 mr-2" />
              <span className="font-semibold tracking-wide">Voice Assistant</span>
            </Button>
          </div>
        )}
        {collapsed && (
          <div className="flex flex-col gap-4 items-center">
            <Button variant="ghost" size="icon" className="w-12 h-12 rounded-xl text-primary hover:bg-primary/10 transition-all duration-300 shadow-sm border border-border/40">
              <Mic className="h-5 w-5" />
            </Button>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

export default AppSidebar;