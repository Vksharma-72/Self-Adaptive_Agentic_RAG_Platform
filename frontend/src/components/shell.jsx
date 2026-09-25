import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, LayoutDashboard, LogOut, Sparkles } from 'lucide-react'
import { useAuth } from '../auth.jsx'

export const STATUS_STYLES = {
  empty:     'bg-slate-500/15 text-slate-300 ring-1 ring-slate-400/20',
  ingesting: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30',
  analyzing: 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30',
  ready:     'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30',
  failed:    'bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/30',
}

export function StatusPill({ status, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] || ''} ${className}`}
    >
      {['ingesting', 'analyzing'].includes(status) && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {status}
    </span>
  )
}

export function Logo({ compact = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 shadow-lg shadow-indigo-500/30">
        <Sparkles className="h-4.5 w-4.5 text-white" size={18} />
      </div>
      {!compact && (
        <div className="leading-tight">
          <p className="text-sm font-bold tracking-tight text-white">Adaptive RAG</p>
          <p className="text-[10px] font-medium uppercase tracking-widest text-indigo-300/70">
            Self-learning platform
          </p>
        </div>
      )}
    </div>
  )
}

export function TopBar({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  const links = [
    { to: '/chat', label: 'Chat', icon: MessageSquare },
    ...(user?.role === 'admin' ? [{ to: '/admin', label: 'Admin', icon: LayoutDashboard }] : []),
  ]

  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-ink-900/60 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-5">
          <Link to="/chat" className="transition hover:opacity-80">
            <Logo compact />
          </Link>
          {children}
        </div>

        <nav className="flex items-center gap-1.5">
          {links.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  active
                    ? 'bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/30'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <Icon size={15} />
                {label}
              </Link>
            )
          })}
          <div className="mx-2 hidden h-6 w-px bg-white/10 sm:block" />
          <span className="hidden text-sm text-slate-400 sm:inline">{user?.email}</span>
          {user?.role && (
            <span
              className={`hidden rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider sm:inline ${
                user.role === 'root'
                  ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30'
                  : user.role === 'admin'
                    ? 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30'
                    : 'bg-slate-500/15 text-slate-400 ring-1 ring-slate-400/20'
              }`}
            >
              {user.role}
            </span>
          )}
          <button
            onClick={logout}
            title="Sign out"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-white/5 hover:text-rose-300"
          >
            <LogOut size={16} />
          </button>
        </nav>
      </div>
    </header>
  )
}

export function Aurora() {
  return <div className="aurora" aria-hidden="true" />
}
