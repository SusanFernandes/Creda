import React, { useState, useEffect } from 'react';
import { Shield, Users, Activity, Loader2, BarChart3, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiService } from '@/services/api';

const Admin: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, a, u] = await Promise.all([ApiService.adminStats(), ApiService.adminActivity(), ApiService.adminUsers()]);
      setStats(s);
      setActivity(Array.isArray(a) ? a : a?.activities || []);
      setUsers(Array.isArray(u) ? u : u?.users || []);
    } catch { /* offline */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex justify-between items-start border-b border-slate-200 dark:border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Admin Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">Platform-wide statistics and user management.</p>
          </div>
          <Button variant="outline" onClick={load} disabled={loading} className="rounded-xl">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />Refresh
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            {/* Stats Cards */}
            {stats && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: 'Total Users', value: stats.total_users ?? '—', icon: Users },
                  { label: 'Active Today', value: stats.active_today ?? '—', icon: Activity },
                  { label: 'Conversations', value: stats.total_conversations ?? '—', icon: BarChart3 },
                  { label: 'Portfolios', value: stats.total_portfolios ?? '—', icon: Shield },
                ].map(s => (
                  <Card key={s.label}>
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-muted-foreground">{s.label}</span>
                        <s.icon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="text-2xl font-bold">{typeof s.value === 'number' ? s.value.toLocaleString() : s.value}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            <Tabs defaultValue="activity">
              <TabsList className="rounded-xl">
                <TabsTrigger value="activity">Recent Activity</TabsTrigger>
                <TabsTrigger value="users">Users</TabsTrigger>
              </TabsList>

              <TabsContent value="activity" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    {activity.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-8">No recent activity.</p>
                    ) : (
                      <div className="divide-y">
                        {activity.slice(0, 20).map((a: any, i: number) => (
                          <div key={i} className="p-4 flex items-center justify-between">
                            <div>
                              <div className="text-sm font-medium">{a.action || a.event_type || 'Activity'}</div>
                              <div className="text-xs text-muted-foreground">{a.user_id || 'system'} · {a.timestamp || a.created_at || ''}</div>
                            </div>
                            {a.details && <Badge variant="outline" className="text-xs">{a.details}</Badge>}
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="users" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    {users.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-8">No users found.</p>
                    ) : (
                      <div className="divide-y">
                        {users.map((u: any, i: number) => (
                          <div key={i} className="p-4 flex items-center justify-between">
                            <div>
                              <div className="text-sm font-medium">{u.name || u.email || `User ${i + 1}`}</div>
                              <div className="text-xs text-muted-foreground">{u.email || u.user_id || ''}</div>
                            </div>
                            <Badge variant={u.is_active !== false ? 'default' : 'secondary'}>{u.is_active !== false ? 'Active' : 'Inactive'}</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </div>
  );
};

export default Admin;
