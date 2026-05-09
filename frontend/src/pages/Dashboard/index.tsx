import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, List, Tag } from 'antd'
import { BankOutlined, CameraOutlined, AlertOutlined, WarningOutlined } from '@ant-design/icons'
import { getRooms, getCameras, getEvents, getEventAggregates, getEventTrend, getRoomRisk, getWarningStats } from '../../services/api'
import { genesisColors } from '../../theme'

const RISK_CONFIG: Record<number, { label: string; color: string }> = {
  0: { label: '正常', color: genesisColors.success },
  1: { label: '低风险', color: genesisColors.primary },
  2: { label: '中风险', color: genesisColors.warning },
  3: { label: '高风险', color: genesisColors.error },
}

interface TrendItem { date: string; count: number }
interface RoomRiskItem { room_id: number; room_name: string; risk_level: number }
interface WarningStatsData {
  active_count: number
  today_count: number
  resolved_count: number
  false_alarm_rate: number
}

const cardStyle: React.CSSProperties = {
  borderRadius: 12,
  border: `1px solid ${genesisColors.border}`,
  boxShadow: 'none',
  transition: 'transform 0.2s, box-shadow 0.2s',
}

export default function Dashboard() {
  const [stats, setStats] = useState({ rooms: 0, cameras: 0, events: 0, riskEvents: 0 })
  const [trend, setTrend] = useState<TrendItem[]>([])
  const [roomRisk, setRoomRisk] = useState<RoomRiskItem[]>([])
  const [warningStats, setWarningStats] = useState<WarningStatsData | null>(null)

  useEffect(() => {
    Promise.all([
      getRooms({ page: 1, size: 1 }),
      getCameras({ page: 1, size: 1 }),
      getEvents({ page: 1, size: 1 }),
      getEventAggregates({ page: 1, size: 1, risk_level: 3 }),
      getEventTrend(7),
      getRoomRisk(),
      getWarningStats(),
    ]).then(([r1, r2, r3, r4, r5, r6, r7]: any[]) => {
      setStats({
        rooms: r1?.data?.total || 0,
        cameras: r2?.data?.total || 0,
        events: r3?.data?.total || 0,
        riskEvents: r4?.data?.total || 0,
      })
      setTrend(r5?.data || [])
      setRoomRisk(r6?.data || [])
      if (r7?.data) setWarningStats(r7.data)
    })
  }, [])

  const maxCount = Math.max(...trend.map(t => t.count), 1)

  const statCards = [
    { key: 'rooms' as const, title: '库房数', icon: <BankOutlined />, color: genesisColors.primary },
    { key: 'cameras' as const, title: '摄像头数', icon: <CameraOutlined />, color: genesisColors.primary },
    { key: 'events' as const, title: '总事件数', icon: <AlertOutlined />, color: genesisColors.warning },
    { key: 'riskEvents' as const, title: '高风险事件', icon: <WarningOutlined />, color: genesisColors.error },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 24, color: genesisColors.textPrimary, fontWeight: 700, fontSize: 20, letterSpacing: '-0.03em' }}>
        数据概览
      </h2>

      {/* KPI Cards */}
      <Row gutter={[20, 20]}>
        {statCards.map(({ key, title, icon, color }) => (
          <Col span={6} key={key}>
            <Card style={cardStyle} styles={{ body: { padding: '20px 24px' } }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 10,
                    background: `${color}12`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 20,
                    color,
                  }}
                >
                  {icon}
                </div>
                <Statistic
                  title={<span style={{ color: genesisColors.textSecondary, fontSize: 13 }}>{title}</span>}
                  value={stats[key]}
                  valueStyle={{
                    color: genesisColors.textPrimary,
                    fontWeight: 700,
                    fontSize: 28,
                    letterSpacing: '-0.5px',
                  }}
                />
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Charts Row */}
      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col span={14}>
          <Card
            title={<span style={{ fontWeight: 600, fontSize: 14 }}>近7天事件趋势</span>}
            style={cardStyle}
          >
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 140, padding: '0 8px' }}>
              {trend.map(item => (
                <div
                  key={item.date}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}
                >
                  <span style={{ fontSize: 11, color: genesisColors.textSecondary, fontWeight: 500 }}>
                    {item.count}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      height: Math.max((item.count / maxCount) * 100, item.count > 0 ? 6 : 0),
                      background: item.count > 0 ? genesisColors.primary : '#F4F4F5',
                      borderRadius: 4,
                      transition: 'height 0.3s ease',
                    }}
                  />
                  <span style={{ fontSize: 10, color: genesisColors.neutral, whiteSpace: 'nowrap' }}>
                    {item.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col span={10}>
          <Card
            title={<span style={{ fontWeight: 600, fontSize: 14 }}>各库房风险状态</span>}
            style={cardStyle}
            styles={{ body: { padding: '4px 16px' } }}
          >
            <List
              size="small"
              dataSource={roomRisk}
              locale={{ emptyText: '暂无数据' }}
              renderItem={item => (
                <List.Item style={{ justifyContent: 'space-between', padding: '10px 0' }}>
                  <span style={{ color: genesisColors.textPrimary, fontSize: 13 }}>{item.room_name}</span>
                  <Tag
                    color={RISK_CONFIG[item.risk_level]?.color}
                    style={{ borderRadius: 9999, margin: 0, border: 'none' }}
                  >
                    {RISK_CONFIG[item.risk_level]?.label}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* AI Summary + Warning Stats */}
      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col span={14}>
          <Card
            style={{
              ...cardStyle,
              background: genesisColors.textPrimary,
              border: 'none',
            }}
            styles={{ body: { padding: 24 } }}
          >
            <div style={{ color: '#fff', fontWeight: 600, fontSize: 14, marginBottom: 12 }}>AI 分析摘要</div>
            <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13, lineHeight: 1.7, margin: 0 }}>
              过去24小时内系统检测到异常事件，整体安全态势评分正在计算中。建议关注高风险库房的门禁记录和温湿度变化趋势。
            </p>
          </Card>
        </Col>

        {warningStats && (
  <Col span={10}>
            <Card
              title={<span style={{ fontWeight: 600, fontSize: 14 }}>预警概览</span>}
              style={cardStyle}
              extra={<a href="/warnings" style={{ color: genesisColors.primary, fontSize: 13 }}>查看全部</a>}
            >
              <Row gutter={[16, 12]}>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ color: genesisColors.textSecondary, fontSize: 12 }}>活跃预警</span>}
                    value={warningStats.active_count}
                    valueStyle={{ color: genesisColors.error, fontWeight: 700, fontSize: 22 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ color: genesisColors.textSecondary, fontSize: 12 }}>今日新增</span>}
                    value={warningStats.today_count}
                    valueStyle={{ color: genesisColors.warning, fontWeight: 700, fontSize: 22 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ color: genesisColors.textSecondary, fontSize: 12 }}>已处理</span>}
                    value={warningStats.resolved_count}
                    valueStyle={{ color: genesisColors.success, fontWeight: 700, fontSize: 22 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ color: genesisColors.textSecondary, fontSize: 12 }}>误报率</span>}
                    value={warningStats.false_alarm_rate}
                    valueStyle={{ color: genesisColors.neutral, fontWeight: 700, fontSize: 22 }}
                    suffix="%"
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  )
}
