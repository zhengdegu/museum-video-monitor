import { useEffect, useState } from 'react'
import { Table, Tag, Button, Space, message, Popconfirm, Select } from 'antd'
import { getVideos, deleteVideo, triggerAnalyze } from '../../services/api'

const statusMap: Record<number, { color: string; text: string }> = {
  0: { color: 'default', text: '待分析' },
  1: { color: 'processing', text: '分析中' },
  2: { color: 'success', text: '已完成' },
  3: { color: 'error', text: '异常' },
}

export default function VideoList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<number | undefined>()

  const fetchData = async (p = page) => {
    setLoading(true)
    const params: any = { page: p, size: 20 }
    if (statusFilter !== undefined) params.analysis_status = statusFilter
    const res: any = await getVideos(params)
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page, statusFilter])

  const handleAnalyze = async (id: number) => {
    const res: any = await triggerAnalyze(id)
    if (res.code === 200) { message.success('已提交分析'); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '摄像头ID', dataIndex: 'camera_id', width: 100 },
    { title: '来源', dataIndex: 'source_type', render: (v: number) => v === 1 ? '自动拉取' : '手动上传' },
    { title: '时长(秒)', dataIndex: 'duration' },
    { title: '大小', dataIndex: 'file_size', render: (v: number) => v ? `${(v / 1024 / 1024).toFixed(1)} MB` : '-' },
    { title: '分析状态', dataIndex: 'analysis_status', render: (v: number) => <Tag color={statusMap[v]?.color}>{statusMap[v]?.text}</Tag> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          {record.analysis_status === 0 && <Button size="small" type="primary" onClick={() => handleAnalyze(record.id)}>开始分析</Button>}
          <Popconfirm title="确认删除？" onConfirm={() => deleteVideo(record.id).then(() => { message.success('已删除'); fetchData() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>视频管理</h2>
        <Select allowClear placeholder="按状态筛选" style={{ width: 150 }} onChange={(v) => setStatusFilter(v)}
          options={Object.entries(statusMap).map(([k, v]) => ({ value: Number(k), label: v.text }))} />
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  )
}
