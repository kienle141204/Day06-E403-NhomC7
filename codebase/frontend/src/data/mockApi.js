const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

let prescription = {
  prescriptionId: 'rx-demo-0603',
  confidence: 0.91,
  doctorName: 'BS. Lê Văn C',
  clinic: 'Phòng khám Nội tiết',
  issuedAt: '2026-06-03',
  status: 'pending',
  medications: [
    {
      id: 'med-1',
      name: 'Metformin',
      strength: '500mg',
      dose: '1 viên',
      schedule: 'Sau ăn sáng và tối',
      duration: '30 ngày',
      risk: 'normal',
      confidence: 0.82,
    },
    {
      id: 'med-2',
      name: 'Atorvastatin',
      strength: '10mg',
      dose: '1 viên',
      schedule: 'Tối trước khi ngủ',
      duration: '30 ngày',
      risk: 'normal',
      confidence: 0.94,
    },
    {
      id: 'med-3',
      name: 'Prednisolone',
      strength: '20mg',
      dose: '1 viên',
      schedule: 'Sau ăn sáng',
      duration: '14 ngày',
      risk: 'high',
      confidence: 0.9,
    },
  ],
  warnings: [
    {
      id: 'warn-1',
      level: 'high',
      title: 'Cần xác nhận với bác sĩ',
      detail: 'Prednisolone cần dùng đúng liều và không tự ý ngừng đột ngột.',
    },
  ],
}

function confirmedPrescription() {
  prescription = { ...prescription, status: 'confirmed' }
  return prescription
}

function normalizeText(value) {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
}

export function createMockApi() {
  return {
    async scanPrescription() {
      await delay(900)
      prescription = { ...prescription, status: 'pending' }
      return prescription
    },

    async updateMedication(_prescriptionId, medicationId, patch) {
      await delay(400)
      prescription = {
        ...prescription,
        medications: prescription.medications.map((item) =>
          item.id === medicationId ? { ...item, ...patch, confidence: 0.99 } : item,
        ),
      }
      return prescription
    },

    async confirmPrescription() {
      await delay(450)
      return confirmedPrescription()
    },

    async sendMessage(_prescriptionId, message) {
      await delay(850)
      const text = normalizeText(message)
      if (text.includes('tac dung phu')) {
        return {
          answer:
            'Metformin có thể gây khó chịu đường tiêu hóa lúc mới bắt đầu. Prednisolone có thể làm tăng đường huyết, mất ngủ hoặc đau dạ dày. Hãy báo bác sĩ nếu có dấu hiệu bất thường.',
          quickReplies: ['Lịch uống trong ngày', 'Tạo nhắc uống thuốc', 'Cần gặp bác sĩ không?'],
        }
      }
      if (text.includes('nhac') || text.includes('lich')) {
        return {
          answer:
            'Tôi có thể tạo nhắc trước 60 phút cho các mốc: sau ăn sáng, sau ăn tối và trước khi ngủ.',
          quickReplies: ['Tạo tất cả nhắc nhở', 'Chỉ nhắc buổi tối'],
        }
      }
      if (text.includes('bac si')) {
        return {
          answer:
            'Đơn có thuốc cần theo dõi cẩn thận. Nếu bạn đang đau dạ dày nặng, mất ngủ nhiều, phù mặt hoặc đường huyết tăng, nên đặt lịch tư vấn sớm.',
          quickReplies: ['Xem lịch chuyên gia', 'Hỏi về Prednisolone'],
        }
      }
      return {
        answer:
          'Theo đơn đã xác nhận, Metformin thường dùng để hỗ trợ kiểm soát đường huyết, Atorvastatin hỗ trợ mỡ máu, và Prednisolone cần dùng đúng liều bác sĩ kê. Thông tin chỉ mang tính tham khảo.',
        quickReplies: ['Tác dụng phụ?', 'Lịch uống trong ngày', 'Tạo nhắc uống thuốc'],
      }
    },

    async createReminders(_prescriptionId, items, leadMinutes) {
      await delay(650)
      return {
        leadMinutes,
        reminders: items.map((item, index) => ({
          id: `rem-${index + 1}`,
          medicationId: item.medicationId,
          label: item.label,
          time: item.time,
          active: true,
        })),
      }
    },

    async getSpecialists() {
      await delay(650)
      return [
        {
          id: 'sp-1',
          name: 'BS. Phạm Thị Lan',
          specialty: 'Nội tiết',
          location: 'Phòng khám C3',
          nextSlot: '2026-06-05T09:00:00+07:00',
        },
        {
          id: 'sp-2',
          name: 'DS. Nguyễn Minh Tuấn',
          specialty: 'Tư vấn dược',
          location: 'Tư vấn trực tuyến',
          nextSlot: '2026-06-06T14:00:00+07:00',
        },
      ]
    },

    async createAppointment(payload) {
      await delay(500)
      return {
        id: 'apt-0605',
        specialistId: payload.specialistId,
        slot: payload.slot,
        status: 'confirmed',
      }
    },
  }
}
