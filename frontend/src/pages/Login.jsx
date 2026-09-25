import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Brain, FileUp, ShieldCheck, Loader2, ShieldAlert, KeyRound } from 'lucide-react'
import { useAuth } from '../auth.jsx'
import { Aurora, Logo } from '../components/shell.jsx'

const HIGHLIGHTS = [
  { icon: FileUp, title: 'Drop any documents', text: 'PDF, DOCX, PPTX, HTML, TXT — any domain, zero config.' },
  { icon: Brain, title: 'It learns the domain', text: 'Topics, terminology and persona are generated automatically.' },
  { icon: ShieldCheck, title: 'Verified answers', text: 'Every response is graded and grounded in your sources.' },
]

export default function Login() {
  const { user, login, register, logout } = useAuth()
  const navigate = useNavigate()

  // view: "auth" (user sign-in/register) | "admin" (administrator access)
  const [view, setView] = useState('auth')
  const [mode, setMode] = useState('login') // within the auth view
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) {
    const dest = ['admin', 'root'].includes(user.role) ? '/admin' : '/chat'
    return <Navigate to={dest} replace />
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (view === 'admin') {
        const me = await login(email, password)
        if (!['admin', 'root'].includes(me.role)) {
          await logout()
          setError('This account does not have administrator access.')
          return
        }
        navigate('/admin')
      } else if (mode === 'login') {
        const me = await login(email, password)
        navigate(['admin', 'root'].includes(me.role) ? '/admin' : '/chat')
      } else {
        await register(email, password)
        setMode('login')
        setError('Account created — you can now sign in.')
      }
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Something went wrong. Check your input.')
    } finally {
      setBusy(false)
    }
  }

  const isAdminView = view === 'admin'

  return (
    <div className="relative flex min-h-full">
      {/* ---------- Left: brand hero ---------- */}
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden p-10 lg:flex">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Logo />
        </motion.div>

        <div className="max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl font-extrabold leading-tight tracking-tight text-white"
          >
            {isAdminView ? (
              <>
                Administrator
                <br />
                <span className="text-gradient">access portal</span>
              </>
            ) : (
              <>
                Upload documents.
                <br />
                <span className="text-gradient">Watch it learn.</span>
              </>
            )}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-4 text-base leading-relaxed text-slate-400"
          >
            {isAdminView
              ? 'Sign in with an administrator account to manage knowledge bases, users and quantization experiments.'
              : 'A self-adaptive RAG platform that analyzes your corpus, writes its own prompts and guardrails, and answers with verified, grounded responses.'}
          </motion.p>

          {!isAdminView && (
            <div className="mt-10 space-y-4">
              {HIGHLIGHTS.map(({ icon: Icon, title, text }, i) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 + i * 0.12 }}
                  className="flex items-start gap-3.5"
                >
                  <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-500/15 ring-1 ring-indigo-400/30">
                    <Icon size={17} className="text-indigo-300" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{title}</p>
                    <p className="text-sm text-slate-400">{text}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
          {isAdminView && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-10 flex items-start gap-3.5 rounded-2xl border border-amber-400/25 bg-amber-500/5 p-4"
            >
              <ShieldAlert size={18} className="mt-0.5 shrink-0 text-amber-300" />
              <p className="text-sm text-slate-300">
                Administrator accounts are created by the <b className="text-amber-200">root</b> account only.
                Self-registration always creates a regular chat user.
              </p>
            </motion.div>
          )}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-xs text-slate-500"
        >
          Multi-agent pipeline · Planner → Rewriter → Grader → Responder → Verifier
        </motion.p>
      </div>

      {/* ---------- Right: auth card ---------- */}
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.55, ease: 'easeOut' }}
          className="w-full max-w-md"
        >
          <div className="mb-8 flex flex-col items-center lg:hidden">
            <Logo />
          </div>

          <div
            className={`glass glow-ring relative overflow-hidden rounded-3xl p-7 shadow-2xl shadow-indigo-950/50 ${
              isAdminView ? 'ring-1 ring-amber-400/30' : ''
            }`}
          >
            {isAdminView && (
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber-400 via-orange-400 to-amber-400" />
            )}

            <div className="mb-5 flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-xl ring-1 ${
                  isAdminView
                    ? 'bg-amber-500/15 ring-amber-400/30'
                    : 'bg-indigo-500/15 ring-indigo-400/30'
                }`}
              >
                <KeyRound size={17} className={isAdminView ? 'text-amber-300' : 'text-indigo-300'} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">
                  {isAdminView ? 'Administrator sign-in' : mode === 'login' ? 'Welcome back' : 'Create your account'}
                </h2>
                <p className="text-sm text-slate-400">
                  {isAdminView
                    ? 'Restricted area — admins and root only.'
                    : mode === 'login'
                      ? 'Sign in to your knowledge platform.'
                      : 'Registration creates a regular chat user.'}
                </p>
              </div>
            </div>

            {!isAdminView && (
              <div className="mb-6 flex rounded-xl bg-white/5 p-1 text-sm font-medium ring-1 ring-white/10">
                {['login', 'register'].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => { setMode(m); setError('') }}
                    className={`relative flex-1 rounded-lg py-2 transition ${
                      mode === m ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {mode === m && (
                      <motion.span
                        layoutId="auth-tab"
                        className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 shadow-lg shadow-indigo-900/40"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.45 }}
                      />
                    )}
                    <span className="relative">{m === 'login' ? 'Sign in' : 'Register'}</span>
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={isAdminView ? 'admin@company.com' : 'you@company.com'}
                  className="w-full rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60"
                />
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`text-sm ${error.includes('now sign in') ? 'text-emerald-400' : 'text-rose-400'}`}
                >
                  {error}
                </motion.p>
              )}

              <motion.button
                whileHover={{ scale: 1.015 }}
                whileTap={{ scale: 0.985 }}
                type="submit"
                disabled={busy}
                className={`group flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-60 ${
                  isAdminView
                    ? 'bg-gradient-to-r from-amber-500 to-orange-500 shadow-amber-950/40'
                    : 'bg-gradient-to-r from-indigo-600 to-violet-600 shadow-indigo-900/40'
                }`}
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : <KeyRound size={15} />}
                {isAdminView ? 'Enter admin console' : mode === 'login' ? 'Sign in' : 'Create account'}
                {!busy && !isAdminView && <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />}
              </motion.button>
            </form>

            {/* switch between user / admin access */}
            <div className="mt-5 border-t border-white/5 pt-4 text-center">
              <button
                type="button"
                onClick={() => { setView(isAdminView ? 'auth' : 'admin'); setMode('login'); setError('') }}
                className="text-xs font-medium text-slate-400 transition hover:text-slate-200"
              >
                {isAdminView ? '← Back to user sign-in' : 'Admin? Sign in here →'}
              </button>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-slate-500">
            Powered by LangGraph · Qdrant · NeMo Guardrails
          </p>
        </motion.div>
      </div>
    </div>
  )
}
