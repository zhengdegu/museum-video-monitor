import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, List, Tag } from 'antd'
import { BankOutlined, CameraOutlined, AlertOutlined, WarningOutlined } from '@ant-design/icons'
import { getRooms, getCameras, getEvents, getEventAggregates, getEventTrend, getRoomRisk } from '../../services/api'
import { wanderMapColors } from '../../theme'

const RISK_CONFIG: Record<number, { label: string; color: string }> = {
  0: { label: '正常', color: wanderMapColors.success },
  1: { label: '低风险', color: wanderMapColors.info },
  2: { label: '中风险', color: wanderMapColors.warning },
  3: { label: '高风险', color: wanderMapColors.error },
}

interface TrendItem { date: string; count: number }
interface RoomRiskItem { room_id: number; room_name: string; risk_level: number }

const statCards = [
  { key: 'rooms', title: '库房数', icon: <BankOutlined />, color: wanderMapColors.primary },
  { key: 'cameras', title: '摄像头数', icon: <CameraOutlined />, color: wanderMapColors.tertiary },
  { key: 'events', title: '总事件数', icon: <AlertOutlined />, color: wanderMapColors.secondary },
  { key: 'riskEvents', title: '高风险事件', icon: <WarningOutlined />, color: wanderMapColors.error },
] as const

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
      <h2 style={{ marginBottom: 24, color: wanderMapColors.textPrimary, fontWeight: 600 }}>
        数据概览
      </h2>

      <Row gutter={[20, 20]}>
        {statCards.map(({ key, title, icon, color }) => (
          <Col span={6} key={key}>
            <Card
              style={{
                borderRadius: 12,
                border: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
              }}
              bodyStyle={{ padding: '24px 28px' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: `${color}14`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                    color,
                  }}
                >
                  {icon}
                </div>
                <Statistic
                  title={<span style={{ color: wanderMapColors.textSecondary, fontSize: 13 }}>{title}</span>}
                  value={stats[key]}
                  valueStyle={{
                    color: wanderMapColors.textPrimary,
                    fontWeight: 700,
                    fontSize: 28,
                  }}
                />
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col span={14}>
          <Card
            title={<span style={{ fontWeight: 600 }}>近7天事件趋势</span>}
            style={{
              borderRadius: 12,
              border: 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 140, padding: '0 8px' }}>
              {trend.map(item => (
                <div
                  key={item.date}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span style={{ fontSize: 12, color: wanderMapColors.textSecondary, fontWeight: 500 }}>
                    {item.count}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      height: Math.max((item.count / maxCount) * 100, item.count > 0 ? 6 : 0),
                      background: item.count > 0
                        ? `linear-gradient(180deg, ${wanderMapColors.primary} 0%, ${wanderMapColors.tertiary} 100%)`
                        : '#f0f0f0',
                      borderRadius: 6,
                      transition: 'height 0.3s ease',
                    }}
                  />
                  <span style={{ fontSize: 11, color: wanderMapColors.textSecondary, whiteSpace: 'nowrap' }}>
                    {item.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col span={10}>
          <Card
            title={<span style={{ fontWeight: 600 }}>各库房风险状态</span>}
            style={{
              borderRadius: 12,
              border: 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            }}
            bodyStyle={{ padding: '4px 16px' }}
          >
            <List
              size="small"
              dataSource={roomRisk}
              locale={{ emptyText: '暂无数据' }}
              renderItem={item => (
                <List.Item style={{ justifyContent: 'space-between', padding: '10px 0' }}>
                  <span style={{ color: wanderMapColors.textPrimary }}>{item.room_name}</span>
                  <Tag
                    color={RISK_CONFIG[item.risk_level]?.color}
                    style={{ borderRadius: 6, margin: 0 }}
                >
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
