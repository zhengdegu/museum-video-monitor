import { useEffect, useState } from 'react'
import { Table, Tag, Select, Space } from 'antd'
import { getEvents } from '../../services/api'

const riskColors = ['green', 'blue', 'orange', 'red']
const riskLabels = ['正常', '低风险', '中风险', '高风险']

export default function EventList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [eventType, setEventType] = useState<string | undefined>()

  const fetchData = async (p = page) => {
    setLoading(true)
    const params: any = { page: p, size: 20 }
    if (eventType) params.event_type = eventType
    const res: any = await getEvents(params)
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page, eventType])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '库房ID', dataIndex: 'room_id', width: 80 },
    { title: '摄像头ID', dataIndex: 'camera_id', width: 100 },
    { title: '事件时间', dataIndex: 'event_time', width: 180 },
    { title: '事件类型', dataIndex: 'event_type', render: (v: string) => <Tag>{v || '未分类'}</Tag> },
    { title: '人数', dataIndex: 'person_count', width: 60 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: 'AI结论', dataIndex: 'ai_conclusion', ellipsis: true },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>事件中心</h2>
        <Space>
          <Select allowClear placeholder="事件类型" style={{ width: 150 }} onChange={setEventType}
            options={[
              { value: 'normal', label: '正常' },
              { value: 'violation', label: '违规' },
              { value: 'alert', label: '告警' },
            ]} />
        </Space>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  )
}
