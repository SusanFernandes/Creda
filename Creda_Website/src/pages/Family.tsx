import React, { useState, useEffect } from 'react';
import { Users, Loader2, UserPlus, Unlink, Check, Heart, Mail } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ApiService } from '@/services/api';

const Family: React.FC = () => {
  const [members, setMembers] = useState<any[]>([]);
  const [wealth, setWealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [relationship, setRelationship] = useState('spouse');
  const [linking, setLinking] = useState(false);
  const [wealthLoading, setWealthLoading] = useState(false);

  const loadMembers = async () => {
    try { const res = await ApiService.getFamilyMembers(); setMembers(Array.isArray(res) ? res : res?.members || []); }
    catch { /* offline */ }
    finally { setLoading(false); }
  };

  useEffect(() => { loadMembers(); }, []);

  const linkMember = async () => {
    if (!email.trim()) return;
    setLinking(true);
    try { await ApiService.linkFamily({ member_email: email, relationship_type: relationship }); setEmail(''); await loadMembers(); }
    catch { /* handle */ }
    finally { setLinking(false); }
  };

  const unlinkMember = async (linkId: string) => {
    try { await ApiService.unlinkFamily(linkId); await loadMembers(); }
    catch { /* handle */ }
  };

  const loadWealth = async () => {
    setWealthLoading(true);
    try { setWealth(await ApiService.familyWealth()); }
    catch { setWealth(null); }
    finally { setWealthLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Family Finance</h1>
          <p className="text-sm text-muted-foreground mt-1">Link family members and get combined financial insights.</p>
        </div>

        {/* Link Member */}
        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center gap-2"><UserPlus className="w-5 h-5" />Link Family Member</CardTitle></CardHeader>
          <CardContent className="flex flex-col sm:flex-row gap-3">
            <Input value={email} onChange={e => setEmail(e.target.value)} placeholder="Family member's email" className="flex-1 rounded-xl" />
            <Select value={relationship} onValueChange={setRelationship}>
              <SelectTrigger className="w-40 rounded-xl"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="spouse">Spouse</SelectItem>
                <SelectItem value="parent">Parent</SelectItem>
                <SelectItem value="child">Child</SelectItem>
                <SelectItem value="sibling">Sibling</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={linkMember} disabled={linking || !email.trim()} className="rounded-xl">
              {linking ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Mail className="w-4 h-4 mr-2" />Send Invite</>}
            </Button>
          </CardContent>
        </Card>

        {/* Members List */}
        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Users className="w-5 h-5" />Linked Members</CardTitle></CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-6"><Loader2 className="w-6 h-6 animate-spin" /></div>
            ) : members.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">No family members linked yet.</p>
            ) : (
              <div className="space-y-3">
                {members.map((m: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Heart className="w-4 h-4 text-pink-500" />
                      <div>
                        <div className="text-sm font-medium">{m.name || m.email || `Member ${i + 1}`}</div>
                        <div className="text-xs text-muted-foreground capitalize">{m.relationship_type || 'family'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={m.is_accepted ? 'default' : 'secondary'}>{m.is_accepted ? 'Accepted' : 'Pending'}</Badge>
                      <Button variant="ghost" size="sm" onClick={() => unlinkMember(m.id || m.link_id)}>
                        <Unlink className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Family Wealth */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Family Wealth Overview</CardTitle>
            <CardDescription>Combined financial picture of your family.</CardDescription>
          </CardHeader>
          <CardContent>
            {!wealth ? (
              <Button onClick={loadWealth} disabled={wealthLoading} className="rounded-xl">
                {wealthLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}Generate Family Wealth Report
              </Button>
            ) : (
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {wealth.narrative || wealth.response || JSON.stringify(wealth, null, 2)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Family;
