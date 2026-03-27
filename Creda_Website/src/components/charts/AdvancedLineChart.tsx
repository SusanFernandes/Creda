import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface DataPoint {
  name: string;
  value: number;
  target?: number;
  previous?: number;
}

interface AdvancedLineChartProps {
  data: DataPoint[];
  title: string;
  description?: string;
  valuePrefix?: string;
  valueSuffix?: string;
  showTarget?: boolean;
  showTrend?: boolean;
  height?: number;
  color?: string;
  className?: string;
  noCard?: boolean;
}

export const AdvancedLineChart: React.FC<AdvancedLineChartProps> = ({
  data,
  title,
  description,
  valuePrefix = '',
  valueSuffix = '',
  showTarget = false,
  showTrend = true,
  height = 300,
  color = 'hsl(var(--primary))',
  className = '',
  noCard = false
}) => {
  const latestValue = data[data.length - 1]?.value || 0;
  const previousValue = data[data.length - 2]?.value || 0;
  const trend = latestValue - previousValue;
  const trendPercentage = previousValue ? ((trend / previousValue) * 100) : 0;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-sm font-medium">{label}</p>
          <p className="text-sm text-primary">
            Value: {valuePrefix}{payload[0].value.toLocaleString()}{valueSuffix}
          </p>
          {showTarget && payload[1] && (
            <p className="text-sm text-muted-foreground">
              Target: {valuePrefix}{payload[1].value.toLocaleString()}{valueSuffix}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  const chartContent = (
    <div className="space-y-4">
      {!noCard && (
        <div className="flex items-center justify-between mb-2">
          <div>
            <CardTitle className="text-lg font-black tracking-tight">{title}</CardTitle>
            {description && <CardDescription className="text-xs uppercase font-bold tracking-widest opacity-60 mt-1">{description}</CardDescription>}
          </div>
          {showTrend && (
            <Badge variant="outline" className={`gap-1 font-black tracking-tighter border-none ${trend >= 0 ? "bg-success/10 text-success" : "bg-error/10 text-error"}`}>
              {trend >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {Math.abs(trendPercentage).toFixed(1)}%
            </Badge>
          )}
        </div>
      )}
      {!noCard && (
        <div className="text-3xl font-black tracking-tighter">
          {valuePrefix}{latestValue.toLocaleString()}{valueSuffix}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <defs>
            <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={color} stopOpacity={0.0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} opacity={0.4} />
          <XAxis 
            dataKey="name" 
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            fontWeight="black"
            tickLine={false}
            axisLine={false}
            dy={10}
          />
          <YAxis 
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            fontWeight="black"
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `${valuePrefix}${value.toLocaleString()}${valueSuffix}`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'hsl(var(--primary))', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={4}
            fill="url(#colorGradient)"
            animationDuration={1500}
            animationEasing="ease-in-out"
          />
          {showTarget && (
            <Line
              type="monotone"
              dataKey="target"
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="5 5"
              strokeWidth={2}
              dot={false}
              opacity={0.3}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );

  if (noCard) return <div className={className}>{chartContent}</div>;

  return (
    <Card className={`bg-card/40 backdrop-blur-xl border-border/50 hover:shadow-xl hover:shadow-primary/5 transition-all duration-500 overflow-hidden ${className}`}>
      <CardContent className="pt-6">
        {chartContent}
      </CardContent>
    </Card>
  );
};

export default AdvancedLineChart;