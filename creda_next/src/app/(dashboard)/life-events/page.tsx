'use client';

import React, { useState } from 'react';
import { CalendarHeart, Loader2, Gift, Baby, GraduationCap, Home, Briefcase, Heart, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ApiService } from '@/services/api';

const EVENTS = [
  { id: 'marriage', label: 'Getting Married', icon: Heart, color: 'text-pink-500' },
  { id: 'baby', label: 'Having a Baby', icon: Baby, color: 'text-blue-500' },
  { id: 'home_purchase', label: 'Buying a Home', icon: Home, color: 'text-green-500' },
  { id: 'job_change', label: 'Job Change', icon: Briefcase, color: 'text-orange-500' },
  { id: 'child_education', label: 'Child Education', icon: GraduationCap, color: 'text-purple-500' },
  { id: 'bonus', label: 'Received Bonus', icon: Gift, color: 'text-yellow-500' },
];

const LifeEvents: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState('');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const analyse = async () => {
    const message = selectedEvent
      ? `I'm planning for: ${selectedEvent}. ${description}`
      : description;
    if (!message.trim()) return;
    setLoading(true);
    try { setResult(await ApiService.lifeEventAdvisor({ message })); }
    catch { setResult({ error: 'Service unavailable.' }); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-20 pt-10 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Life Event Advisor</h1>
          <p className="text-sm text-muted-foreground mt-1">Get personalised financial advice for major life events.</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {EVENTS.map(e => (
            <Card key={e.id} className={`cursor-pointer transition-all hover:shadow-md ${selectedEvent === e.id ? 'ring-2 ring-primary' : ''}`}
              onClick={() => setSelectedEvent(e.id)}>
              <CardContent className="p-4 flex items-center gap-3">
                <e.icon className={`w-5 h-5 ${e.color}`} />
                <span className="text-sm font-medium">{e.label}</span>
              </CardContent>
            </Card>
          ))}
        </div>

        <Textarea value={description} onChange={e => setDescription(e.target.value)}
          placeholder="Describe your situation (e.g., 'Getting married next year, budget ₹15 lakhs, want to buy a house in 3 years')..."
          className="min-h-[100px] rounded-xl" />

        <Button onClick={analyse} disabled={loading || (!selectedEvent && !description.trim())} className="rounded-xl">
          {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Analysing...</> : <><CalendarHeart className="w-4 h-4 mr-2" />Get Advice</>}
        </Button>

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>Financial Impact Analysis</CardTitle>
              {result.bonus_recorded && <Badge className="w-fit">Bonus Recorded: ₹{result.ytd_bonus_income?.toLocaleString('en-IN')}</Badge>}
            </CardHeader>
            <CardContent>
              {result.error ? (
                <p className="text-red-500">{result.error}</p>
              ) : (
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {result.narrative || result.response || JSON.stringify(result, null, 2)}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default LifeEvents;
