import React, { useState, useEffect } from 'react';
import { Bell, Loader2, CheckCheck, Trash2, Info, AlertCircle, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const Notifications: React.FC = () => {
  const [nudges, setNudges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    setLoading(true);
    try { const res = await ApiService.getPendingNudges(); setNudges(Array.isArray(res) ? res : res?.nudges || []); }
    catch { /* offline */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const markRead = async (id: string) => {
    try { await ApiService.markNudgeRead(id); setNudges(prev => prev.filter(n => n.id !== id)); }
    catch { /* handle */ }
  };

  const markAllRead = async () => {
    try { await ApiService.markAllNudgesRead(); setNudges([]); }
    catch { /* handle */ }
  };

  const generate = async () => {
    setGenerating(true);
    try { await ApiService.generateNudges(); await load(); }
    catch { /* handle */ }
    finally { setGenerating(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="flex justify-between items-start border-b border-slate-200 dark:border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Notifications</h1>
            <p className="text-sm text-muted-foreground mt-1">AI-generated nudges and financial reminders.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={generate} disabled={generating} className="rounded-xl">
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Sparkles className="w-4 h-4 mr-2" />Generate</>}
            </Button>
            {nudges.length > 0 && (
              <Button variant="outline" onClick={markAllRead} className="rounded-xl">
                <CheckCheck className="w-4 h-4 mr-2" />Mark All Read
              </Button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
        ) : nudges.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <Bell className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-1">All caught up!</h3>
              <p className="text-sm text-muted-foreground">No pending notifications. Click "Generate" to get fresh AI nudges.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {nudges.map((n: any) => (
              <Card key={n.id} className="hover:shadow-sm transition-shadow">
                <CardContent className="p-4 flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${
                    n.priority === 'high' ? 'bg-red-100 dark:bg-red-900/30' :
                    n.priority === 'medium' ? 'bg-yellow-100 dark:bg-yellow-900/30' :
                    'bg-blue-100 dark:bg-blue-900/30'
                  }`}>
                    {n.priority === 'high' ? <AlertCircle className="w-4 h-4 text-red-600" /> : <Info className="w-4 h-4 text-blue-600" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {n.category && <Badge variant="secondary" className="text-[10px]">{n.category}</Badge>}
                      {n.priority && <Badge variant={n.priority === 'high' ? 'destructive' : 'outline'} className="text-[10px]">{n.priority}</Badge>}
                    </div>
                    <p className="text-sm">{n.message || n.text || n.content || 'Notification'}</p>
                    {n.created_at && <p className="text-xs text-muted-foreground mt-1">{new Date(n.created_at).toLocaleDateString()}</p>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => markRead(n.id)}>
                    <CheckCheck className="w-4 h-4" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Notifications;
