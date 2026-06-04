import { createMockApi } from '../data/mockApi.js'

const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
const mockApi = createMockApi()

async function request(path, options = {}) {
  if (!baseUrl) {
    return null
  }

  const response = await fetch(`${baseUrl}${path}`, options)
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `API error ${response.status}`)
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

  async sendMessage(prescriptionId, message) {
    if (!baseUrl) return mockApi.sendMessage(prescriptionId, message)
    return request('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prescriptionId, message }),
    })
  },

  async createReminders(prescriptionId, items, leadMinutes = 60) {
    if (!baseUrl) return mockApi.createReminders(prescriptionId, items, leadMinutes)
    return request('/reminders/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prescriptionId, leadMinutes, items }),
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
