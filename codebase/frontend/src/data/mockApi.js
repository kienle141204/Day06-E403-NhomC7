const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function normalizeText(value) {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
}

// ─── Scenario datasets ────────────────────────────────────────────────────────

const SCENARIO_1_DATA = {
  prescriptionId: 'rx-sc1-0001',
  confidence: 0.92,
  doctorName: 'BS. Nguyễn Thị Hoa',
  clinic: 'Phòng khám Đa khoa Bình Dân',
  issuedAt: '2026-06-03',
  status: 'pending',
  medications: [
    {
      id: 'med-s1-1',
      name: 'Amoxicillin',
      strength: '500mg',
      dose: '1 viên',
      schedule: 'Sáng, trưa, tối (sau ăn)',
      duration: '7 ngày',
      risk: 'normal',
      confidence: 0.93,
    },
    {
      id: 'med-s1-2',
      name: 'Paracetamol',
      strength: '500mg',
      dose: '1-2 viên',
      schedule: 'Khi sốt hoặc đau (cách 4-6 giờ)',
      duration: '5 ngày',
      risk: 'normal',
      confidence: 0.97,
    },
    {
      id: 'med-s1-3',
      name: 'Cetirizine',
      strength: '10mg',
      dose: '1 viên',
      schedule: 'Tối trước khi ngủ',
      duration: '7 ngày',
      risk: 'normal',
      confidence: 0.88,
    },
  ],
  warnings: [],
}

const SCENARIO_2_DATA = {
  prescriptionId: 'rx-sc2-0002',
  confidence: 0.89,
  doctorName: 'BS. Trần Quốc Bảo',
  clinic: 'Bệnh viện Đa khoa Trung Ương',
  issuedAt: '2026-06-03',
  status: 'pending',
  medications: [
    {
      id: 'med-s2-1',
      name: 'Warfarin',
      strength: '5mg',
      dose: '1 viên',
      schedule: 'Tối (cùng giờ mỗi ngày)',
      duration: '30 ngày',
      risk: 'high',
      confidence: 0.91,
    },
    {
      id: 'med-s2-2',
      name: 'Digoxin',
      strength: '0.25mg',
      dose: '1 viên',
      schedule: 'Sáng trước ăn',
      duration: '30 ngày',
      risk: 'high',
      confidence: 0.87,
    },
    {
      id: 'med-s2-3',
      name: 'Furosemide',
      strength: '40mg',
      dose: '1 viên',
      schedule: 'Sáng sau ăn',
      duration: '14 ngày',
      risk: 'normal',
      confidence: 0.94,
    },
  ],
  warnings: [
    {
      id: 'warn-s2-1',
      level: 'high',
      title: 'Thuốc kháng đông nguy cơ cao',
      detail:
        'Warfarin có khoảng điều trị hẹp. Không tự ý thay đổi liều. Xét nghiệm INR định kỳ theo chỉ định bác sĩ.',
    },
    {
      id: 'warn-s2-2',
      level: 'high',
      title: 'Glycoside tim — theo dõi nhịp',
      detail:
        'Digoxin có chỉ số điều trị hẹp. Cần theo dõi nhịp tim và điện giải đồ. Báo ngay nếu buồn nôn, nhìn mờ hoặc nhịp tim bất thường.',
    },
  ],
}

const SCENARIO_3_DATA = {
  prescriptionId: 'rx-sc3-0003',
  confidence: 0.45,
  doctorName: 'BS. ??? (không rõ)',
  clinic: 'Phòng khám (chưa nhận dạng được)',
  issuedAt: '2026-06-03',
  status: 'pending',
  medications: [
    {
      id: 'med-s3-1',
      name: '??? (Thuốc X...)',
      strength: '???mg',
      dose: '1 viên',
      schedule: 'Không rõ',
      duration: '7 ngày',
      risk: 'normal',
      confidence: 0.32,
    },
    {
      id: 'med-s3-2',
      name: 'Paracetamol',
      strength: '500mg',
      dose: '1-2 viên',
      schedule: 'Khi sốt (cách 4-6 giờ)',
      duration: '5 ngày',
      risk: 'normal',
      confidence: 0.85,
    },
    {
      id: 'med-s3-3',
      name: 'Thuốc Y (không đọc được)',
      strength: '???',
      dose: 'Không rõ',
      schedule: 'Không rõ',
      duration: 'Không rõ',
      risk: 'normal',
      confidence: 0.41,
    },
  ],
  warnings: [
    {
      id: 'warn-s3-1',
      level: 'high',
      title: 'Độ tin cậy OCR thấp',
      detail:
        'Hệ thống không đọc rõ tên một số thuốc. Vui lòng sửa đúng tên thuốc trước khi xác nhận để tránh nhầm lẫn.',
    },
  ],
}

// ─── Module-level state ───────────────────────────────────────────────────────

let prescription = null
let activeScenario = 'scenario1'

function detectScenario(filename) {
  const name = (filename || '').toLowerCase()
  if (name.startsWith('scenario2') || name.startsWith('nguy-hiem')) return 'scenario2'
  if (name.startsWith('scenario3') || name.startsWith('khong-ro')) return 'scenario3'
  if (name.startsWith('scenario4') || name.startsWith('khong-doc')) return 'scenario4'
  return 'scenario1'
}

// ─── Mock API factory ─────────────────────────────────────────────────────────

export function createMockApi() {
  return {
    async scanPrescription(file) {
      await delay(900)
      activeScenario = detectScenario(file?.name || '')

      if (activeScenario === 'scenario4') {
        throw new Error(
          'Không thể nhận diện đơn thuốc. Ảnh quá mờ hoặc bị che khuất. Vui lòng chụp lại và tải lên.',
        )
      }

      const datasets = {
        scenario1: SCENARIO_1_DATA,
        scenario2: SCENARIO_2_DATA,
        scenario3: SCENARIO_3_DATA,
      }
      prescription = { ...datasets[activeScenario], status: 'pending' }
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
      prescription = { ...prescription, status: 'confirmed' }
      return prescription
    },

    async sendMessage(_prescriptionId, message) {
      await delay(850)
      const text = normalizeText(message)

      if (activeScenario === 'scenario2') {
        return {
          answer:
            'Tôi không thể tư vấn về đơn thuốc này. Vui lòng liên hệ bác sĩ chuyên khoa để được tư vấn an toàn.',
          quickReplies: ['Đặt lịch với bác sĩ', 'Xem cảnh báo'],
        }
      }

      // Scenario 1 & 3 (after resolution)
      if (text.includes('tac dung phu')) {
        return {
          answer:
            'Amoxicillin có thể gây tiêu chảy, buồn nôn hoặc dị ứng da. Paracetamol an toàn khi dùng đúng liều, tránh dùng quá 4g/ngày. Cetirizine có thể gây buồn ngủ nhẹ.',
          quickReplies: ['Lịch uống trong ngày', 'Hỏi về Amoxicillin', 'Tạo nhắc uống thuốc'],
        }
      }
      if (text.includes('nhac') || text.includes('lich')) {
        return {
          answer:
            'Tôi có thể tạo nhắc: sáng/trưa/tối cho Amoxicillin và tối cho Cetirizine. Paracetamol chỉ uống khi cần nên không cần nhắc định kỳ.',
          quickReplies: ['Tạo tất cả nhắc nhở', 'Chỉ nhắc buổi tối'],
        }
      }
      if (text.includes('ngung thuoc') || text.includes('tang lieu') || text.includes('giam lieu')) {
        return {
          answer:
            'Mình không thể thay bác sĩ quyết định đổi liều hoặc ngừng thuốc. Hãy liên hệ BS. Nguyễn Thị Hoa để được tư vấn trực tiếp.',
          quickReplies: ['Giải thích từng thuốc', 'Lịch uống trong ngày', 'Đặt lịch với bác sĩ'],
        }
      }
      return {
        answer:
          'Theo đơn đã xác nhận: Amoxicillin là kháng sinh dùng 7 ngày (sáng/trưa/tối sau ăn), Paracetamol hạ sốt khi cần, Cetirizine kháng dị ứng uống tối. Thông tin chỉ mang tính tham khảo về thuốc.',
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
      if (activeScenario === 'scenario2') {
        return [
          {
            id: 'sp-s2-1',
            name: 'BS. CKI. Lê Minh Khoa',
            specialty: 'Tim mạch & Chống đông',
            location: 'Phòng khám Tim mạch B2',
            nextSlot: '2026-06-05T08:30:00+07:00',
          },
          {
            id: 'sp-s2-2',
            name: 'DS. Phạm Thị Thu',
            specialty: 'Dược lâm sàng',
            location: 'Tư vấn trực tuyến',
            nextSlot: '2026-06-05T14:00:00+07:00',
          },
        ]
      }
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
        id: `apt-${Date.now()}`,
        specialistId: payload.specialistId,
        slot: payload.slot,
        status: 'confirmed',
      }
    },
  }
}
