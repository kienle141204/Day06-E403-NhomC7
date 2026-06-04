import { createMockApi } from '../data/mockApi.js'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const forceMock = import.meta.env.VITE_USE_MOCK === 'true'
const baseUrl = forceMock ? '' : (configuredBaseUrl || 'http://localhost:8000').replace(/\/$/, '')
const mockApi = createMockApi()

async function request(path, options = {}) {
  if (!baseUrl) {
    return null
  }

  const response = await fetch(`${baseUrl}${path}`, options)
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    try {
      const parsed = JSON.parse(detail)
      throw new Error(parsed.detail || `API error ${response.status}`)
    } catch (err) {
      if (err instanceof SyntaxError) {
        throw new Error(detail || `API error ${response.status}`)
      }
      throw err
    }
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export const api = {
  usingMock: !baseUrl,

  async scanPrescription(file) {
    if (!baseUrl) return mockApi.scanPrescription(file)
    const form = new FormData()
    form.append('file', file)
    return request('/prescriptions/scan', { method: 'POST', body: form })
  },

  async updateMedication(prescriptionId, medicationId, patch) {
    if (!baseUrl) return mockApi.updateMedication(prescriptionId, medicationId, patch)
    return request(`/prescriptions/${prescriptionId}/medications/${medicationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
  },

  async confirmPrescription(prescriptionId) {
    if (!baseUrl) return mockApi.confirmPrescription(prescriptionId)
    return request(`/prescriptions/${prescriptionId}/confirm`, { method: 'POST' })
  },

  async sendMessage(prescriptionId, message, sessionId) {
    if (!baseUrl) return mockApi.sendMessage(prescriptionId, message, sessionId)
    return request('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prescriptionId, message, sessionId }),
    })
  },

  async createReminders(prescriptionId, leadMinutes = 60) {
    if (!baseUrl) return mockApi.createReminders(prescriptionId, leadMinutes)
    return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/reminders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leadMinutes }),
    })
  },

  async getSpecialists(prescriptionId) {
    if (!baseUrl) return mockApi.getSpecialists(prescriptionId)
    return request(`/specialists?prescriptionId=${encodeURIComponent(prescriptionId)}`)
  },

  async createAppointment(payload) {
    if (!baseUrl) return mockApi.createAppointment(payload)
    return request('/appointments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
}
