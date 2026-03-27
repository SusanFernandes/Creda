import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface PieDataPoint {
  name: string;
  value: number;
  color?: string;
  percentage?: number;
}

interface AdvancedPieChartProps {
  data: PieDataPoint[];
  title?: string;
  description?: string;
  valuePrefix?: string;
  valueSuffix?: string;
  showPercentages?: boolean;
  showLegend?: boolean;
  height?: number;
  className?: string;
  noCard?: boolean;
}

const COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

export const AdvancedPieChart: React.FC<AdvancedPieChartProps> = ({
  data,
  title,
  description,
  valuePrefix = '',
  valueSuffix = '',
  showPercentages = true,
  showLegend = true,
  height = 300,
  className = '',
  noCard = false
}) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  
  const dataWithPercentages = data.map((item, index) => ({
    ...item,
    percentage: (item.value / total) * 100,
    color: item.color || COLORS[index % COLORS.length]
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-card/80 backdrop-blur-xl border border-border/50 rounded-2xl p-4 shadow-2xl">
          <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1">{data.name}</p>
          <div className="flex items-end gap-2">
            <p className="text-xl font-black tracking-tighter">
              {valuePrefix}{data.value.toLocaleString()}{valueSuffix}
            </p>
            <Badge variant="outline" className="mb-1 text-[10px] font-black border-none bg-primary/10 text-primary">
              {data.percentage.toFixed(1)}%
            </Badge>
          </div>
        </div>
      );
    }
    return null;
  };

  const chartContent = (
    <div className={showLegend ? "flex flex-col items-center gap-10 w-full" : ""}>
      <div className="relative flex justify-center items-center group/pie pt-0 w-full">
        <div style={{ width: '100%', height: height }} className="relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <defs>
                {dataWithPercentages.map((entry, index) => (
                  <linearGradient key={`gradient-${index}`} id={`grad-${index}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
                    <stop offset="100%" stopColor={entry.color} stopOpacity={0.8} />
                  </linearGradient>
                ))}
              </defs>
              <Pie
                data={dataWithPercentages}
                cx="50%"
                cy="50%"
                innerRadius={height / 4.5}
                outerRadius={height / 3}
                paddingAngle={4}
                dataKey="value"
                stroke="white"
                strokeWidth={2}
                animationBegin={0}
                animationDuration={1000}
                animationEasing="ease-out"
              >
                {dataWithPercentages.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={`url(#grad-${index})`}
                    className="hover:opacity-100 opacity-90 transition-all cursor-pointer outline-none"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        {/* Center Neural Label - No Blur */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-20">
          <div className="w-24 h-24 rounded-full bg-background border-2 border-border shadow-xl flex flex-col items-center justify-center">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/60 leading-none mb-1">Portfolio</span>
            <span className="text-xl font-black tracking-tighter leading-none">{valuePrefix}{(total/1000).toFixed(0)}K</span>
            <div className="mt-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20">
              <span className="text-[8px] font-black text-primary">LIVE</span>
            </div>
          </div>
        </div>
      </div>
      
      {showLegend && (
        <div className="flex flex-wrap justify-center gap-3 w-full">
          {dataWithPercentages.map((item, index) => (
            <Badge 
              key={item.name}
              variant="outline"
              className="px-4 py-2 border-none rounded-xl gap-2 h-auto bg-muted/30 group hover:bg-primary/10 transition-all duration-300"
            >
              <div 
                className="w-2 h-2 rounded-full shadow-sm group-hover:scale-125 transition-transform" 
                style={{ backgroundColor: item.color }}
              />
              <div className="flex flex-col items-start">
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{item.name}</span>
                <span className="text-[11px] font-black tracking-tighter text-foreground">
                  {valuePrefix}{item.value.toLocaleString()} ({item.percentage.toFixed(0)}%)
                </span>
              </div>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );

  if (noCard) return <div className={className}>{chartContent}</div>;

  return (
    <Card className={`bg-card border-none shadow-xl ${className}`}>
      <CardHeader>
        <CardTitle className="text-lg font-black tracking-tight">{title}</CardTitle>
        {description && <CardDescription className="text-xs uppercase font-bold tracking-widest opacity-60 mt-1">{description}</CardDescription>}
        <div className="text-3xl font-black tracking-tighter mt-2">
          {valuePrefix}{total.toLocaleString()}{valueSuffix}
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {chartContent}
      </CardContent>
    </Card>
  );
};

export default AdvancedPieChart;