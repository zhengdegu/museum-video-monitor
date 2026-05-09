import { useState, useEffect } from 'react'
import { Button, Card, DatePicker, Select, Space, Table, Tag, message, Modal } from 'antd'
import { FileTextOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons'
import { generateReport, getReportList, getReportDownloadUrl } from '../../services/api'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const typeOptions = [
  { value: 'weekly', label: '周报' },
  { value: 'monthly', label: '月报' },
  { value: 'quarterly', label: '季报' },
]

const statusMap: Record<string, { color: string; text: string }> = {
  completed: { color: 'green', text: '已完成' },
  generating: { color: 'blue', text: '生成中' },
  failed: { color: 'red', text: '失败' },
}

export default function ReportPage() {
  const [reportType, setReportType] = useState<string>('weekly')
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [generating, setGenerating] = useState(false)
  const [list, setList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)

  const fetchList = async (p = page) => {
    setLoading(true)
    try {
      const res: any = await getReportList({ page: p, size: 20 })
      if (res.code === 200) {
        setList(res.data.items)
        setTotal(res.data.total)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchList() }, [page])

  const handleGenerate = async () => {
    if (!dateRange) {
      message.warning('请选择时间范围')
      return
    }
    setGenerating(true)
    try {
      const res: any = await generateReport({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        report_type: reportType,
      })
      if (res.code === 200) {
        message.success('报告生成成功')
        fetchList(1)
        setPage(1)
      } else {
        message.error(res.message || '生成失败')
      }
    } catch {
      message.error('生成报告失败')
    } finally {
      setGenerating(false)
    }
  }

  const handlePreview = (record: any) => {
    const url = getReportDownloadUrl(record.id)
    setPreviewHtml(url)
  }

  const handleDownload = (record: any) => {
    const url = getReportDownloadUrl(record.id)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${record.report_type}_${record.start_date}.html`
    a.click()
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '报告类型',
      dataIndex: 'report_type',
      width: 100,
      render: (v: string) => {
        const opt = typeOptions.find(o => o.value === v)
        return <Tag color="blue">{opt?.label || v}</Tag>
      },
    },
    { title: '开始日期', dataIndex: 'start_date', width: 120 },
    { title: '结束日期', dataIndex: 'end_date', width: 120 },
    { title: '生成时间', dataIndex: 'generated_at', width: 180 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const s = statusMap[v] || { color: 'default', text: v }
        return <Tag color={s.color}>{s.text}</Tag>
      },
    },
    {
      title: '操作',
      width: 160,
      render: (_: any, record: any) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            disabled={record.status !== 'completed'}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            disabled={record.status !== 'completed'}
            onClick={() => handleDownload(record)}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>合规报告</h2>
      </div>

      <Card title="生成报告" style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            value={reportType}
            onChange={setReportType}
            options={typeOptions}
            style={{ width: 120 }}
          />
          <RangePicker
            value={dateRange}
            onChange={(val) => setDateRange(val as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          />
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            loading={generating}
            onClick={handleGenerate}
          >
            生成报告
          </Button>
        </Space>
      </Card>

      <Card title="历史报告">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
        />
      </Card>

      <Modal
        title="报告预览"
        open={!!previewHtml}
        onCancel={() => setPreviewHtml(null)}
        footer={null}
        width={900}
        styles={{ body: { height: 600, padding: 0 } }}
      >
        {previewHtml && (
          <iframe
            src={previewHtml}
            style={{ width: '100%', height: '100%', border: 'none', minHeight: 560 }}
            title="report-preview"
          />
        )}
      </Modal>
    </div>
  )
}
