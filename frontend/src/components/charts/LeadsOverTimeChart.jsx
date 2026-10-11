import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORICAL, INK, SURFACE } from "./palette";

export default function LeadsOverTimeChart({ data, scheme }) {
  const ink = INK[scheme];
  const lineColor = CATEGORICAL[scheme][0];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={ink.grid} vertical={false} strokeDasharray="0" />
        <XAxis
          dataKey="date"
          tick={{ fill: ink.muted, fontSize: 12 }}
          axisLine={{ stroke: ink.axis }}
          tickLine={false}
          minTickGap={24}
        />
        <YAxis allowDecimals={false} tick={{ fill: ink.muted, fontSize: 12 }} axisLine={{ stroke: ink.axis }} tickLine={false} width={30} />
        <Tooltip
          contentStyle={{ background: SURFACE[scheme], border: `1px solid ${ink.grid}`, borderRadius: 8, fontSize: 13 }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.secondary }}
        />
        <Line type="monotone" dataKey="count" name="Leads" stroke={lineColor} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
