import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Button, Table, Tag, Select, Modal, Space, message, InputNumber, Switch, Descriptions } from 'antd'
import { SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, QuestionCircleOutlined, WarningOutlined } from '@ant-design/icons'
import {
  triggerAiInventory, getAiInventoryTasks, getAiInventoryTaskDetail,
  getAiInventorySchedule, updateAiInventorySchedule, getAiInventoryStats, getRooms,
} from '../../services/api'
import InventoryCompare from '../../components/InventoryCompare'

const statusColorMap: Record<string, string> = {
  present: 'success',
  missing: 'error',
  displaced: 'warning',
  uncertain: 'default',
}
const statusTextMap: Record<string, string> = {
  present: '在位',
  missing: '缺失',
  displaced: '位移',
  uncertain: '不确定',
}
const taskStatusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  running: { color: 'processing', text: '执行中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
}

export default function AiInventory() {
  const [stats, setStats] = useState<any>(null)
  const [tasks, setTasks] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [rooms, setRooms] = useState<any[]>([])
  const [selectedRoom, setSelectedRoom] = useState<number | undefined>(undefined)
  const [triggering, setTriggering] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [taskDetail, setTaskDetail] = useState<any>(null)
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [schedules, setSchedules] = useState<any[]>([])
  const [scheduleRoom, setScheduleRoom] = useState<number | undefined>(undefined)
  const [scheduleHours, setScheduleHours] = useState(24)
  const [scheduleEnabled, setScheduleEnabled] = useState(true)

  const fetchStats = async () => {
    const res: any = await getAiInventoryStats(7)
    if (res.code === 200) setStats(res.data)
  }

  const fetchTasks = async (p = page) => {
    setLoading(true)
    const res: any = await getAiInventoryTasks({ page: p, size: 20 })
    if (res.code === 200) {
      setTasks(res.data.items)
      setTotal(res.data.total)
    }
    setLoading(false)
  }

  const fetchRooms = async () => {
    const res: any = await getRooms({ page: 1, size: 200 })
    if (res.code === 200) setRooms(res.data.items)
  }

  useEffect(() => {
    fetchStats()
    fetchTasks()
    fetchRooms()
  }, [])

  useEffect(() => { fetchTasks() }, [page])

  const handleTrigger = async () => {
    if (!selectedRoom) {
      message.warning('请选择库房')
      return
    }
    setTriggering(true)
    const res: any = await triggerAiInventory(selectedRoom)
    if (res.code === 200) {
      message.success('盘点任务已触发')
      setTimeout(() => fetchTasks(), 2000)
    } else {
      message.error(res.message || '触发失败')
    }
    setTriggering(false)
  }

  const handleViewDetail = async (taskId: number) => {
    const res: any = await getAiInventoryTaskDetail(taskId)
    if (res.code === 200) {
      setTaskDetail(res.data)
      setDetailOpen(true)
    }
  }

  const handleOpenSchedule = async () => {
    const res: any = await getAiInventorySchedule()
    if (res.code === 200) setSchedules(res.data)
    setScheduleOpen(true)
  }

  const handleSaveSchedule = async () => {
    if (!scheduleRoom) {
      message.warning('请选择库房')
      return
    }
    const res: any = await updateAiInventorySchedule({
      room_id: scheduleRoom,
      interval_hours: scheduleHours,
      enabled: scheduleEnabled ? 1 : 0,
    })
    if (res.code === 200) {
      message.success('配置已保存')
      const res2: any = await getAiInventorySchedule()
      if (res2.code === 200) setSchedules(res2.data)
    }
  }

  const taskColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '库房', dataIndex: 'room_id', width: 80 },
    {
      title: '触发方式', dataIndex: 'trigger_type', width: 90,
      render: (v: string) => v === 'manual' ? '手动' : '定时',
    },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={taskStatusMap[v]?.color}>{taskStatusMap[v]?.text}</Tag>,
    },
    { title: '总数', dataIndex: 'total_items', width: 60 },
    { title: '在位', dataIndex: 'matched_items', width: 60 },
    { title: '缺失', dataIndex: 'missing_items', width: 60 },
    { title: '不确定', dataIndex: 'uncertain_items', width: 70 },
    { title: '完成时间', dataIndex: 'completed_at', width: 170, ellipsis: true },
    {
      title: '操作', width: 80,
      render: (_: any, record: any) => (
        <Button size="small" onClick={() => handleViewDetail(record.id)} disabled={record.status !== 'completed'}>
          详情
        </Button>
      ),
    },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>AI 自动盘点</h2>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="在位率"
              value={stats?.present_rate || 0}
              suffix="%"
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="累计盘点次数"
              value={stats?.total_tasks || 0}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="累计缺失"
              value={stats?.total_missing || 0}
              prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最近盘点"
              value={stats?.last_inventory_at ? stats.last_inventory_at.split(' ')[0] : '暂无'}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作区 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Select
            placeholder="选择库房"
            style={{ width: 200 }}
            value={selectedRoom}
            onChange={setSelectedRoom}
            options={rooms.map((r: any) => ({ value: r.id, label: r.name }))}
          />
          <Button type="primary" icon={<SyncOutlined />} loading={triggering} onClick={handleTrigger}>
            触发盘点
          </Button>
          <Button onClick={handleOpenSchedule}>定时配置</Button>
          <Button onClick={() => { fetchTasks(); fetchStats() }}>刷新</Button>
        </Space>
      </Card>

      {/* 任务列表 */}
      <Table
        rowKey="id"
        columns={taskColumns}
        dataSource={tasks}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
      />

      {/* 任务详情弹窗 */}
      <Modal
        title="盘点详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={900}
      >
        {taskDetail && (
          <>
            <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="任务ID">{taskDetail.id}</Descriptions.Item>
              <Descriptions.Item label="库房ID">{taskDetail.room_id}</Descriptions.Item>
              <Descriptions.Item label="触发方式">{taskDetail.trigger_type === 'manual' ? '手动' : '定时'}</Descriptions.Item>
              <Descriptions.Item label="总数">{taskDetail.total_items}</Descriptions.Item>
              <Descriptions.Item label="在位">{taskDetail.matched_items}</Descriptions.Item>
              <Descriptions.Item label="缺失">{taskDetail.missing_items}</Descriptions.Item>
            </Descriptions>

            {taskDetail.results && taskDetail.results.length > 0 && (
              <InventoryCompare
                results={taskDetail.results}
                framePath={taskDetail.results[0]?.frame_path}
              />
            )}
          </>
        )}
      </Modal>

      {/* 定时配置弹窗 */}
      <Modal
        title="定时盘点配置"
        open={scheduleOpen}
        onCancel={() => setScheduleOpen(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <h4>当前配置</h4>
          {schedules.length === 0 ? (
            <p style={{ color: '#999' }}>暂无定时配置</p>
          ) : (
            <Table
              rowKey="id"
              size="small"
              dataSource={schedules}
              pagination={false}
              columns={[
                { title: '库房ID', dataIndex: 'room_id', width: 80 },
                { title: '间隔(小时)', dataIndex: 'interval_hours', width: 100 },
                { title: '状态', dataIndex: 'enabled', width: 80, render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag> },
                { title: '上次执行', dataIndex: 'last_run_at', ellipsis: true },
              ]}
            />
          )}
        </div>
        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
          <h4>新增/更新配置</h4>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Select
              placeholder="选择库房"
              style={{ width: '100%' }}
              value={scheduleRoom}
              onChange={setScheduleRoom}
              options={rooms.map((r: any) => ({ value: r.id, label: r.name }))}
            />
            <Space>
              <span>间隔:</span>
              <InputNumber min={1} max={720} value={scheduleHours} onChange={(v) => setScheduleHours(v || 24)} />
              <span>小时</span>
              <Switch checked={scheduleEnabled} onChange={setScheduleEnabled} checkedChildren="启用" unCheckedChildren="禁用" />
            </Space>
            <Button type="primary" onClick={handleSaveSchedule}>保存配置</Button>
          </Space>
        </div>
      </Modal>
    </div>
  )
}
