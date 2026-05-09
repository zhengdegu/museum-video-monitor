import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Tag, Select, DatePicker, Button, Progress, Modal, Space, message } from 'antd'
import {
  WarningOutlined, ClockCircleOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined, EyeOutlined, StopOutlined,
} from '@ant-design/icons'
import { getWarnings, getWarningStats, resolveWarning, dismissWarning, getWarning } from '../../services/api'
import { wanderMapColors } from '../../theme'
import TrajectoryView from '../../components/TrajectoryView'

const { RangePicker } = DatePicker

const WARNING_TYPE_MAP: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  loiter: { label: '滞留', color: '#F97316', icon: <ClockCircleOutlined /> },
  repeated_approach: { label: '反复接近', color: '#EF4444', icon: <ExclamationCircleOutlined /> },
  acceleration: { label: '突然加速', color: '#8B5CF6', icon: <WarningOutlined /> },
  off_hours: { label: '非工作时间', color: '#0EA5E9', icon: <StopOutlined /> },
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  active: { label: '活跃', color: 'error' },
  resolved: { label: '已处理', color: 'success' },
  dismissed: { label: '误报', color: 'default' },
}

interface WarningItem {
  id: number
  camera_id: number
  room_id: number
  warning_type: string
  risk_score: number
  person_track_id?: string
  trajectory_data?: any
  description?: string
  status: string
  created_at: string
  resolved_at?: string
}

interface WarningStatsData {
  active_count: number
  today_count: number
  resolved_count: number
  dismissed_count: number
  false_alarm_rate: number
  by_type: Record<string, number>
  by_room: Record<number, number>
}

export default function WarningPage() {
  const [warnings, setWarnings] = useState<WarningItem[]>([])
  const [stats, setStats] = useState<WarningStatsData | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<{
    warning_type?: string
    status?: string
    room_id?: number
    start_time?: string
    end_time?: string
  }>({})
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailData, setDetailData] = useState<WarningItem | null>(null)

  const fetchWarnings = async () => {
    setLoading(true)
    try {
      const res: any = await getWarnings({ page, size: 20, ...filters })
      if (res?.data) {
        setWarnings(res.data.items || [])
        setTotal(res.data.total || 0)
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    const res: any = await getWarningStats()
    if (res?.data) {
      setStats(res.data)
    }
  }

  useEffect(() => {
    fetchWarnings()
    fetchStats()
  }, [page, filters])

  const handleResolve = async (id: number) => {
    await resolveWarning(id)
    message.success('已标记为已处理')
    fetchWarnings()
    fetchStats()
  }

  const handleDismiss = async (id: number) => {
    await dismissWarning(id)
    message.success('已标记为误报')
    fetchWarnings()
    fetchStats()
  }

  const handleViewDetail = async (id: number) => {
    const res: any = await getWarning(id)
    if (res?.data) {
      setDetailData(res.data)
      setDetailVisible(true)
    }
  }

  const getRiskColor = (score: number) => {
    if (score >= 80) return wanderMapColors.error
    if (score >= 60) return wanderMapColors.warning
    if (score >= 40) return '#F97316'
    return wanderMapColors.success
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24, color: wanderMapColors.textPrimary, fontWeight: 600 }}>
        预警中心
      </h2>

      {/* 统计卡片 */}
      <Row gutter={[20, 20]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #E8E8EC', boxShadow: 'none' }}>
            <Statistic
              title={<span style={{ color: wanderMapColors.textSecondary }}>活跃预警</span>}
              value={stats?.active_count || 0}
              valueStyle={{ color: wanderMapColors.error, fontWeight: 700 }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #E8E8EC', boxShadow: 'none' }}>
            <Statistic
              title={<span style={{ color: wanderMapColors.textSecondary }}>今日新增</span>}
              value={stats?.today_count || 0}
              valueStyle={{ color: wanderMapColors.secondary, fontWeight: 700 }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #E8E8EC', boxShadow: 'none' }}>
            <Statistic
              title={<span style={{ color: wanderMapColors.textSecondary }}>已处理</span>}
              value={stats?.resolved_count || 0}
              valueStyle={{ color: wanderMapColors.success, fontWeight: 700 }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #E8E8EC', boxShadow: 'none' }}>
            <Statistic
              title={<span style={{ color: wanderMapColors.textSecondary }}>误报率</span>}
              value={stats?.false_alarm_rate || 0}
              valueStyle={{ color: wanderMapColors.info, fontWeight: 700 }}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <Card style={{ borderRadius: 12, border: '1px solid #E8E8EC', boxShadow: 'none', marginBottom: 20 }}>
        <Space wrap>
          <Select
            placeholder="预警类型"
            allowClear
            style={{ width: 140 }}
            onChange={(v) => setFilters(f => ({ ...f, warning_type: v }))}
            options={[
              { label: '滞留', value: 'loiter' },
              { label: '反复接近', value: 'repeated_approach' },
              { label: '突然加速', value: 'acceleration' },
              { label: '非工作时间', value: 'off_hours' },
            ]}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setFilters(f => ({ ...f, status: v }))}
            options={[
              { label: '活跃', value: 'active' },
              { label: '已处理', value: 'resolved' },
              { label: '误报', value: 'dismissed' },
            ]}
          />
          <RangePicker
            onChange={(_, dateStrings) => {
              setFilters(f => ({
                ...f,
                start_time: dateStrings[0] || undefined,
                end_time: dateStrings[1] || undefined,
              }))
            }}
          />
        </Space>
      </Card>

      {/* 预警列表 */}
      <Row gutter={[16, 16]}>
        {warnings.map(item => {
          const typeInfo = WARNING_TYPE_MAP[item.warning_type] || { label: item.warning_type, color: '#999', icon: <WarningOutlined /> }
          const statusInfo = STATUS_MAP[item.status] || { label: item.status, color: 'default' }

          return (
            <Col span={12} key={item.id}>
              <Card
                style={{
                  borderRadius: 12,
                  border: 'none',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  borderLeft: `4px solid ${getRiskColor(item.risk_score)}`,
                }}
                bodyStyle={{ padding: '16px 20px' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ color: typeInfo.color, fontSize: 18 }}>{typeInfo.icon}</span>
                      <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
                      <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
                      <span style={{ fontSize: 12, color: wanderMapColors.textSecondary, marginLeft: 'auto' }}>
                        {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : ''}
                      </span>
                    </div>

                    <div style={{ marginBottom: 8, color: wanderMapColors.textPrimary, fontSize: 14 }}>
                      {item.description || '无描述'}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
                      <span style={{ fontSize: 12, color: wanderMapColors.textSecondary }}>
                        摄像头 #{item.camera_id}
                      </span>
                      <span style={{ fontSize: 12, color: wanderMapColors.textSecondary }}>
                        库房 #{item.room_id}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ fontSize: 12, color: wanderMapColors.textSecondary }}>风险分数</span>
                      <Progress
                        percent={item.risk_score}
                        size="small"
                        strokeColor={getRiskColor(item.risk_score)}
                        style={{ flex: 1, maxWidth: 200 }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginLeft: 12 }}>
                    <Button
                      size="small"
                      type="link"
                      icon={<EyeOutlined />}
                      onClick={() => handleViewDetail(item.id)}
                    >
                      详情
                    </Button>
                    {item.status === 'active' && (
                      <>
                        <Button size="small" type="primary" onClick={() => handleResolve(item.id)}>
                          处理
                        </Button>
                        <Button size="small" onClick={() => handleDismiss(item.id)}>
                          误报
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </Card>
            </Col>
          )
        })}
      </Row>

      {warnings.length === 0 && !loading && (
        <Card style={{ borderRadius: 12, textAlign: 'center', padding: 40, color: wanderMapColors.textSecondary }}>
          暂无预警数据
        </Card>
      )}

      {total > 20 && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            style={{ marginRight: 8 }}
          >
            上一页
          </Button>
          <span style={{ color: wanderMapColors.textSecondary }}>
            第 {page} 页 / 共 {Math.ceil(total / 20)} 页
          </span>
          <Button
            disabled={page >= Math.ceil(total / 20)}
            onClick={() => setPage(p => p + 1)}
            style={{ marginLeft: 8 }}
          >
            下一页
          </Button>
        </div>
      )}

      {/* 预警详情弹窗 */}
      <Modal
        title="预警详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {detailData && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <p><strong>预警类型：</strong>{WARNING_TYPE_MAP[detailData.warning_type]?.label || detailData.warning_type}</p>
                <p><strong>风险分数：</strong>{detailData.risk_score}</p>
                <p><strong>状态：</strong>{STATUS_MAP[detailData.status]?.label || detailData.status}</p>
              </Col>
              <Col span={12}>
                <p><strong>摄像头：</strong>#{detailData.camera_id}</p>
                <p><strong>库房：</strong>#{detailData.room_id}</p>
                <p><strong>时间：</strong>{detailData.created_at ? new Date(detailData.created_at).toLocaleString('zh-CN') : ''}</p>
              </Col>
            </Row>
            <p><strong>描述：</strong>{detailData.description}</p>

            {detailData.trajectory_data && (
              <div style={{ marginTop: 16 }}>
                <h4>轨迹可视化</h4>
                <TrajectoryView data={detailData.trajectory_data} />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
