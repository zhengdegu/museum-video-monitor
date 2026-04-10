import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic } from 'antd'
import { BankOutlined, CameraOutlined, AlertOutlined, WarningOutlined } from '@ant-design/icons'
import { getRooms, getCameras, getEvents, getEventAggregates } from '../../services/api'

export default function Dashboard() {
  const [stats, setStats] = useState({ rooms: 0, cameras: 0, events: 0, riskEvents: 0 })

  useEffect(() => {
    Promise.all([
      getRooms({ page: 1, size: 1 }),
      getCameras({ page: 1, size: 1 }),
      getEvents({ page: 1, size: 1 }),
      getEventAggregates({ page: 1, size: 1, risk_level: 3 }),
    ]).then(([r1, r2, r3, r4]: any[]) => {
      setStats({
        rooms: r1?.data?.total || 0,
        cameras: r2?.data?.total || 0,
        events: r3?.data?.total || 0,
        riskEvents: r4?.data?.total || 0,
      })
    })
  }, [])

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
    </div>
  )
}
