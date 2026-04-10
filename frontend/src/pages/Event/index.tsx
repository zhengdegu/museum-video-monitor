import { useEffect, useState } from 'react'
import { Table, Tag, Select, Space, Drawer, Tabs, Timeline, Image, Typography } from 'antd'
import { getEvents } from '../../services/api'

const riskColors = ['green', 'blue', 'orange', 'red']
const riskLabels = ['正常', '低风险', '中风险', '高风险']

const dotColor = (level: number) => riskColors[level] ?? 'gray'

export default function EventList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [eventType, setEventType] = useState<string | undefined>()
  const [selected, setSelected] = useState<any>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list')

  const fetchData = async (p = page) => {
    setLoading(true)
    const params: any = { page: p, size: 20 }
    if (eventType) params.event_type = eventType
    const res: any = await getEvents(params)
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page, eventType])

  const openDrawer = (record: any) => {
    setSelected(record)
    setDrawerOpen(true)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '库房ID', dataIndex: 'room_id', width: 80 },
    { title: '摄像头ID', dataIndex: 'camera_id', width: 100 },
    { title: '事件时间', dataIndex: 'event_time', width: 180 },
    { title: '事件类型', dataIndex: 'event_type', render: (v: string) => <Tag>{v || '未分类'}</Tag> },
    { title: '风险等级', dataIndex: 'risk_level', width: 90, render: (v: number) => <Tag color={riskColors[v]}>{riskLabels[v] ?? '未知'}</Tag> },
    { title: '人数', dataIndex: 'person_count', width: 60 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: 'AI结论', dataIndex: 'ai_conclusion', ellipsis: true },
  ]

  const timelineItems = [...data]
    .sort((a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime())
    .map(item => ({
      color: dotColor(item.risk_level),
      children: (
        <div style={{ cursor: 'pointer' }} onClick={() => openDrawer(item)}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{item.event_time}</Typography.Text>
          <div>
            <Tag>{item.event_type || '未分类'}</Tag>
            <Tag color={riskColors[item.risk_level]}>{riskLabels[item.risk_level] ?? '未知'}</Tag>
            <Typography.Text style={{ marginLeft: 8 }}>库房 {item.room_id}</Typography.Text>
          </div>
          {item.description && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Typography.Text>}
        </div>
      ),
    }))

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

      <Tabs
        activeKey={viewMode}
        onChange={k => setViewMode(k as 'list' | 'timeline')}
        items={[
          { key: 'list', label: '列表视图' },
          { key: 'timeline', label: '时间线视图' },
        ]}
      />

      {viewMode === 'list' ? (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          onRow={record => ({ onClick: () => openDrawer(record), style: { cursor: 'pointer' } })}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
        />
      ) : (
        <div style={{ padding: '24px 8px', maxHeight: 600, overflowY: 'auto' }}>
          <Timeline items={timelineItems} />
        </div>
      )}

      <Drawer
        title="事件详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
      >
        {selected && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Typography.Text strong>关联视频ID：</Typography.Text>
              <Typography.Text>{selected.video_id ?? '—'}</Typography.Text>
            </div>
            <div>
              <Typography.Text strong>AI结论：</Typography.Text>
              <Typography.Paragraph style={{ marginTop: 4 }}>{selected.ai_conclusion || '暂无'}</Typography.Paragraph>
            </div>
            <div>
              <Typography.Text strong>规则命中：</Typography.Text>
              <div style={{ marginTop: 6 }}>
                {selected.rules_hit?.length
                  ? selected.rules_hit.map((r: string, i: number) => <Tag key={i} color="red">{r}</Tag>)
                  : <Typography.Text type="secondary">无</Typography.Text>}
              </div>
            </div>
            <div>
              <Typography.Text strong>证据截图：</Typography.Text>
              <div style={{ marginTop: 8 }}>
                {selected.evidence_images?.length ? (
                  <Image.PreviewGroup>
                    <Space wrap>
                      {selected.evidence_images.map((src: string, i: number) => (
                        <Image key={i} src={src} width={120} height={80} style={{ objectFit: 'cover' }} />
                      ))}
                    </Space>
                  </Image.PreviewGroup>
                ) : (
                  <Typography.Text type="secondary">暂无截图</Typography.Text>
                )}
              </div>
            </div>
          </Space>
        )}
      </Drawer>
    </div>
  )
}
