'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, PieChart, Wallet, Brain, Mic, Settings, HelpCircle,
  TrendingUp, Target, BarChart3, CreditCard, Shield, Bell, Flame,
  Calculator, Receipt, Heart, MessageSquare, AlertTriangle, Globe,
  Fingerprint, Users, Search, CalendarHeart, ShieldCheck, Award, UserCog,
} from 'lucide-react';
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarHeader, SidebarFooter, useSidebar,
} from '@/components/ui/sidebar';
import { Badge } from '@/components/ui/badge';

const mainNavItems = [
  { title: 'Dashboard', url: '/dashboard', icon: LayoutDashboard },
  { title: 'Chat', url: '/chat', icon: MessageSquare, badge: 'AI' },
  { title: 'Portfolio', url: '/portfolio', icon: PieChart },
  { title: 'Budget', url: '/budget', icon: Wallet },
  { title: 'Expenses', url: '/expense-analytics', icon: CreditCard },
  { title: 'Goals', url: '/goals', icon: Target },
  { title: 'Health Score', url: '/health', icon: Shield },
];

const planningNavItems = [
  { title: 'FIRE Planner', url: '/fire-planner', icon: Flame },
  { title: 'SIP Calculator', url: '/sip-calculator', icon: Calculator },
  { title: 'Tax Wizard', url: '/tax-wizard', icon: Receipt },
  { title: 'Couples Planner', url: '/couples-planner', icon: Heart },
  { title: 'Stress Test', url: '/stress-test', icon: AlertTriangle },
  { title: 'Market Pulse', url: '/market-pulse', icon: Globe, badge: 'New' },
  { title: 'Personality', url: '/personality', icon: Fingerprint },
  { title: 'Social Proof', url: '/social-proof', icon: Users },
  { title: 'Life Events', url: '/life-events', icon: CalendarHeart },
];

const toolsNavItems = [
  { title: 'Voice Assistant', url: '/voice', icon: Mic, badge: 'AI' },
  { title: 'Research Hub', url: '/research', icon: Search },
  { title: 'Advisory', url: '/advisory', icon: HelpCircle },
  { title: 'Knowledge Hub', url: '/knowledge', icon: Brain },
  { title: 'Report Card', url: '/report-card', icon: Award },
  { title: 'Family', url: '/family', icon: Users },
  { title: 'Compliance', url: '/compliance', icon: ShieldCheck },
  { title: 'Notifications', url: '/notifications', icon: Bell },
];

const settingsNavItems = [
  { title: 'Settings', url: '/settings', icon: Settings },
  { title: 'Security', url: '/security', icon: Shield },
  { title: 'Admin', url: '/admin', icon: UserCog },
  { title: 'Help', url: '/help', icon: HelpCircle },
];

function NavGroup({ label, items, collapsed, currentPath }: { label: string; items: typeof mainNavItems; collapsed: boolean; currentPath: string }) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel className={`px-4 text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 mb-2 ${collapsed ? 'sr-only' : ''}`}>
        {label}
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu className="gap-1">
          {items.map((item) => {
            const active = currentPath === item.url;
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild size="lg" className="h-11">
                  <Link
                    href={item.url}
                    className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300 group ${
                      active
                        ? 'bg-primary/10 text-primary font-semibold shadow-[0_0_15px_rgba(var(--primary),0.1)]'
                        : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                    }`}
                  >
                    <div className={`relative flex items-center justify-center ${collapsed ? 'w-full' : ''}`}>
                      <item.icon className={`h-5 w-5 transition-transform duration-300 ${active ? 'scale-110' : 'group-hover:scale-110'}`} />
                      {active && !collapsed && (
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
                              active ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted/50 text-muted-foreground/70'
                            }`}
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                    )}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar() {
  const { state } = useSidebar();
  const pathname = usePathname();
  const collapsed = state === 'collapsed';

  return (
    <Sidebar
      className={`border-r border-border/50 transition-all duration-500 ease-in-out ${collapsed ? 'w-20' : 'w-72'}`}
      collapsible="icon"
    >
      <SidebarHeader className="p-6">
        {!collapsed ? (
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
        ) : (
          <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary-variant rounded-xl flex items-center justify-center mx-auto shadow-lg hover:shadow-primary/30 transition-all duration-300">
            <TrendingUp className="w-6 h-6 text-primary-foreground" />
          </div>
        )}
      </SidebarHeader>

      <SidebarContent className="px-3 py-4">
        <NavGroup label="Main Terminal" items={mainNavItems} collapsed={collapsed} currentPath={pathname} />
        <NavGroup label="Wealth Planning" items={planningNavItems} collapsed={collapsed} currentPath={pathname} />
        <NavGroup label="AI Tools" items={toolsNavItems} collapsed={collapsed} currentPath={pathname} />
        <NavGroup label="Settings" items={settingsNavItems} collapsed={collapsed} currentPath={pathname} />
      </SidebarContent>

      <SidebarFooter className="p-4">
        {!collapsed && (
          <div className="text-[10px] text-muted-foreground/50 text-center">
            Creda v3.0 &middot; AI Finance Hub
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

export default AppSidebar;
