import { useEffect, useState } from 'react'
import { Table, Button, Switch, Space, message, Popconfirm, Card, Row, Col } from 'antd'
import { getRules, toggleRule, deleteRule, getRuleHitStats } from '../../services/api'

interface HitStat { rule_id: number; rule_name: string; code: string; hit_count: number }

export default function RuleList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [hitStats, setHitStats] = useState<HitStat[]>([])

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getRules({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  const fetchStats = async () => {
    const res: any = await getRuleHitStats()
    if (res.code === 200) setHitStats(res.data || [])
  }

  useEffect(() => { fetchData(); fetchStats() }, [page])

  const handleToggle = async (id: number) => {
    const res: any = await toggleRule(id)
    if (res.code === 200) { message.success('已切换'); fetchData() }
  }

  const maxHit = Math.max(...hitStats.map(s => s.hit_count), 1)

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '规则名称', dataIndex: 'name' },
    { title: '编码', dataIndex: 'code' },
    { title: '类型', dataIndex: 'rule_type' },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '启用', dataIndex: 'enabled', render: (v: number, record: any) => <Switch checked={v === 1} onChange={() => handleToggle(record.id)} /> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Popconfirm title="确认删除？" onConfirm={() => deleteRule(record.id).then(() => { message.success('已删除'); fetchData(); fetchStats() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}><h2>规则管理</h2></div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="规则命中统计" size="small">
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 120, padding: '0 8px' }}>
              {hitStats.map(item => (
                <div key={item.rule_id} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 'bold' }}>{item.hit_count}</span>
                  <div style={{
                    width: '100%', maxWidth: 60,
                    height: Math.max((item.hit_count / maxHit) * 80, item.hit_count > 0 ? 4 : 0),
                    background: item.hit_count > 0 ? '#ff4d4f' : '#f0f0f0',
                    borderRadius: 3, transition: 'height 0.3s',
                  }} />
                  <span style={{ fontSize: 10, color: '#666', textAlign: 'center', lineHeight: '1.2', wordBreak: 'break-all' }}>
                    {item.rule_name.length > 6 ? item.rule_name.slice(0, 6) + '…' : item.rule_name}
                  </span>
                </div>
              ))}
              {hitStats.length === 0 && <span style={{ color: '#999', margin: 'auto' }}>暂无数据</span>}
            </div>
          </Card>
        </Col>
      </Row>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  )
}
