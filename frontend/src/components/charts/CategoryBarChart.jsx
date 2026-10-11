import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { INK, SURFACE } from "./palette";

/** Reusable bar chart where each bar's color comes from a per-label lookup —
 * used for both categorical data (status, intent) and ordinal data
 * (priority, score bands), since the color job differs but the chart shape
 * doesn't. `colorFor(label)` decides which job's rule applies. */
export default function CategoryBarChart({ data, colorFor, scheme }) {
  const ink = INK[scheme];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 20, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={ink.grid} vertical={false} strokeDasharray="0" />
        <XAxis dataKey="label" tick={{ fill: ink.muted, fontSize: 12 }} axisLine={{ stroke: ink.axis }} tickLine={false} />
        <YAxis allowDecimals={false} tick={{ fill: ink.muted, fontSize: 12 }} axisLine={{ stroke: ink.axis }} tickLine={false} width={30} />
        <Tooltip
          contentStyle={{ background: SURFACE[scheme], border: `1px solid ${ink.grid}`, borderRadius: 8, fontSize: 13 }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.secondary }}
          cursor={{ fill: ink.grid, opacity: 0.4 }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {data.map((entry) => (
            <Cell key={entry.label} fill={colorFor(entry.label)} />
          ))}
          <LabelList dataKey="count" position="top" style={{ fill: ink.secondary, fontSize: 12 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
