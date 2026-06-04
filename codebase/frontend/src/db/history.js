import initSqlJs from 'sql.js'
import sqlWasmUrl from 'sql.js/dist/sql-wasm.wasm?url'

const STORAGE_KEY = 'medchat-sqlite-v1'
const MAX_SESSIONS = 30

let _db = null

// ─── Init ─────────────────────────────────────────────────────────────────────

async function getDb() {
  if (_db) return _db

  const SQL = await initSqlJs({ locateFile: () => sqlWasmUrl })

  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    const bytes = Uint8Array.from(atob(saved), (c) => c.charCodeAt(0))
    _db = new SQL.Database(bytes)
  } else {
    _db = new SQL.Database()
  }

  _db.run(`
    CREATE TABLE IF NOT EXISTS chat_history (
      id           TEXT PRIMARY KEY,
      saved_at     TEXT NOT NULL,
      doctor_name  TEXT,
      clinic       TEXT,
      issued_at    TEXT,
      status       TEXT,
      confidence   REAL,
      prescription TEXT NOT NULL,
      messages     TEXT NOT NULL
    )
  `)

  flush()
  return _db
}

function flush() {
  if (!_db) return
  const data = _db.export()
  let binary = ''
  for (let i = 0; i < data.byteLength; i++) binary += String.fromCharCode(data[i])
  localStorage.setItem(STORAGE_KEY, btoa(binary))
}

// ─── Public API ───────────────────────────────────────────────────────────────

export async function getAllSessions() {
  const db = await getDb()
  const result = db.exec(
    'SELECT id, saved_at, prescription, messages FROM chat_history ORDER BY saved_at DESC LIMIT ?',
    [MAX_SESSIONS],
  )
  if (!result.length) return []
  return result[0].values.map(([id, savedAt, prescription, messages]) => ({
    id,
    savedAt,
    prescription: JSON.parse(prescription),
    messages: JSON.parse(messages),
  }))
}

export async function upsertSession(prescription, messages) {
  if (!prescription) return
  const db = await getDb()
  db.run(
    `INSERT OR REPLACE INTO chat_history
       (id, saved_at, doctor_name, clinic, issued_at, status, confidence, prescription, messages)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      prescription.prescriptionId,
      new Date().toISOString(),
      prescription.doctorName ?? null,
      prescription.clinic ?? null,
      prescription.issuedAt ?? null,
      prescription.status ?? null,
      prescription.confidence ?? null,
      JSON.stringify(prescription),
      JSON.stringify(messages),
    ],
  )
  flush()
}

export async function removeSession(id) {
  const db = await getDb()
  db.run('DELETE FROM chat_history WHERE id = ?', [id])
  flush()
}

export async function clearAllSessions() {
  const db = await getDb()
  db.run('DELETE FROM chat_history')
  flush()
}

/** Export the raw SQLite database as a downloadable .db file */
export function exportDatabase() {
  if (!_db) return
  const data = _db.export()
  const blob = new Blob([data], { type: 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `medchat-history-${new Date().toISOString().slice(0, 10)}.db`
  a.click()
  URL.revokeObjectURL(url)
}
