import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Gauge, Loader2, Zap } from 'lucide-react'
import api from '../../api.js'

const PRESETS = [
  { id: 'scalar_int8', label: 'Scalar int8', compression: '4x', note: 'Classic scalar quantization' },
  { id: 'turbo_b4', label: 'TurboQuant 4-bit', compression: '8x', note: 'Near-identical accuracy to int8, half the storage' },
  { id: 'turbo_b2', label: 'TurboQuant 2-bit', compression: '16x', note: 'Best quality per bit for most workloads' },
  { id: 'turbo_b1_5', label: 'TurboQuant 1.5-bit', compression: '~21x', note: 'Middle ground' },
  { id: 'turbo_b1', label: 'TurboQuant 1-bit', compression: '32x', note: 'Maximum compression' },
]

const CURRENT_LABELS = {
  scalar_int8: 'Scalar int8', turbo_b4: 'TurboQuant 4-bit', turbo_b2: 'TurboQuant 2-bit',
  turbo_b1_5: 'TurboQuant 1.5-bit', turbo_b1: 'TurboQuant 1-bit', custom: 'Custom config',
}

export default function OptimizationTab({ workspace }) {
  const [selected, setSelected] = useState(PRESETS.map((p) => p.id))
  const [runState, setRunState] = useState({ status: 'never_run', results: null })
  const [current, setCurrent] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    if (!workspace) return
    api.get(`/workspaces/${workspace.id}/optimize`).then((res) => setRunState(res.data))
    api.get(`/workspaces/${workspace.id}/quantization`).then((res) => setCurrent(res.data.preset))
  }

  useEffect(() => {
    load()
    if (runState.status === 'running') {
      const t = setInterval(load, 4000)
      return () => clearInterval(t)
    }
  }, [workspace?.id, runState.status])

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  const run = async () => {
    if (!selected.length) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/workspaces/${workspace.id}/optimize`, { presets: selected })
      setRunState((s) => ({ ...s, status: 'running' }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start the experiment')
    } finally {
      setBusy(false)
    }
  }

  const apply = async (preset) => {
    if (!confirm(`Apply "${preset}" to this knowledge base? Qdrant will re-index the collection.`)) return
    setError('')
    try {
      await api.post(`/workspaces/${workspace.id}/optimize/apply`, { preset })
      setCurrent(preset)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not apply the preset')
    }
  }

  const bench = runState.results?.bench
  const results = runState.results?.results || []
  const bestRecall = Math.max(0, ...results.map((r) => r.recall_at_5 || 0))

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/25 to-fuchsia-500/25 ring-1 ring-indigo-400/30">
            <Gauge size={19} className="text-indigo-300" />
          </div>
          <div>
            <h2 className="font-bold text-white">Optimization Lab — TurboQuant benchmarking</h2>
            <p className="text-sm text-slate-400">
              Benchmark quantization presets against exact search on this knowledge base's real vectors,
              then apply the winner to the live collection.
            </p>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Current quantization:{' '}
          <b className="text-slate-300">{current ? CURRENT_LABELS[current] || current : 'none (full-precision vectors)'}</b>
          {runState.status === 'running' && (
            <span className="ml-3 inline-flex items-center gap-1.5 text-amber-300">
              <Loader2 size={12} className="animate-spin" /> experiment running…
            </span>
          )}
        </p>
      </div>

      <div className="space-y-2.5">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Presets to benchmark</h3>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {PRESETS.map((p) => {
            const active = selected.includes(p.id)
            return (
              <button
                key={p.id}
                onClick={() => toggle(p.id)}
                className={`flex items-start gap-3 rounded-2xl px-4 py-3.5 text-left transition ${
                  active
                    ? 'glass-strong ring-2 ring-indigo-400/50'
                    : 'glass text-slate-400 hover:ring-1 hover:ring-white/15'
                }`}
              >
                <span
                  className={`mt-0.5 flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-md border transition ${
                    active ? 'border-indigo-400 bg-indigo-500' : 'border-slate-600'
                  }`}
                  style={{ height: 18, width: 18 }}
                >
                  {active && <Check size={12} className="text-white" />}
                </span>
                <span>
                  <span className={`text-sm font-semibold ${active ? 'text-white' : ''}`}>
                    {p.label}
                  </span>
                  <span className="ml-2 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                    {p.compression}
                  </span>
                  <br />
                  <span className="text-xs text-slate-500">{p.note}</span>
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <motion.button
        whileHover={{ scale: 1.015 }}
        whileTap={{ scale: 0.985 }}
        onClick={run}
        disabled={busy || runState.status === 'running' || !selected.length}
        className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 disabled:opacity-50"
      >
        {runState.status === 'running' ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
        {runState.status === 'running' ? 'Benchmarking…' : 'Run experiment'}
      </motion.button>

      {error && <p className="text-sm text-rose-400">{error}</p>}
      {runState.status === 'failed' && (
        <p className="text-sm text-rose-400">Experiment failed: {runState.error}</p>
      )}

      {results.length > 0 && (
        <div className="glass overflow-hidden rounded-2xl">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-white/5 text-[10px] uppercase tracking-widest text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Preset</th>
                <th className="px-4 py-3 font-semibold">Recall@{bench?.k || 5}</th>
                <th className="px-4 py-3 font-semibold">Latency p50 / p95</th>
                <th className="px-4 py-3 font-semibold">Memory saved</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {results.map((r) => (
                <tr key={r.preset} className="transition hover:bg-white/[0.03]">
                  <td className="px-4 py-3.5">
                    <p className="font-medium text-slate-200">
                      {PRESETS.find((p) => p.id === r.preset)?.label || r.preset}
                    </p>
                    {r.note && <p className="text-xs text-slate-500">{r.note}</p>}
                  </td>
                  <td className="px-4 py-3.5">
                    {r.status !== 'ok' ? (
                      <span className="text-xs font-semibold text-amber-400">{r.status}</span>
                    ) : (
                      <div className="flex items-center gap-2.5">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(r.recall_at_5 * 100).toFixed(1)}%` }}
                            transition={{ duration: 0.7, ease: 'easeOut' }}
                            className={`h-full rounded-full ${
                              r.recall_at_5 >= 0.98
                                ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                                : r.recall_at_5 >= 0.9
                                  ? 'bg-gradient-to-r from-indigo-500 to-violet-400'
                                  : 'bg-gradient-to-r from-amber-500 to-rose-400'
                            }`}
                          />
                        </div>
                        <span className={`text-xs font-bold ${
                          r.recall_at_5 === bestRecall ? 'text-emerald-300' : 'text-slate-300'
                        }`}>
                          {(r.recall_at_5 * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-xs text-slate-300">
                    {r.latency_p50_ms != null ? `${r.latency_p50_ms} / ${r.latency_p95_ms} ms` : '—'}
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-300">
                      {r.memory_saved_pct != null ? `${r.memory_saved_pct}%` : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    {r.status === 'ok' && (
                      <motion.button
                        whileHover={{ scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => apply(r.preset)}
                        disabled={current === r.preset}
                        className="rounded-lg border border-indigo-400/40 px-3.5 py-1.5 text-xs font-semibold text-indigo-300 transition hover:bg-indigo-500/10 disabled:opacity-30"
                      >
                        {current === r.preset ? '✓ Applied' : 'Apply'}
                      </motion.button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {bench && (
            <p className="border-t border-white/5 px-4 py-2.5 text-xs text-slate-500">
              Benchmarked on {bench.vectors} vectors ({bench.dim}-dim) with {bench.queries} queries against
              exact-search ground truth.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
