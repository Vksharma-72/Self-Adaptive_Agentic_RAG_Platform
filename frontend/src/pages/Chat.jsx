import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Bot, ChevronDown, Plus, Send, Trash2, User as UserIcon, Wand2, AlertTriangle, BadgeCheck,
} from 'lucide-react'
import api from '../api.js'
import { useAuth } from '../auth.jsx'
import { TopBar, StatusPill } from '../components/shell.jsx'

/* ---------- message subcomponents ---------- */

function Collapsible({ icon: Icon, label, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-xl border border-white/5 bg-ink-800/60">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-slate-300"
      >
        <Icon size={13} className="text-indigo-300" />
        {label}
        <ChevronDown size={13} className={`ml-auto text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/5 px-3 py-2.5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function AssistantMessage({ msg }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/80 to-fuchsia-500/80 shadow-md shadow-indigo-900/40">
        <Bot size={16} className="text-white" />
      </div>
      <div className="min-w-0 max-w-[85%] flex-1 space-y-2">
        {msg.steps?.length > 0 && (
          <Collapsible icon={Wand2} label={`Agent reasoning · ${msg.steps.length} steps`}>
            <ul className="space-y-1 text-xs text-slate-400">
              {msg.steps.map((s, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex gap-2"
                >
                  <span className="text-indigo-400/70">▸</span>
                  {s}
                </motion.li>
              ))}
            </ul>
          </Collapsible>
        )}

        <div className="glass rounded-2xl rounded-tl-md px-4 py-3.5 shadow-lg shadow-black/20">
          {msg.verified === true && (
            <span className="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300 ring-1 ring-emerald-400/25">
              <BadgeCheck size={12} /> Verified against sources
            </span>
          )}
          {msg.verified === false && (
            <span className="mb-2 inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300 ring-1 ring-amber-400/25">
              <AlertTriangle size={12} /> Not fully grounded — treat with care
            </span>
          )}
          {msg.error && <p className="mb-1 text-sm text-rose-400">Something went wrong.</p>}
          <div className="md text-slate-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ''}</ReactMarkdown>
          </div>
          {msg.sources?.length > 0 && (
            <div className="mt-3">
              <Collapsible icon={ChevronDown} label={`Sources · ${msg.sources.length} chunks`}>
                <div className="space-y-2">
                  {msg.sources.map((src, i) => {
                    const clean = src.replace(/^CONTENT: /, '')
                    return (
                      <details key={i} className="group rounded-lg bg-ink-900/70 ring-1 ring-white/5">
                        <summary className="cursor-pointer select-none truncate px-3 py-1.5 text-xs text-slate-400 transition group-hover:text-slate-200">
                          <span className="mr-1.5 font-mono text-[10px] text-indigo-300/80">#{i + 1}</span>
                          {clean.slice(0, 92)}…
                        </summary>
                        <p className="max-h-40 overflow-auto border-t border-white/5 px-3 py-2 whitespace-pre-wrap text-xs text-slate-300">
                          {clean}
                        </p>
                      </details>
                    )
                  })}
                </div>
              </Collapsible>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function UserMessage({ content }) {
  return (
    <div className="flex items-start justify-end gap-3">
      <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-gradient-to-br from-indigo-600 to-violet-600 px-4 py-3 text-sm leading-relaxed text-white shadow-lg shadow-indigo-950/40">
        {content}
      </div>
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/8 ring-1 ring-white/15">
        <UserIcon size={15} className="text-slate-300" />
      </div>
    </div>
  )
}

const THINKING_PHASES = ['Rewriting your question…', 'Searching the knowledge base…', 'Grading retrieved chunks…', 'Synthesizing the answer…', 'Verifying against sources…']

function Thinking() {
  const [phase, setPhase] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setPhase((p) => (p + 1) % THINKING_PHASES.length), 1600)
    return () => clearInterval(t)
  }, [])
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/80 to-fuchsia-500/80 shadow-md shadow-indigo-900/40">
        <Bot size={16} className="text-white" />
      </div>
      <div className="glass flex items-center gap-3 rounded-2xl rounded-tl-md px-4 py-3.5">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-300"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
        <span key={phase} className="shimmer text-xs font-medium">
          {THINKING_PHASES[phase]}
        </span>
      </div>
    </motion.div>
  )
}

/* ---------- sidebar ---------- */

function WorkspaceSidebar({ workspaces, wsId, onSelect, onNewChat }) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-white/5 bg-ink-900/50 backdrop-blur-xl md:flex">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 transition hover:brightness-110 active:scale-[0.99]"
        >
          <Plus size={16} /> New conversation
        </button>
      </div>
      <p className="px-4 pb-1.5 pt-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
        Knowledge bases
      </p>
      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2.5 pb-3">
        {workspaces.map((ws) => (
          <button
            key={ws.id}
            onClick={() => onSelect(ws.id)}
            className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition ${
              wsId === ws.id
                ? 'bg-indigo-500/15 text-white ring-1 ring-indigo-400/30'
                : 'text-slate-300 hover:bg-white/5'
            }`}
          >
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                ws.status === 'ready' ? 'bg-emerald-400 shadow-[0_0_8px] shadow-emerald-400/60'
                : ws.status === 'failed' ? 'bg-rose-400'
                : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{ws.name}</span>
            </span>
          </button>
        ))}
        {workspaces.length === 0 && (
          <p className="px-3 py-4 text-xs text-slate-500">No knowledge bases yet — create one in Admin.</p>
        )}
      </div>
    </aside>
  )
}

/* ---------- main ---------- */

export default function Chat() {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState([])
  const [wsId, setWsId] = useState(null)
  const [messages, setMessages] = useState([])
  const [threadId, setThreadId] = useState(() => crypto.randomUUID())
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    api.get('/workspaces').then((res) => {
      setWorkspaces(res.data)
      const ready = res.data.find((w) => w.status === 'ready')
      if (ready) setWsId((cur) => cur ?? ready.id)
    })
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const selected = workspaces.find((w) => w.id === wsId)

  const suggestions = useMemo(() => {
    if (!selected?.profile_json) return []
    try {
      return JSON.parse(selected.profile_json).sample_questions?.slice(0, 4) || []
    } catch {
      return []
    }
  }, [selected])

  const send = async (q) => {
    if (typeof q !== 'string') q = input
    q = q.trim()
    if (!q || !wsId || thinking) return

    setInput('')
    setMessages((m) => [...m, { role: 'user', content: q }])
    setThinking(true)

    try {
      const { data } = await api.post(`/workspaces/${wsId}/query`, { q, thread_id: threadId })
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: data.answer,
          steps: data.thought_process,
          sources: data.sources,
          status: data.status,
          verified: data.verified,
        },
      ])
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: '❌ Backend error — is the server running?', error: true },
      ])
    } finally {
      setThinking(false)
    }
  }

  const newChat = () => {
    setMessages([])
    setThreadId(crypto.randomUUID())
  }

  return (
    <div className="flex h-full min-h-0">
      <WorkspaceSidebar workspaces={workspaces} wsId={wsId} onSelect={setWsId} onNewChat={newChat} />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TopBar>
          {/* mobile workspace picker */}
          <select
            value={wsId || ''}
            onChange={(e) => setWsId(e.target.value)}
            className="rounded-lg border border-white/10 bg-ink-800 px-2.5 py-1.5 text-xs text-slate-200 outline-none md:hidden"
          >
            <option value="" disabled>Select knowledge base…</option>
            {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          {selected && (
            <>
              <span className="hidden text-sm font-medium text-slate-300 md:inline">{selected.name}</span>
              <StatusPill status={selected.status} />
            </>
          )}
        </TopBar>

        {/* messages */}
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.length === 0 && !thinking && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-14 text-center"
              >
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 shadow-xl shadow-indigo-900/40">
                  <Bot size={28} className="text-white" />
                </div>
                <h2 className="text-xl font-bold text-white">
                  {selected ? `Ask anything about ${selected.name}` : 'Pick a knowledge base to start'}
                </h2>
                <p className="mt-1.5 text-sm text-slate-400">
                  {selected?.status === 'ready'
                    ? 'Answers are grounded in your documents and verified before display.'
                    : selected
                      ? `This knowledge base is ${selected.status} — answers improve once it's ready.`
                      : 'Create one in the Admin dashboard, then come back here.'}
                </p>

                {suggestions.length > 0 && (
                  <div className="mx-auto mt-7 flex max-w-xl flex-wrap justify-center gap-2">
                    {suggestions.map((q, i) => (
                      <motion.button
                        key={q}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.15 + i * 0.08 }}
                        onClick={() => send(q)}
                        className="glass rounded-full px-4 py-2 text-xs text-slate-300 transition hover:border-indigo-400/40 hover:text-white"
                      >
                        {q}
                      </motion.button>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                >
                  {msg.role === 'user'
                    ? <UserMessage content={msg.content} />
                    : <AssistantMessage msg={msg} />}
                </motion.div>
              ))}
            </AnimatePresence>

            {thinking && <Thinking />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* composer */}
        <div className="border-t border-white/5 bg-ink-900/50 px-4 py-3.5 backdrop-blur-xl">
          <form
            onSubmit={(e) => { e.preventDefault(); send() }}
            className="glass glow-ring mx-auto flex max-w-3xl items-end gap-2 rounded-2xl p-2"
          >
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
              }}
              placeholder={wsId ? 'Ask about your documents…  (Enter to send, Shift+Enter for newline)' : 'Select a knowledge base first…'}
              disabled={!wsId || thinking}
              className="max-h-40 flex-1 resize-none bg-transparent px-2.5 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 disabled:opacity-50"
            />
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="button"
              onClick={newChat}
              title="New conversation"
              className="rounded-xl p-2.5 text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
            >
              <Trash2 size={16} />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="submit"
              disabled={!wsId || thinking || !input.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 transition disabled:opacity-40"
            >
              <Send size={15} />
            </motion.button>
          </form>
          <p className="mt-2 text-center text-[11px] text-slate-600">
            Answers are graded and verified against your sources before display.
          </p>
        </div>
      </div>
    </div>
  )
}
