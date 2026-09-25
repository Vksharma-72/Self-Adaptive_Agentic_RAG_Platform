import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { CloudUpload, Trash2, FileText } from 'lucide-react'
import api from '../../api.js'
import { StatusPill } from '../../components/shell.jsx'

const DOC_STATUS_STYLES = {
  queued:     'text-slate-300',
  processing: 'text-amber-300',
  indexed:    'text-emerald-300',
  failed:     'text-rose-300',
}

function CreateWorkspace({ onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post('/workspaces', { name, description })
      setName('')
      setDescription('')
      onCreated(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create knowledge base')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="glass glow-ring rounded-2xl p-5">
      <h2 className="mb-4 text-sm font-bold uppercase tracking-widest text-indigo-300/80">New knowledge base</h2>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name — e.g. HR Policies"
          className="w-full rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60 sm:w-56"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Short description (optional)"
          className="flex-1 rounded-xl border border-white/10 bg-ink-800/80 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-slate-500 focus:border-indigo-400/60"
        />
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          disabled={busy}
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 disabled:opacity-50"
        >
          Create
        </motion.button>
      </div>
      {error && <p className="mt-2 text-sm text-rose-400">{error}</p>}
    </form>
  )
}

function UploadPanel({ workspace, onUploaded }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [message, setMessage] = useState(null)

  const upload = async (files) => {
    if (!files.length) return
    const form = new FormData()
    for (const f of files) form.append('files', f)
    setMessage(null)
    try {
      const { data } = await api.post(`/workspaces/${workspace.id}/documents`, form)
      const rejected = data.rejected?.length
        ? ` (${data.rejected.length} rejected — unsupported type)`
        : ''
      setMessage({ ok: true, text: `Queued ${data.queued.length} file(s) for ingestion.${rejected}` })
      onUploaded()
    } catch (err) {
      setMessage({ ok: false, text: err.response?.data?.detail || 'Upload failed' })
    }
  }

  return (
    <div>
      <motion.div
        animate={dragging ? { scale: 1.01 } : { scale: 1 }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          upload(Array.from(e.dataTransfer.files))
        }}
        onClick={() => inputRef.current?.click()}
        className={`group cursor-pointer rounded-2xl border-2 border-dashed px-6 py-9 text-center transition ${
          dragging
            ? 'border-indigo-400 bg-indigo-500/10'
            : 'border-white/10 bg-ink-800/40 hover:border-indigo-400/50'
        }`}
      >
        <motion.div
          animate={{ y: dragging ? -4 : 0 }}
          className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/15 ring-1 ring-indigo-400/30"
        >
          <CloudUpload size={22} className="text-indigo-300" />
        </motion.div>
        <p className="text-sm font-medium text-slate-200">
          Drop documents here or click to browse
        </p>
        <p className="mt-1 text-xs text-slate-500">
          PDF · DOCX · PPTX · HTML · TXT — upload a batch on one topic and the platform learns the domain automatically
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.html,.htm,.txt"
          className="hidden"
          onChange={(e) => {
            upload(Array.from(e.target.files))
            e.target.value = ''
          }}
        />
      </motion.div>
      {message && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-2 text-sm ${message.ok ? 'text-emerald-400' : 'text-rose-400'}`}
        >
          {message.text}
        </motion.p>
      )}
    </div>
  )
}

function DocumentsTable({ workspace, docs, onChanged }) {
  const remove = async (doc) => {
    if (!confirm(`Delete "${doc.filename}" and its indexed chunks?`)) return
    await api.delete(`/workspaces/${workspace.id}/documents/${doc.id}`)
    onChanged()
  }

  if (!docs.length) {
    return (
      <div className="glass rounded-2xl p-6 text-center text-sm text-slate-500">
        No documents uploaded yet.
      </div>
    )
  }

  return (
    <div className="glass overflow-hidden rounded-2xl">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-white/5 text-[10px] uppercase tracking-widest text-slate-500">
          <tr>
            <th className="px-4 py-3 font-semibold">File</th>
            <th className="px-4 py-3 font-semibold">Status</th>
            <th className="px-4 py-3 font-semibold">Chunks</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {docs.map((doc) => (
            <tr key={doc.id} className="transition hover:bg-white/[0.03]">
              <td className="max-w-xs px-4 py-3">
                <div className="flex items-center gap-2.5">
                  <FileText size={15} className="shrink-0 text-indigo-300/70" />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-200" title={doc.filename}>{doc.filename}</p>
                    {doc.error && <p className="truncate text-xs text-rose-400/80">{doc.error}</p>}
                  </div>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className={`text-xs font-semibold ${DOC_STATUS_STYLES[doc.status] || ''}`}>
                  {doc.status === 'processing' || doc.status === 'queued' ? '● ' : ''}{doc.status}
                </span>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-slate-400">{doc.num_chunks || '—'}</td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => remove(doc)}
                  className="rounded-lg p-1.5 text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-400"
                  title="Delete document"
                >
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ProfileViewer({ profile }) {
  if (!profile) return null
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl border border-violet-400/25 bg-gradient-to-br from-violet-500/10 via-ink-800/60 to-fuchsia-500/5 p-5"
    >
      <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-fuchsia-500/15 blur-2xl" />
      <h3 className="mb-1 text-sm font-bold uppercase tracking-widest text-violet-300">🧬 Learned knowledge profile</h3>
      <p className="mb-3 text-xs text-slate-500">Auto-generated from your documents — this drives prompts, persona and guardrails.</p>
      <p className="text-sm text-slate-200">
        <b className="text-white">{profile.domain_name}</b> — {profile.summary}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {profile.topics?.map((t) => (
          <span key={t} className="rounded-full bg-violet-500/15 px-2.5 py-1 text-xs text-violet-200 ring-1 ring-violet-400/25">
            {t}
          </span>
        ))}
      </div>
      {profile.terminology?.length > 0 && (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer text-slate-400 transition hover:text-slate-200">
            Terminology ({profile.terminology.length})
          </summary>
          <ul className="mt-2 space-y-1 text-slate-400">
            {profile.terminology.map((t) => (
              <li key={t.term}><b className="text-slate-200">{t.term}</b> — {t.definition}</li>
            ))}
          </ul>
        </details>
      )}
      {profile.sample_questions?.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-slate-400 transition hover:text-slate-200">
            Example questions it can now answer
          </summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-slate-400">
            {profile.sample_questions.map((q) => <li key={q}>{q}</li>)}
          </ul>
        </details>
      )}
    </motion.div>
  )
}

export default function WorkspacesTab() {
  const [workspaces, setWorkspaces] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [docs, setDocs] = useState([])
  const [profile, setProfile] = useState(null)
  const [relearning, setRelearning] = useState(false)

  const loadWorkspaces = useCallback(async (selectId) => {
    const { data } = await api.get('/workspaces')
    setWorkspaces(data)
    setSelectedId((cur) => selectId ?? cur ?? (data[0] ? data[0].id : null))
  }, [])

  useEffect(() => { loadWorkspaces() }, [loadWorkspaces])

  const selected = workspaces.find((w) => w.id === selectedId)

  // Poll while anything is in flight — live progress in the UI
  useEffect(() => {
    if (!selected) return
    const active =
      ['ingesting', 'analyzing'].includes(selected.status) ||
      docs.some((d) => ['queued', 'processing'].includes(d.status))

    const loadDocs = async () => {
      const [docsRes, profileRes] = await Promise.all([
        api.get(`/workspaces/${selected.id}/documents`),
        api.get(`/workspaces/${selected.id}/profile`),
      ])
      setDocs(docsRes.data)
      setProfile(profileRes.data.profile)
      loadWorkspaces()
    }

    loadDocs()
    if (active) {
      const t = setInterval(loadDocs, 2500)
      return () => clearInterval(t)
    }
  }, [selected?.id, selected?.status, docs.map((d) => d.status).join(), loadWorkspaces])

  const relearn = async () => {
    setRelearning(true)
    try {
      await api.post(`/workspaces/${selected.id}/reanalyze`)
      loadWorkspaces()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not start re-analysis')
    } finally {
      setRelearning(false)
    }
  }

  const removeWorkspace = async (ws) => {
    if (!confirm(`Delete knowledge base "${ws.name}" with ALL its documents and learned profile?`)) return
    await api.delete(`/workspaces/${ws.id}`)
    setSelectedId(null)
    setDocs([])
    setProfile(null)
    loadWorkspaces()
  }

  return (
    <div className="space-y-6">
      <CreateWorkspace onCreated={(ws) => loadWorkspaces(ws.id)} />

      <div className="flex flex-wrap gap-2.5">
        {workspaces.map((ws, i) => (
          <motion.button
            key={ws.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            onClick={() => setSelectedId(ws.id)}
            className={`flex items-center gap-2.5 rounded-2xl px-4 py-3 text-sm transition ${
              selectedId === ws.id
                ? 'glass-strong text-white ring-2 ring-indigo-400/50'
                : 'glass text-slate-300 hover:ring-1 hover:ring-white/20'
            }`}
          >
            <span className="font-semibold">{ws.name}</span>
            <StatusPill status={ws.status} />
          </motion.button>
        ))}
        {workspaces.length === 0 && (
          <p className="text-sm text-slate-500">Create your first knowledge base above.</p>
        )}
      </div>

      {selected && (
        <motion.div
          key={selected.id}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">{selected.name}</h2>
              {selected.description && <p className="text-sm text-slate-400">{selected.description}</p>}
            </div>
            <div className="flex gap-2">
              <button
                onClick={relearn}
                disabled={relearning || ['ingesting', 'analyzing'].includes(selected.status)}
                title="Re-run the corpus analyzer on all indexed documents"
                className="rounded-xl border border-indigo-400/40 px-3.5 py-2 text-sm font-medium text-indigo-300 transition hover:bg-indigo-500/10 disabled:opacity-40"
              >
                {relearning || selected.status === 'analyzing' ? 'Re-learning…' : '↻ Re-learn profile'}
              </button>
              <button
                onClick={() => removeWorkspace(selected)}
                className="rounded-xl border border-rose-500/30 px-3.5 py-2 text-sm font-medium text-rose-400 transition hover:bg-rose-500/10"
              >
                Delete KB
              </button>
            </div>
          </div>

          <ProfileViewer profile={profile} />
          <UploadPanel workspace={selected} onUploaded={() => loadWorkspaces(selected.id)} />
          <div>
            <h3 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-400">Documents</h3>
            <DocumentsTable workspace={selected} docs={docs} onChanged={loadWorkspaces} />
          </div>
        </motion.div>
      )}
    </div>
  )
}
