import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  BotMessageSquare,
  Check,
  ChevronDown,
  ChevronUp,
  Clock3,
  Download,
  FileText,
  History,
  Info,
  MapPin,
  MessageCircle,
  Pill,
  SendHorizontal,
  ShieldCheck,
  Stethoscope,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react'
import { api } from './api/client.js'
import { getAllSessions, upsertSession, removeSession, exportDatabase } from './db/history.js'

const initialMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    text: 'Chào bạn, tôi là dược sĩ AI MedChat. Hãy tải ảnh đơn thuốc để tôi đọc, tóm tắt và giúp bạn hỏi đáp an toàn hơn.',
  },
]


const navItems = [
  ['chat', 'Đọc đơn AI', 'chat'],
  ['file', 'Đơn của tôi', 'history'],
  ['clock', 'Nhắc uống thuốc', 'clock'],
  ['map', 'Nhà thuốc gần đây', 'map'],
]

function App() {
  const fileInputRef = useRef(null)
  const [messages, setMessages] = useState(initialMessages)
  const [quickReplies, setQuickReplies] = useState(['Tải ảnh đơn thuốc', 'Quy trình an toàn'])
  const [prescription, setPrescription] = useState(null)
  const [chatSessionId, setChatSessionId] = useState('')
  const [reminders, setReminders] = useState([])
  const [specialists, setSpecialists] = useState([])
  const [appointment, setAppointment] = useState(null)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [panelOpen, setPanelOpen] = useState(false)
  const [editingMedicationId, setEditingMedicationId] = useState('')
  const [editName, setEditName] = useState('')
  const [activeNav, setActiveNav] = useState('chat')
  const [history, setHistory] = useState([])
  const [dbReady, setDbReady] = useState(false)

  useEffect(() => {
    getAllSessions()
      .then((rows) => {
        setHistory(rows)
        setDbReady(true)
      })
      .catch(() => setDbReady(true))
  }, [])

  const highRisk = useMemo(
    () => prescription?.medications?.some((item) => item.risk === 'high') || false,
    [prescription],
  )

  async function saveCurrentSession(currentPrescription, currentMessages) {
    if (!currentPrescription) return
    await upsertSession(currentPrescription, currentMessages)
    const rows = await getAllSessions()
    setHistory(rows)
  }

  async function deleteSession(id) {
    await removeSession(id)
    setHistory((prev) => prev.filter((h) => h.id !== id))
  }

  function addMessage(role, text, meta) {
    setMessages((items) => [
      ...items,
      { id: `${Date.now()}-${Math.random()}`, role, text, meta },
    ])
  }

  async function runTask(task) {
    setBusy(true)
    setError('')
    try {
      await task()
    } catch (err) {
      setError(err.message || 'Có lỗi xảy ra. Vui lòng thử lại.')
    } finally {
      setBusy(false)
    }
  }

  async function handleUpload(file) {
    if (!file) return
    await saveCurrentSession(prescription, messages)
    await runTask(async () => {
      addMessage('user', `Đã chọn tệp: ${file.name}`)
      const result = await api.scanPrescription(file)
      const nextSessionId =
        crypto.randomUUID?.() || `${result.prescriptionId}-${Date.now()}-${Math.random()}`
      setPrescription(result)
      setChatSessionId(nextSessionId)
      setReminders([])
      setSpecialists([])
      setAppointment(null)
      setMessages([
        ...initialMessages,
        { id: `${Date.now()}-file`, role: 'user', text: `Đã chọn tệp: ${file.name}` },
      ])
      setPanelOpen(true)
      addMessage(
        'assistant',
        `Tôi đã đọc được ${result.medications.length} thuốc với độ tin cậy ${Math.round(
          result.confidence * 100,
        )}%. Vui lòng kiểm tra tên thuốc và xác nhận trước khi hỏi đáp.`,
        'scan',
      )
      setQuickReplies(['Xác nhận đơn thuốc', 'Có sai tên thuốc', 'Xem cảnh báo'])
    })
  }

  async function confirmPrescription() {
    if (!prescription) return
    const unclearMeds = prescription.medications.filter((m) => m.confidence < 0.7)
    if (unclearMeds.length > 0) {
      addMessage(
        'assistant',
        `Còn ${unclearMeds.length} thuốc chưa được nhận dạng rõ ràng. Vui lòng nhấn "Sửa" và nhập đúng tên thuốc trước khi xác nhận.`,
      )
      setQuickReplies(['Có sai tên thuốc', 'Sửa thuốc khác'])
      return
    }
    await runTask(async () => {
      // Confirm the prescription
      const result = await api.confirmPrescription(prescription.prescriptionId)
      
      // Analyze to get drug info from local database
      let analysisData = null
      try {
        const analyzeResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'}/prescription/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prescription_id: prescription.prescriptionId })
        })
        if (analyzeResponse.ok) {
          analysisData = await analyzeResponse.json()
        }
      } catch (e) {
        console.log('Analysis not available, using basic info')
      }
      
      // Merge analysis data into prescription and preserve metadata like doctorName
      const mergedPrescription = { ...prescription, ...result }
      if (analysisData && analysisData.medications) {
        mergedPrescription.medications = result.medications.map((med, idx) => {
          const analysis = analysisData.medications[idx] || {}
          return {
            ...med,
            category_vi: analysis.category_vi || med.category_vi,
            uses_vi: analysis.uses_vi || [],
            important_notes_vi: analysis.important_notes_vi || [],
            risk_level: analysis.risk_level || 'normal',
            found: analysis.found,
          }
        })
        mergedPrescription.analysis = analysisData
      }
      
      setPrescription(mergedPrescription)
      addMessage(
        'assistant',
        'Đơn thuốc đã được xác nhận. Bây giờ bạn có thể hỏi về công dụng, cách uống, tác dụng phụ hoặc tạo nhắc uống thuốc.',
        'confirmed',
      )
      setQuickReplies(['Tác dụng phụ?', 'Lịch uống trong ngày', 'Tạo nhắc uống thuốc'])
    })
  }

  async function updateMedication() {
    if (!prescription || !editingMedicationId || !editName.trim()) return
    await runTask(async () => {
      const result = await api.updateMedication(prescription.prescriptionId, editingMedicationId, {
        name: editName.trim(),
      })
      setPrescription(result)
      setEditingMedicationId('')
      setEditName('')
      addMessage('assistant', 'Đã cập nhật tên thuốc. Hãy kiểm tra lại danh sách trước khi xác nhận.')
      setQuickReplies(['Xác nhận đơn thuốc', 'Sửa thuốc khác'])
    })
  }

  async function sendMessage(text = input) {
    const trimmed = text.trim()
    const normalized = normalizeText(trimmed)
    if (!trimmed) return

    if (normalized.includes('tai anh') || normalized.includes('upload')) {
      fileInputRef.current?.click()
      return
    }

    if (normalized.includes('xac nhan')) {
      await confirmPrescription()
      return
    }

    if (normalized.includes('sai ten') || normalized.includes('sua thuoc')) {
      const first = prescription?.medications?.[0]
      if (first) {
        setEditingMedicationId(first.id)
        setEditName(first.name)
        addMessage('assistant', 'Chọn thuốc trong panel bên phải và nhập tên đúng để cập nhật.')
      }
      return
    }

    if (normalized.includes('tao nhac')) {
      await createReminders()
      return
    }

    if (normalized.includes('dat lich')) {
      await loadSpecialists()
      return
    }

    if (!prescription) {
      addMessage('assistant', 'Vui lòng tải ảnh đơn thuốc trước để tôi có ngữ cảnh trả lời.')
      return
    }

    if (prescription.status !== 'confirmed') {
      addMessage(
        'assistant',
        'Tôi cần bạn xác nhận tên thuốc trước khi giải thích để tránh nhầm lẫn nguy hiểm.',
      )
      setQuickReplies(['Xác nhận đơn thuốc', 'Có sai tên thuốc'])
      return
    }

    if (highRisk) {
      addMessage(
        'assistant',
        'Đơn thuốc này chứa thuốc có nguy cơ cao. Để đảm bảo an toàn, tôi không thể tư vấn trực tiếp. Vui lòng đặt lịch với bác sĩ.',
      )
      setQuickReplies(['Đặt lịch với bác sĩ', 'Xem cảnh báo'])
      return
    }

    setInput('')
    addMessage('user', trimmed)
    await runTask(async () => {
      const result = await api.sendMessage(prescription.prescriptionId, trimmed, chatSessionId)
      if (result.sessionId && result.sessionId !== chatSessionId) {
        setChatSessionId(result.sessionId)
      }
      addMessage('assistant', result.answer)
      setQuickReplies(result.quickReplies || [])
    })
  }

  async function createReminders() {
    if (!prescription) return
    await runTask(async () => {
      const result = await api.createReminders(prescription.prescriptionId, 60)
      setReminders(result.reminders)
      const timeCount = new Set(result.reminders.map((item) => item.time)).size
      addMessage('assistant', `Đã tạo ${timeCount} lịch nhắc uống thuốc trước ${result.leadMinutes} phút.`)
      setQuickReplies(['Tác dụng phụ?', 'Lịch uống trong ngày'])
    })
  }

  async function loadSpecialists() {
    if (!prescription) return
    await runTask(async () => {
      const result = await api.getSpecialists(prescription.prescriptionId)
      setSpecialists(result)
      setPanelOpen(true)
      addMessage('assistant', 'Đã tìm thấy lịch tư vấn phù hợp. Bạn có thể chọn lịch trong panel bên phải.')
      setQuickReplies(['Tạo nhắc uống thuốc', 'Hỏi về Prednisolone'])
    })
  }

  async function bookSpecialist(specialist) {
    if (!prescription) return
    await runTask(async () => {
      const result = await api.createAppointment({
        prescriptionId: prescription.prescriptionId,
        specialistId: specialist.id,
        slot: specialist.nextSlot,
      })
      setAppointment({ ...result, specialist })
      addMessage('assistant', `Đã đặt lịch với ${specialist.name}. Hệ thống sẽ gửi nhắc lịch trước buổi tư vấn.`)
    })
  }

  return (
    <div className="grid h-dvh min-w-80 grid-cols-1 overflow-hidden bg-[#eef5ff] text-slate-900 [font-family:'Be_Vietnam_Pro',ui-sans-serif,system-ui,sans-serif] lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)_360px]">
      <Sidebar usingMock={api.usingMock} activeNav={activeNav} onNavChange={setActiveNav} />

      <main className="flex min-h-0 min-w-0 flex-col">
        <header className="flex min-h-20 items-center gap-3 border-b border-blue-100 bg-white/90 px-4 shadow-sm shadow-blue-950/5 backdrop-blur md:px-6">
          <div className={`grid size-11 shrink-0 place-items-center rounded-2xl text-white shadow-lg ${activeNav === 'history' ? 'bg-gradient-to-br from-slate-700 to-slate-500 shadow-slate-200' : 'bg-gradient-to-br from-blue-700 to-cyan-500 shadow-blue-200'}`}>
            <Icon name={activeNav === 'history' ? 'history' : 'chat'} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase text-blue-700">Dược sĩ AI</p>
            <h1 className="truncate text-lg font-bold text-slate-950 md:text-xl">
              {activeNav === 'history' ? 'Lịch sử đơn thuốc' : 'MedChat đơn thuốc'}
            </h1>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button className="hidden size-10 place-items-center rounded-xl bg-blue-50 text-blue-800 ring-1 ring-blue-100 md:grid" type="button" title="Thông tin">
              <Icon name="info" />
            </button>
            {activeNav === 'chat' ? (
              <button
                className="inline-flex h-10 items-center rounded-xl border border-blue-200 bg-white px-4 text-sm font-bold text-blue-800 shadow-sm xl:hidden"
                type="button"
                onClick={() => setPanelOpen(true)}
              >
                Đơn thuốc
              </button>
            ) : null}
          </div>
        </header>

        {activeNav === 'history' ? (
          <HistoryView history={history} onDelete={deleteSession} dbReady={dbReady} />
        ) : (
          <>
            <ChatWindow messages={messages} busy={busy} highRisk={highRisk} />

            {error ? (
              <div className="mx-4 mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 md:mx-6">
                {error}
              </div>
            ) : null}

            <QuickReplies items={quickReplies} onPick={sendMessage} />

            <Composer
              input={input}
              setInput={setInput}
              onSend={() => sendMessage()}
              onUploadClick={() => fileInputRef.current?.click()}
              busy={busy}
            />

            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept="image/*,.pdf"
              onChange={(event) => handleUpload(event.target.files?.[0])}
            />
          </>
        )}
      </main>

      <PrescriptionPanel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        prescription={prescription}
        reminders={reminders}
        specialists={specialists}
        appointment={appointment}
        editingMedicationId={editingMedicationId}
        editName={editName}
        setEditName={setEditName}
        startEdit={(item) => {
          setEditingMedicationId(item.id)
          setEditName(item.name)
        }}
        cancelEdit={() => setEditingMedicationId('')}
        updateMedication={updateMedication}
        confirmPrescription={confirmPrescription}
        createReminders={createReminders}
        loadSpecialists={loadSpecialists}
        bookSpecialist={bookSpecialist}
        busy={busy}
      />
    </div>
  )
}

function Sidebar({ usingMock, activeNav, onNavChange }) {
  return (
    <aside className="hidden flex-col gap-6 bg-[#071a33] px-4 py-6 text-blue-100 lg:flex">
      <div className="flex items-center gap-3">
        <div className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-400 text-white shadow-lg shadow-blue-950/30">
          <Icon name="pill" />
        </div>
        <div>
          <strong className="block text-lg text-white">MedChat</strong>
          <span className="block text-xs text-blue-200">Prescription assistant</span>
        </div>
      </div>

      <nav className="grid gap-2" aria-label="Main">
        {navItems.map(([icon, label, navId]) => (
          <button
            className={`flex h-11 items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold transition ${
              activeNav === navId ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/30' : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
            type="button"
            key={label}
            onClick={() => onNavChange(navId)}
          >
            <Icon name={icon} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="mt-auto rounded-2xl border border-white/10 bg-white/10 p-4">
        <p className="text-xs font-bold uppercase text-blue-200">Chế độ API</p>
        <strong className="mt-2 block text-white">{usingMock ? 'Mock local' : 'Backend live'}</strong>
        <span className="mt-2 block text-xs leading-5 text-blue-100">
          {usingMock ? 'Đặt VITE_API_BASE_URL để nối API thật.' : 'Đang kết nối qua adapter.'}
        </span>
      </div>
    </aside>
  )
}

function ChatWindow({ messages, busy, highRisk }) {
  return (
    <section className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto bg-[linear-gradient(#d7e8ff_1px,transparent_1px),linear-gradient(90deg,#d7e8ff_1px,transparent_1px)] bg-[size:32px_32px] bg-[#f4f8ff] p-4 md:p-6" aria-live="polite">
      <div className="flex w-full max-w-2xl items-center gap-3 rounded-2xl border border-blue-100 bg-white/95 p-4 shadow-xl shadow-blue-950/5">
        <div className={`grid size-10 shrink-0 place-items-center rounded-xl ${highRisk ? 'bg-rose-100 text-rose-700' : 'bg-blue-100 text-blue-800'}`}>
          <Icon name={highRisk ? 'alert' : 'shield'} />
        </div>
        <div>
          <strong className="block text-sm text-slate-950">
            {highRisk ? 'Đơn có thuốc cần theo dõi' : 'Xác nhận trước khi giải thích'}
          </strong>
          <span className="mt-1 block text-sm text-slate-500">AI chỉ giải thích thông tin thuốc trong đơn đã xác nhận.</span>
        </div>
      </div>

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {busy ? (
        <div className="flex max-w-[82%] items-end gap-3 self-start">
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-blue-700 text-white">
            <Icon name="chat" />
          </div>
          <div className="flex gap-1 rounded-2xl rounded-bl-md bg-white px-4 py-4 shadow-lg shadow-blue-950/5">
            <span className="size-2 animate-bounce rounded-full bg-blue-300" />
            <span className="size-2 animate-bounce rounded-full bg-blue-500 [animation-delay:150ms]" />
            <span className="size-2 animate-bounce rounded-full bg-cyan-500 [animation-delay:300ms]" />
          </div>
        </div>
      ) : null}
    </section>
  )
}

function MessageBubble({ message }) {
  const isAssistant = message.role === 'assistant'
  return (
    <div className={`flex max-w-[92%] gap-3 md:max-w-[82%] ${isAssistant ? 'self-start' : 'self-end'}`}>
      {isAssistant ? (
        <div className="grid size-8 shrink-0 place-items-center self-end rounded-full bg-blue-700 text-white">
          <Icon name="bot" />
        </div>
      ) : null}
      <div
        className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-lg ${
          isAssistant
            ? 'rounded-bl-md bg-white text-slate-800 shadow-blue-950/5'
            : 'rounded-br-md bg-gradient-to-br from-blue-700 to-blue-600 text-white shadow-blue-200'
        }`}
      >
        <FormattedMessage text={message.text} />
      </div>
    </div>
  )
}

function FormattedMessage({ text }) {
  return (
    <div className="whitespace-pre-wrap break-words">
      {String(text)
        .split('\n')
        .map((line, lineIndex, lines) => (
          <span key={`${line}-${lineIndex}`}>
            {renderInlineMarkdown(line)}
            {lineIndex < lines.length - 1 ? <br /> : null}
          </span>
        ))}
    </div>
  )
}

function renderInlineMarkdown(line) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${part}-${index}`} className="font-bold">{part.slice(2, -2)}</strong>
    }
    return <span key={`${part}-${index}`}>{part}</span>
  })
}

function QuickReplies({ items, onPick }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap gap-2 border-t border-blue-100 bg-white/90 px-4 py-3 md:px-6">
      {items.map((item) => (
        <button
          className="h-9 rounded-full border border-blue-200 bg-white px-4 text-sm font-bold text-blue-800 shadow-sm transition hover:bg-blue-50"
          type="button"
          key={item}
          onClick={() => onPick(item)}
        >
          {item}
        </button>
      ))}
    </div>
  )
}

function Composer({ input, setInput, onSend, onUploadClick, busy }) {
  return (
    <div className="flex items-center gap-3 border-t border-blue-100 bg-white px-4 py-4 md:px-6">
      <button className="grid size-11 shrink-0 place-items-center rounded-xl border border-blue-200 bg-blue-50 text-blue-800" type="button" onClick={onUploadClick} title="Tải đơn thuốc">
        <Icon name="upload" />
      </button>
      <input
        className="h-11 min-w-0 flex-1 rounded-xl border border-blue-100 bg-blue-50 px-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') onSend()
        }}
        placeholder="Hỏi về cách uống, tác dụng phụ, lịch nhắc..."
      />
      <button className="grid size-11 shrink-0 place-items-center rounded-xl bg-blue-700 text-white shadow-lg shadow-blue-200 disabled:cursor-wait disabled:opacity-60" type="button" onClick={onSend} disabled={busy}>
        <Icon name="send" />
      </button>
    </div>
  )
}

function PrescriptionPanel(props) {
  const {
    open,
    onClose,
    prescription,
    reminders,
    specialists,
    appointment,
    editingMedicationId,
    editName,
    setEditName,
    startEdit,
    cancelEdit,
    updateMedication,
    confirmPrescription,
    createReminders,
    loadSpecialists,
    bookSpecialist,
    busy,
  } = props

  return (
    <>
      <button
        className={`fixed inset-0 z-30 bg-slate-950/30 transition xl:hidden ${open ? 'block' : 'hidden'}`}
        type="button"
        onClick={onClose}
        aria-label="Đóng panel"
      />
      <aside
        className={`fixed right-0 top-0 z-40 flex h-dvh w-[min(390px,92vw)] flex-col overflow-y-auto border-l border-blue-100 bg-white shadow-2xl shadow-slate-950/20 transition-transform xl:static xl:z-auto xl:w-auto xl:translate-x-0 xl:shadow-none ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-start justify-between gap-3 border-b border-blue-100 bg-blue-50/90 px-5 py-5">
          <div>
            <p className="text-xs font-bold uppercase text-blue-700">Đơn thuốc hiện tại</p>
            <h2 className="mt-1 text-lg font-bold text-slate-950">{prescription ? `BS. ${prescription.doctorName}` : 'Chưa có dữ liệu'}</h2>
          </div>
          <button className="grid size-9 place-items-center rounded-xl bg-white text-blue-800 ring-1 ring-blue-100 xl:hidden" type="button" onClick={onClose} title="Đóng">
            <Icon name="close" />
          </button>
        </div>

        {!prescription ? (
          <div className="m-5 grid place-items-center gap-3 rounded-2xl border border-dashed border-blue-200 p-8 text-center text-slate-500">
            <div className="grid size-12 place-items-center rounded-2xl bg-blue-50 text-blue-800">
              <Icon name="upload" />
            </div>
            <strong className="text-slate-800">Tải ảnh đơn thuốc</strong>
            <span className="max-w-60 text-sm leading-6">Kết quả OCR, cảnh báo và nhắc uống thuốc sẽ xuất hiện tại đây.</span>
          </div>
        ) : (
          <>
            <div className="mx-5 mt-5 flex items-center gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4">
              <span className={`size-3 rounded-full ${prescription.status === 'confirmed' ? 'bg-emerald-500' : 'bg-amber-400'}`} />
              <div>
                <strong className="block text-sm text-slate-900">
                  {prescription.status === 'confirmed' ? 'Đã xác nhận' : 'Cần bạn kiểm tra'}
                </strong>
                <span className="mt-1 block text-xs text-slate-500">Độ tin cậy OCR {Math.round(prescription.confidence * 100)}%</span>
              </div>
            </div>

            <section className="border-b border-blue-50 p-5">
              <SectionTitle title="Danh sách thuốc" meta={`${prescription.medications.length} mục`} />
              <div className="grid gap-3">
                {prescription.medications.map((item) => (
                  <div className={`grid grid-cols-[36px_minmax(0,1fr)_auto] gap-3 rounded-2xl border p-3 ${item.risk === 'high' ? 'border-rose-200 bg-rose-50' : 'border-blue-100 bg-white'}`} key={item.id}>
                    <div className={`grid size-9 place-items-center rounded-xl ${item.risk === 'high' ? 'bg-rose-100 text-rose-700' : 'bg-blue-50 text-blue-800'}`}>
                      <Icon name={item.risk === 'high' ? 'alert' : 'pill'} />
                    </div>
                    <div className="min-w-0">
                      {editingMedicationId === item.id ? (
                        <div className="grid grid-cols-[1fr_auto_auto] gap-2">
                          <input className="min-w-0 rounded-lg border border-blue-200 px-2 text-sm outline-none focus:ring-2 focus:ring-blue-100" value={editName} onChange={(event) => setEditName(event.target.value)} />
                          <button className="rounded-lg bg-blue-700 px-3 text-sm font-bold text-white" type="button" onClick={updateMedication} disabled={busy}>
                            Lưu
                          </button>
                          <button className="rounded-lg bg-slate-100 px-3 text-sm font-bold text-slate-600" type="button" onClick={cancelEdit}>
                            Hủy
                          </button>
                        </div>
                      ) : (
                        <>
                          <strong className="block truncate text-sm text-slate-950">
                            {item.name} {item.strength}
                          </strong>
                          <span className="mt-1 block text-xs leading-5 text-slate-500">{item.dose} · {item.schedule} · {item.duration}</span>
                          <small className="mt-1 block text-xs font-semibold text-blue-700">Confidence {Math.round(item.confidence * 100)}%</small>
                        </>
                      )}
                    </div>
                    {editingMedicationId !== item.id ? (
                      <button className="text-sm font-bold text-blue-800" type="button" onClick={() => startEdit(item)}>
                        Sửa
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>

            {prescription.warnings?.length ? (
              <section className="mx-5 mt-5 flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
                <Icon name="alert" />
                <div>
                  <strong className="block text-sm">{prescription.warnings[0].title}</strong>
                  <span className="mt-1 block text-xs leading-5">{prescription.warnings[0].detail}</span>
                </div>
              </section>
            ) : null}

            <div className="grid gap-2 border-b border-blue-50 p-5">
              <button type="button" className="h-11 rounded-xl bg-blue-700 text-sm font-bold text-white shadow-lg shadow-blue-100" onClick={confirmPrescription} disabled={busy}>
                Xác nhận đơn
              </button>
              <button type="button" className="h-11 rounded-xl border border-blue-200 bg-white text-sm font-bold text-blue-800" onClick={createReminders} disabled={busy}>
                Tạo nhắc
              </button>
              <button type="button" className="h-11 rounded-xl border border-blue-200 bg-white text-sm font-bold text-blue-800" onClick={loadSpecialists} disabled={busy}>
                Đặt lịch tư vấn riêng
              </button>
            </div>

            <RemindersByTime
              title="Nhắc uống thuốc"
              empty="Chưa có nhắc nhở"
              reminders={reminders}
              prescription={prescription}
            />

            <section className="border-b border-blue-50 p-5">
              <SectionTitle title="Chuyên gia phù hợp" meta={specialists.length ? `${specialists.length} lịch` : 'Chưa tìm'} />
              {specialists.length ? (
                <div className="grid gap-3">
                  {specialists.map((item) => (
                    <div className="grid gap-1 rounded-2xl border border-blue-100 bg-white p-3" key={item.id}>
                      <strong className="text-sm text-slate-950">{item.name}</strong>
                      <span className="text-xs text-slate-500">{item.specialty} · {item.location}</span>
                      <small className="text-xs font-semibold text-blue-700">{formatSlot(item.nextSlot)}</small>
                      <button className="mt-2 h-9 rounded-xl bg-[#071a33] text-sm font-bold text-white" type="button" onClick={() => bookSpecialist(item)} disabled={busy}>
                        Đặt lịch
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-500">Dùng khi đơn có thuốc cần theo dõi hoặc bạn cần gặp dược sĩ.</p>
              )}
            </section>

            {appointment ? (
              <section className="m-5 flex gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">
                <Icon name="check" />
                <div>
                  <strong className="block text-sm">Đã đặt lịch</strong>
                  <span className="mt-1 block text-xs leading-5">{appointment.specialist.name} · {formatSlot(appointment.slot)}</span>
                </div>
              </section>
            ) : null}
          </>
        )}
      </aside>
    </>
  )
}

function RemindersByTime({ title, empty, reminders, prescription }) {
  const medicationMap = (prescription?.medications || []).reduce((acc, med) => {
    acc[med.id] = med
    return acc
  }, {})

  const parseTime = (time) => {
    const [hours, minutes] = (time || '00:00').split(':').map(Number)
    return hours * 60 + minutes
  }

  const formatTime = (minutes) => {
    const h = String(Math.floor(minutes / 60)).padStart(2, '0')
    const m = String(minutes % 60).padStart(2, '0')
    return `${h}:${m}`
  }

  const groups = reminders
    .slice()
    .filter((item) => item.time)
    .sort((a, b) => parseTime(a.time) - parseTime(b.time))
    .reduce((acc, item) => {
      const itemMinutes = parseTime(item.time)
      const current = acc[acc.length - 1]
      if (!current) {
        acc.push({ start: itemMinutes, end: itemMinutes, items: [item] })
        return acc
      }

      if (itemMinutes - current.end <= 30) {
        current.end = Math.max(current.end, itemMinutes)
        current.items.push(item)
      } else {
        acc.push({ start: itemMinutes, end: itemMinutes, items: [item] })
      }
      return acc
    }, [])

  return (
    <section className="border-b border-blue-50 p-5">
      <SectionTitle title={title} meta={groups.length ? `${reminders.length} nhắc` : empty} />
      {groups.length ? (
        <div className="grid gap-4">
          {groups.map((group) => {
            const label = group.start === group.end ? formatTime(group.start) : `${formatTime(group.start)} - ${formatTime(group.end)}`
            return (
              <div key={label} className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <strong className="text-sm font-bold text-slate-950">{label}</strong>
                  <span className="text-xs font-semibold text-slate-500">{group.items.length} thuốc</span>
                </div>
                <div className="grid gap-2">
                  {group.items.map((item) => {
                    const med = medicationMap[item.medicationId]
                    const name = med?.name || item.label
                    const details = med?.dose || ''
                    return (
                      <div key={`${item.medicationId}-${item.time}-${item.label}`} className="rounded-xl bg-white px-3 py-3 shadow-sm">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <strong className="text-sm text-slate-950">{name}</strong>
                          <span className="text-xs text-slate-500">{details || item.label}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}

function SectionTitle({ title, meta }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <span className="text-sm font-bold text-slate-950">{title}</span>
      <small className="text-xs font-bold text-slate-400">{meta}</small>
    </div>
  )
}

function HistoryView({ history, onDelete, dbReady }) {
  const [openId, setOpenId] = useState(null)

  if (!dbReady) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-slate-400">
        <div className="flex gap-1">
          <span className="size-2 animate-bounce rounded-full bg-blue-300" />
          <span className="size-2 animate-bounce rounded-full bg-blue-500 [animation-delay:150ms]" />
          <span className="size-2 animate-bounce rounded-full bg-cyan-500 [animation-delay:300ms]" />
        </div>
        <p className="text-sm text-slate-400">Đang khởi động cơ sở dữ liệu...</p>
      </div>
    )
  }

  if (!history.length) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-slate-400">
        <div className="grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-400">
          <History className="h-7 w-7" strokeWidth={1.8} />
        </div>
        <p className="text-sm font-semibold text-slate-500">Chưa có lịch sử chat nào</p>
        <p className="max-w-xs text-center text-xs leading-5 text-slate-400">
          Mỗi lần bạn tải đơn thuốc mới, phiên chat cũ sẽ được lưu vào SQLite và hiển thị tại đây.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4 md:p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900">{history.length} phiên đã lưu</h2>
        <button
          className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-xs font-bold text-blue-700 shadow-sm transition hover:bg-blue-50"
          type="button"
          onClick={exportDatabase}
          title="Tải file .db về máy, mở bằng DB Browser for SQLite"
        >
          <Download className="h-3.5 w-3.5" />
          Export .db
        </button>
      </div>

      {history.map((session) => {
        const isOpen = openId === session.id
        const userMsgs = session.messages.filter((m) => m.role === 'user' && !m.text.startsWith('Đã chọn tệp:')).length
        return (
          <div key={session.id} className="overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm">
            <button
              className="flex w-full items-center gap-3 p-4 text-left transition hover:bg-blue-50/50"
              type="button"
              onClick={() => setOpenId(isOpen ? null : session.id)}
            >
              <div className={`grid size-10 shrink-0 place-items-center rounded-xl ${session.prescription.status === 'confirmed' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                <Icon name="file" />
              </div>
              <div className="min-w-0 flex-1">
                <strong className="block truncate text-sm text-slate-900">{session.prescription.doctorName}</strong>
                <span className="block truncate text-xs text-slate-500">{session.prescription.clinic}</span>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`size-2 rounded-full ${session.prescription.status === 'confirmed' ? 'bg-emerald-500' : 'bg-amber-400'}`} />
                  <small className="text-xs text-slate-400">
                    {new Date(session.savedAt).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </small>
                  <small className="text-xs font-semibold text-blue-700">{userMsgs} câu hỏi</small>
                </div>
              </div>
              <div className="shrink-0 text-slate-400">
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </div>
            </button>

            {isOpen ? (
              <div className="border-t border-blue-50">
                <div className="flex flex-col gap-3 overflow-y-auto bg-[#f4f8ff] p-4" style={{ maxHeight: '420px' }}>
                  {session.messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}
                </div>
                <div className="flex items-center justify-between border-t border-blue-50 px-4 py-3">
                  <span className="text-xs text-slate-400">
                    {session.prescription.medications.length} thuốc · {session.prescription.status === 'confirmed' ? 'Đã xác nhận' : 'Chưa xác nhận'}
                  </span>
                  <button
                    className="flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-bold text-rose-700 transition hover:bg-rose-100"
                    type="button"
                    onClick={() => {
                      onDelete(session.id)
                      setOpenId(null)
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Xóa
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function Icon({ name }) {
  const icons = {
    alert: AlertTriangle,
    bot: BotMessageSquare,
    chat: MessageCircle,
    check: Check,
    clock: Clock3,
    close: X,
    doctor: Stethoscope,
    file: FileText,
    history: History,
    info: Info,
    map: MapPin,
    pill: Pill,
    send: SendHorizontal,
    shield: ShieldCheck,
    upload: UploadCloud,
  }
  const Component = icons[name] || Info
  return <Component aria-hidden="true" className="h-5 w-5" strokeWidth={2.1} />
}

function normalizeText(value) {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
}

function formatSlot(value) {
  return new Intl.DateTimeFormat('vi-VN', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default App