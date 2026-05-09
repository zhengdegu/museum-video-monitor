import { useEffect, useState } from 'react'
import { Table, Button, Space, Modal, Form, Input, Select, InputNumber, Switch, Tag, message, Tabs, Popconfirm } from 'antd'
import { getPushChannels, createPushChannel, updatePushChannel, deletePushChannel, testPushChannel, getPushLogs } from '../../services/api'

const channelTypeOptions = [
  { value: 'feishu', label: '飞书' },
  { value: 'dingtalk', label: '钉钉' },
  { value: 'email', label: '邮件' },
  { value: 'serverchan', label: 'Server酱' },
]

const riskLevelOptions = [
  { value: 0, label: '全部(0+)' },
  { value: 1, label: '低风险(1+)' },
  { value: 2, label: '中风险(2+)' },
  { value: 3, label: '仅高风险(3)' },
]

export default function PushChannels() {
  const [channels, setChannels] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()
  const [channelType, setChannelType] = useState<string>('feishu')
  const [tabKey, setTabKey] = useState('channels')
  const [logs, setLogs] = useState<any[]>([])
  const [logTotal, setLogTotal] = useState(0)
  const [logPage, setLogPage] = useState(1)
  const [logLoading, setLogLoading] = useState(false)

  const fetchChannels = async () => {
    setLoading(true)
    const res: any = await getPushChannels()
    if (res.code === 200) setChannels(res.data || [])
    setLoading(false)
  }

  const fetchLogs = async (p = logPage) => {
    setLogLoading(true)
    const res: any = await getPushLogs({ page: p, size: 20 })
    if (res.code === 200) { setLogs(res.data.items || []); setLogTotal(res.data.total) }
    setLogLoading(false)
  }

  useEffect(() => { fetchChannels() }, [])
  useEffect(() => { if (tabKey === 'logs') fetchLogs() }, [tabKey, logPage])

  const openCreate = () => {
    setEditing(null)
    setChannelType('feishu')
    form.resetFields()
    form.setFieldsValue({ channel_type: 'feishu', enabled: true, min_risk_level: 0 })
    setModalOpen(true)
  }

  const openEdit = (record: any) => {
    setEditing(record)
    setChannelType(record.channel_type)
    form.setFieldsValue({
      ...record,
      enabled: record.enabled === 1,
      ...record.config,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const { channel_type, name, enabled, min_risk_level, ...configFields } = values
    const data = {
      channel_type,
      name,
      enabled: enabled ? 1 : 0,
      min_risk_level,
      config: configFields,
    }

    let res: any
    if (editing) {
      res = await updatePushChannel(editing.id, data)
    } else {
      res = await createPushChannel(data)
    }

    if (res.code === 200) {
      message.success(editing ? '更新成功' : '创建成功')
      setModalOpen(false)
      fetchChannels()
    } else {
      message.error(res.message)
    }
  }

  const handleDelete = async (id: number) => {
    const res: any = await deletePushChannel(id)
    if (res.code === 200) { message.success('删除成功'); fetchChannels() }
    else message.error(res.message)
  }

  const handleTest = async (id: number) => {
    const res: any = await testPushChannel(id)
    if (res.code === 200) message.success('测试消息发送成功')
    else message.error(res.message || '测试失败')
  }

  const channelColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '类型', dataIndex: 'channel_type', width: 100, render: (v: string) => {
      const opt = channelTypeOptions.find(o => o.value === v)
      return <Tag>{opt?.label || v}</Tag>
    }},
    { title: '名称', dataIndex: 'name' },
    { title: '状态', dataIndex: 'enabled', width: 80, render: (v: number) => v === 1 ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag> },
    { title: '最低风险等级', dataIndex: 'min_risk_level', width: 120, render: (v: number) => riskLevelOptions.find(o => o.value === v)?.label || v },
    { title: '创建时间', dataIndex: 'created_at', width: 180 },
    { title: '操作', width: 220, render: (_: any, record: any) => (
      <Space>
        <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
        <Button size="small" type="primary" onClick={() => handleTest(record.id)}>测试</Button>
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ]

  const logColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '渠道ID', dataIndex: 'channel_id', width: 80 },
    { title: '事件ID', dataIndex: 'event_id', width: 80 },
    { title: '状态', dataIndex: 'status', width: 80, render: (v: string) => <Tag color={v === 'success' ? 'green' : 'red'}>{v}</Tag> },
    { title: '响应', dataIndex: 'response', ellipsis: true },
    { title: '发送时间', dataIndex: 'sent_at', width: 180 },
  ]

  const renderConfigFields = () => {
    switch (channelType) {
      case 'feishu':
      case 'dingtalk':
        return <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true }]}><Input placeholder="https://..." /></Form.Item>
      case 'email':
        return (
          <>
            <Form.Item name="smtp_host" label="SMTP 主机" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="smtp_port" label="SMTP 端口"><InputNumber style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
            <Form.Item name="sender" label="发件人"><Input placeholder="默认同用户名" /></Form.Item>
            <Form.Item name="recipients" label="收件人(逗号分隔)" rules={[{ required: true }]}><Input placeholder="a@x.com,b@x.com" /></Form.Item>
            <Form.Item name="use_tls" label="使用 TLS" valuePropName="checked"><Switch defaultChecked /></Form.Item>
          </>
        )
      case 'serverchan':
        return <Form.Item name="key" label="SendKey" rules={[{ required: true }]}><Input placeholder="SCT..." /></Form.Item>
      default:
        return null
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>推送渠道管理</h2>
      </div>

      <Tabs activeKey={tabKey} onChange={setTabKey} items={[
        { key: 'channels', label: '渠道配置' },
        { key: 'logs', label: '推送日志' },
      ]} />

      {tabKey === 'channels' && (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" onClick={openCreate}>新增渠道</Button>
          </div>
          <Table rowKey="id" columns={channelColumns} dataSource={channels} loading={loading} pagination={false} />
        </>
      )}

      {tabKey === 'logs' && (
        <Table rowKey="id" columns={logColumns} dataSource={logs} loading={logLoading}
          pagination={{ current: logPage, total: logTotal, pageSize: 20, onChange: setLogPage }} />
      )}

      <Modal
        title={editing ? '编辑推送渠道' : '新增推送渠道'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Select options={channelTypeOptions} onChange={setChannelType} disabled={!!editing} />
          </Form.Item>
          <Form.Item name="name" label="渠道名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="min_risk_level" label="最低推送风险等级">
            <Select options={riskLevelOptions} />
          </Form.Item>
          {renderConfigFields()}
        </Form>
      </Modal>
    </div>
  )
}
