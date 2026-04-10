import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, List, Tag } from 'antd'
import { BankOutlined, CameraOutlined, AlertOutlined, WarningOutlined } from '@ant-design/icons'
import { getRooms, getCameras, getEvents, getEventAggregates, getEventTrend, getRoomRisk } from '../../services/api'

const RISK_CONFIG: Record<number, { label: string; color: string }> = {
  0: { label: '正常', color: 'green' },
  1: { label: '低风险', color: 'blue' },
  2: { label: '中风险', color: 'orange' },
  3: { label: '高风险', color: 'red' },
}

interface TrendItem { date: string; count: number }
interface RoomRiskItem { room_id: number; room_name: string; risk_level: number }

export default function Dashboard() {
  const [stats, setStats] = useState({ rooms: 0, cameras: 0, events: 0, riskEvents: 0 })
  const [trend, setTrend] = useState<TrendItem[]>([])
  const [roomRisk, setRoomRisk] = useState<RoomRiskItem[]>([])

  useEffect(() => {
    Promise.all([
      getRooms({ page: 1, size: 1 }),
      getCameras({ page: 1, size: 1 }),
      getEvents({ page: 1, size: 1 }),
      getEventAggregates({ page: 1, size: 1, risk_level: 3 }),
      getEventTrend(7),
      getRoomRisk(),
    ]).then(([r1, r2, r3, r4, r5, r6]: any[]) => {
      setStats({
        rooms: r1?.data?.total || 0,
        cameras: r2?.data?.total || 0,
        events: r3?.data?.total || 0,
        riskEvents: r4?.data?.total || 0,
      })
      setTrend(r5?.data || [])
      setRoomRisk(r6?.data || [])
    })
  }, [])

  const maxCount = Math.max(...trend.map(t => t.count), 1)

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>数据概览</h2>
      <Row gutter={16}>
        <Col span={6}>
          <Card><Statistic title="库房数" value={stats.rooms} prefix={<BankOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="摄像头数" value={stats.cameras} prefix={<CameraOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总事件数" value={stats.events} prefix={<AlertOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="高风险事件" value={stats.riskEvents} prefix={<WarningOutlined />} valueStyle={{ color: '#cf1322' }} /></Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={14}>
          <Card title="近7天事件趋势">
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120, padding: '0 8px' }}>
              {trend.map(item => (
                <div key={item.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 11, color: '#666' }}>{item.count}</span>
                  <div
                    style={{
                      width: '100%',
                      height: Math.max((item.count / maxCount) * 80, item.count > 0 ? 4 : 0),
                      background: item.count > 0 ? '#1677ff' : '#f0f0f0',
                      borderRadius: 3,
                      transition: 'height 0.3s',
                    }}
                  />
                  <span style={{ fontSize: 10, color: '#999', whiteSpace: 'nowrap' }}>
                    {item.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col span={10}>
          <Card title="各库房风险状态" bodyStyle={{ padding: '0 16px' }}>
            <List
              size="small"
              dataSource={roomRisk}    locale={{ emptyText: '暂无数据' }}
              renderItem={item => (
                <List.Item style={{ justifyContent: 'space-between' }}>
                  <span>{item.room_name}</span>
                  <Tag color={RISK_CONFIG[item.risk_level]?.color}>
                    {RISK_CONFIG[item.risk_level]?.label}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
