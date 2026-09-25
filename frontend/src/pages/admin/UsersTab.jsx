import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Crown, Lock, ShieldCheck, Trash2, User as UserIcon, UserPlus } from 'lucide-react'
import api from '../../api.js'
import { useAuth } from '../../auth.jsx'

const ROLE_BADGE = {
  root: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30',
  admin: 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30',
  user: 'bg-slate-500/15 text-slate-400 ring-1 ring-slate-400/20',
}

function AddUserForm({ isRoot, onCreated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      await api.post('/users', { email, password, role: isRoot ? role : 'user' })
      setEmail('')
      setPassword('')
      setRole('user')
      setMsg({ ok: true, text: `Account created for ${email}${isRoot && role === 'admin' ? ' (admin)' : ''}` })
      onCreated()
    } catch (err) {
      setMsg({ ok: false, text: err.response?.data?.detail || 'Could not create user' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="glass glow-ring mb-5 rounded-2xl p-5">
      <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-indigo-300/80">Add user</h3>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="new.user@company.com"
          className="w-full rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60 sm:w-64"
        />
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (min 8 chars)"
          className="flex-1 rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60"
        />
        {isRoot ? (
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="rounded-xl border border-white/10 bg-ink-800 px-3 py-2.5 text-sm outline-none focus:border-indigo-400/60"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        ) : null}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          disabled={busy}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 disabled:opacity-50"
        >
          <UserPlus size={15} /> Create
        </motion.button>
      </div>
      {msg && (
        <p className={`mt-2 text-sm ${msg.ok ? 'text-emerald-400' : 'text-rose-400'}`}>{msg.text}</p>
      )}
    </form>
  )
}

export default function UsersTab() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState([])
  const isRoot = me?.role === 'root'

  const load = () => api.get('/users').then((res) => setUsers(res.data))

  useEffect(() => { load() }, [])

  const setRole = async (u, role) => {
    try {
      await api.patch(`/users/${u.id}`, { role })
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not change role')
      load()
    }
  }

  const remove = async (u) => {
    if (!confirm(`Delete user ${u.email}?`)) return
    try {
      await api.delete(`/users/${u.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not delete user')
    }
  }

  return (
    <div>
      <AddUserForm isRoot={isRoot} onCreated={load} />

      <div className="glass overflow-hidden rounded-2xl">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-white/5 text-[10px] uppercase tracking-widest text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">User</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {users.map((u) => {
              const isMe = u.email === me.email
              const isRootRow = u.role === 'root'
              const canManage = !isMe && !isRootRow && (isRoot || u.role === 'user')
              return (
                <tr key={u.id} className="transition hover:bg-white/[0.03]">
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-xl ring-1 ${
                        u.role === 'root'
                          ? 'bg-gradient-to-br from-amber-500/25 to-orange-500/25 ring-amber-400/30'
                          : u.role === 'admin'
                            ? 'bg-gradient-to-br from-violet-500/25 to-fuchsia-500/25 ring-violet-400/30'
                            : 'bg-white/5 ring-white/10'
                      }`}>
                        {u.role === 'root'
                          ? <ShieldCheck size={14} className="text-amber-300" />
                          : u.role === 'admin'
                            ? <Crown size={14} className="text-violet-300" />
                            : <UserIcon size={14} className="text-slate-400" />}
                      </div>
                      <div>
                        <p className="font-medium text-slate-200">
                          {u.email}
                          {isMe && <span className="ml-2 rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300">you</span>}
                        </p>
                        {isRootRow && <p className="text-xs text-amber-300/70">super-admin — manages all accounts</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    {isRoot && canManage ? (
                      <select
                        value={u.role}
                        onChange={(e) => setRole(u, e.target.value)}
                        className="rounded-lg border border-white/10 bg-ink-800 px-2.5 py-1.5 text-xs outline-none transition focus:border-indigo-400/60"
                      >
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                      </select>
                    ) : (
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase tracking-wider ${ROLE_BADGE[u.role] || ''}`}>
                        {u.role}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    {isRootRow ? (
                      <Lock size={14} className="ml-auto text-slate-600" title="The root account is protected" />
                    ) : (
                      <button
                        onClick={() => remove(u)}
                        disabled={!canManage}
                        title={canManage ? 'Delete user' : isMe ? "You can't delete yourself" : 'Only root can delete admins'}
                        className="rounded-lg p-1.5 text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-400 disabled:opacity-25"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="border-t border-white/5 px-4 py-2.5 text-xs text-slate-500">
          {isRoot
            ? 'You are the root account: you can create admins, change roles and manage every account.'
            : 'Admins can create regular chat users. Only the root account can create admins or change roles.'}
        </p>
      </div>
    </div>
  )
}
