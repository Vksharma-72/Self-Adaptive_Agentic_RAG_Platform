import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity, BadgeCheck, Database, FileText, Gauge, MessagesSquare, Timer, Users as UsersIcon,
} from 'lucide-react'
import api from '../../api.js'

const STAT_CARDS = [
  { key: 'queries_24h', label: 'Queries (24h)', icon: Activity, accent: 'from-indigo-500/25 to-indigo-500/5 text-indigo-300' },
  { key: 'queries', label: 'Total queries', icon: MessagesSquare, accent: 'from-violet-500/25 to-violet-500/5 text-violet-300' },
  { key: 'workspaces', label: 'Knowledge bases', icon: Database, accent: 'from-fuchsia-500/25 to-fuchsia-500/5 text-fuchsia-300' },
  { key: 'documents', label: 'Documents', icon: FileText, accent: 'from-sky-500/25 to-sky-500/5 text-sky-300' },
  { key: 'chunks', label: 'Indexed chunks', icon: Gauge, accent: 'from-emerald-500/25 to-emerald-500/5 text-emerald-300' },
  { key: 'users', label: 'Users', icon: UsersIcon, accent: 'from-amber-500/25 to-amber-500/5 text-amber-300' },
]

function AnimatedNumber({ value }) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    if (typeof value !== 'number') return
    const start = performance.now()
    const dur = 600
    let raf
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur)
      setShown(Math.round(value * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{shown}</>
}

function RecentQueries({ rows }) {
  if (!rows.length) {
    return (
      <div className="glass rounded-2xl p-8 text-center text-sm text-slate-500">
        No chat activity yet — queries will appear here as users talk to the assistant.
      </div>
    )
  }
  return (
    <div className="glass overflow-hidden rounded-2xl">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-white/5 text-[10px] uppercase tracking-widest text-slate-500">
          <tr>
            <th className="px-4 py-3 font-semibold">Question</th>
            <th className="hidden px-4 py-3 font-semibold md:table-cell">User</th>
            <th className="hidden px-4 py-3 font-semibold lg:table-cell">Knowledge base</th>
            <th className="px-4 py-3 font-semibold">Status</th>
            <th className="px-4 py-3 font-semibold">Latency</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((r, i) => (
            <tr key={i} className="transition hover:bg-white/[0.03]">
              <td className="max-w-xs px-4 py-3">
                <p className="truncate text-slate-200" title={r.question}>{r.question}</p>
                <p className="text-xs text-slate-500 md:hidden">{r.user} · {r.workspace}</p>
              </td>
              <td className="hidden max-w-[140px] truncate px-4 py-3 text-xs text-slate-400 md:table-cell">{r.user}</td>
              <td className="hidden max-w-[140px] truncate px-4 py-3 text-xs text-slate-400 lg:table-cell">{r.workspace}</td>
              <td className="px-4 py-3">
                {r.status === 'Blocked by guardrails.' ? (
                  <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-300">blocked</span>
                ) : r.verified ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-300">
                    <BadgeCheck size={11} /> verified
                  </span>
                ) : (
                  <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300">
                    {r.status === 'error' ? 'error' : 'unverified'}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-slate-400">{r.latency_ms} ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function OverviewTab() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  const load = () => api.get('/stats').then((r) => setStats(r.data)).catch((e) => setError(e.message))

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  if (error) return <p className="text-sm text-rose-400">Could not load stats: {error}</p>
  if (!stats) {
    return (
      <div className="glass animate-pulse rounded-2xl p-10 text-center text-sm text-slate-500">
        Loading platform activity…
      </div>
    )
  }

  const maxActivity = Math.max(1, ...stats.workspace_activity.map((a) => a.queries))

  return (
    <div className="space-y-6">
      {/* health strip */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm">
          <BadgeCheck size={14} className="text-emerald-400" />
          <b className="text-white">{stats.verified_pct}%</b>
          <span className="text-slate-400">answers verified</span>
        </span>
        {stats.avg_latency_ms != null && (
          <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm">
            <Timer size={14} className="text-indigo-300" />
            <b className="text-white">{stats.avg_latency_ms} ms</b>
            <span className="text-slate-400">avg latency</span>
          </span>
        )}
        <span className="ml-auto text-xs text-slate-500">auto-refreshes every 15s</span>
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {STAT_CARDS.map(({ key, label, icon: Icon, accent }, i) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="glass relative overflow-hidden rounded-2xl p-4"
          >
            <div className={`absolute -right-6 -top-6 h-20 w-20 rounded-full bg-gradient-to-br ${accent.split(' ').slice(0, 2).join(' ')} blur-xl opacity-60`} />
            <div className="flex items-center justify-between">
              <p className="text-2xl font-extrabold tabular-nums text-white">
                <AnimatedNumber value={stats.totals[key]} />
              </p>
              <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${accent} ring-1 ring-white/10`}>
                <Icon size={16} />
              </div>
            </div>
            <p className="mt-1 text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* recent queries */}
        <div className="lg:col-span-3">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-400">Recent questions</h3>
          <RecentQueries rows={stats.recent_queries} />
        </div>

        {/* workspace activity */}
        <div className="lg:col-span-2">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-400">Activity by knowledge base</h3>
          <div className="glass space-y-4 rounded-2xl p-5">
            {stats.workspace_activity.length === 0 && (
              <p className="text-sm text-slate-500">No activity yet.</p>
            )}
            {stats.workspace_activity.map((a) => (
              <div key={a.workspace}>
                <div className="mb-1.5 flex items-center justify-between text-sm">
                  <span className="truncate font-medium text-slate-200">{a.workspace}</span>
                  <span className="font-mono text-xs text-slate-400">{a.queries}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(a.queries / maxActivity) * 100}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-fuchsia-500"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
