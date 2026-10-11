import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { INK, STATUS, SURFACE } from "./palette";

/** Two-segment stacked bar for a good/bad state split (success vs failed,
 * on-plan vs fallback) — status colors, not categorical, since the series
 * genuinely means good/bad rather than "series N". Always paired with a
 * legend since there are 2 series. */
export default function StackedStatusBarChart({ data, xKey, goodKey, badKey, goodLabel, badLabel, badColor, scheme }) {
  const ink = INK[scheme];
  const surface = SURFACE[scheme];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={ink.grid} vertical={false} strokeDasharray="0" />
        <XAxis dataKey={xKey} tick={{ fill: ink.muted, fontSize: 12 }} axisLine={{ stroke: ink.axis }} tickLine={false} />
        <YAxis allowDecimals={false} tick={{ fill: ink.muted, fontSize: 12 }} axisLine={{ stroke: ink.axis }} tickLine={false} width={30} />
        <Tooltip
          contentStyle={{ background: surface, border: `1px solid ${ink.grid}`, borderRadius: 8, fontSize: 13 }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.secondary }}
          cursor={{ fill: ink.grid, opacity: 0.4 }}
        />
        <Legend wrapperStyle={{ fontSize: 13, color: ink.secondary }} />
        <Bar dataKey={goodKey} name={goodLabel} stackId="a" fill={STATUS.good} stroke={surface} strokeWidth={2} maxBarSize={40} radius={[0, 0, 0, 0]} />
        <Bar
          dataKey={badKey}
          name={badLabel}
          stackId="a"
          fill={badColor || STATUS.warning}
          stroke={surface}
          strokeWidth={2}
          maxBarSize={40}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
