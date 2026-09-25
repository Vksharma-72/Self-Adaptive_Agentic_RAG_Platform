import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import api from '../../api.js'
import { TopBar } from '../../components/shell.jsx'
import OverviewTab from './OverviewTab.jsx'
import WorkspacesTab from './WorkspacesTab.jsx'
import OptimizationTab from './OptimizationTab.jsx'
import UsersTab from './UsersTab.jsx'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'workspaces', label: 'Knowledge Bases' },
  { id: 'optimize', label: 'Optimization' },
  { id: 'users', label: 'Users' },
]

export default function Admin() {
  const [tab, setTab] = useState('overview')

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TopBar />
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-7">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mx-auto max-w-5xl"
        >
          <h1 className="mb-1 text-2xl font-bold tracking-tight text-white">Admin console</h1>
          <p className="mb-6 text-sm text-slate-400">
            Manage knowledge bases, run quantization experiments, and control access.
          </p>

          <div className="glass mb-7 inline-flex gap-1 rounded-xl p-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`relative rounded-lg px-4 py-2 text-sm font-medium transition ${
                  tab === t.id ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab === t.id && (
                  <motion.span
                    layoutId="admin-tab"
                    className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-600/80 to-violet-600/80 ring-1 ring-indigo-400/30"
                    transition={{ type: 'spring', bounce: 0.2, duration: 0.45 }}
                  />
                )}
                <span className="relative">{t.label}</span>
              </button>
            ))}
          </div>

          {tab === 'overview' && <OverviewTab />}
          {tab === 'workspaces' && <WorkspacesTab />}
          {tab === 'optimize' && <OptimizationTabWrapper />}
          {tab === 'users' && <UsersTab />}
        </motion.div>
      </div>
    </div>
  )
}

function OptimizationTabWrapper() {
  const [workspaces, setWorkspaces] = useState([])
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    api.get('/workspaces').then((res) => {
      setWorkspaces(res.data)
      setSelectedId((cur) => cur ?? (res.data[0] ? res.data[0].id : null))
    })
  }, [])

  const selected = workspaces.find((w) => w.id === selectedId)

  return (
    <div className="space-y-5">
      {workspaces.length > 1 && (
        <select
          value={selectedId || ''}
          onChange={(e) => setSelectedId(e.target.value)}
          className="rounded-xl border border-white/10 bg-ink-800 px-3 py-2 text-sm outline-none focus:border-indigo-400/60"
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      )}
      {selected ? (
        <OptimizationTab workspace={selected} />
      ) : (
        <div className="glass rounded-2xl p-8 text-center text-sm text-slate-400">
          Create a knowledge base with indexed documents first — the Optimization Lab
          benchmarks its real vectors.
        </div>
      )}
    </div>
  )
}
