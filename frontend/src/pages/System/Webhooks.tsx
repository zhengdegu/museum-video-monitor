import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Tag, Drawer, Timeline } from 'antd'
import { PlusOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons'
import { getWebhooks, createWebhook, updateWebhook, deleteWebhook, getWebhookLogs, testWebhook } from '../../services/api'

const EVENT_TYPE_OPTIONS = [
  { value: 'all', label: '全部事件' },
  { value: 'violation', label: '违规事件' },
  { value: 'high_risk', label: '高风险事件' },
]

export default function Webhooks() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [logsDrawerOpen, setLogsDrawerOpen] = useState(false)
  const [logs, setLogs] = useState<any[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [secretModalOpen, setSecretModalOpen] = useState(false)
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    const res: any = await getWebhooks()
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleSave = async () => {
    const values = await form.validateFields()
    if (editing) {
      const res: any = await updateWebhook(editing.id, values)
      if (res.code === 200) { message.success('更新成功'); setModalOpen(false); fetchData() }
      else message.error(res.message)
    } else {
      const res: any = await createWebhook(values)
      if (res.code === 200) {
        setNewSecret(res.data.secret)
        setSecretModalOpen(true)
        setModalOpen(false)
        form.resetFields()
        fetchData()
      } else {
        message.error(res.message)
      }
    }
  }

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除此 Webhook 吗？',
      onOk: async () => {
        const res: any = await deleteWebhook(id)
        if (res.code === 200) { message.success('删除成功'); fetchData() }
        else message.error(res.message)
      },
    })
  }

  const handleTest = async (id: number) => {
    const res: any = await testWebhook(id)
    if (res.code === 200 && res.data?.success) {
      message.success('测试事件发送成功')
    } else {
      message.warning(res.data?.message || '测试发送失败')
    }
  }

  const handleViewLogs = async (webhookId: number) => {
    setLogsDrawerOpen(true)
    setLogsLoading(true)
    const res: any = await getWebhookLogs(webhookId)
    if (res.code === 200) setLogs(res.data)
    setLogsLoading(false)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'URL', dataIndex: 'url', ellipsis: true },
    {
      title: '事件类型', dataIndex: 'event_types',
      render: (v: string[]) => v?.map((t: string) => <Tag key={t}>{t}</Tag>) || '-',
    },
    {
      title: '状态', dataIndex: 'status',
      render: (v: number) => <Tag color={v === 1 ? 'green' : 'red'}>{v === 1 ? '启用' : '禁用'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>
            编辑
          </Button>
          <Button size="small" icon={<SendOutlined />} onClick={() => handleTest(record.id)}>
            测试
          </Button>
          <Button size="small" onClick={() => handleViewLogs(record.id)}>
            日志
          </Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ]

  const logColumns = [
    { title: '事件类型', dataIndex: 'event_type', width: 100 },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => (
        <Tag color={v === 'success' ? 'green' : v === 'failed' ? 'red' : 'orange'}>{v}</Tag>
      ),
    },
    { title: '响应码', dataIndex: 'response_code', width: 80, render: (v: number | null) => v ?? '-' },
    { title: '尝试次数', dataIndex: 'attempts', width: 80 },
    { title: '时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>Webhook 管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>
          添加 Webhook
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} />

      <Modal
        title={editing ? '编辑 Webhook' : '添加 Webhook'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="url" label="回调 URL" rules={[{ required: true, message: '请输入 URL' }]}>
            <Input placeholder="https://your-server.com/webhook" />
          </Form.Item>
          <Form.Item name="event_types" label="订阅事件类型" rules={[{ required: true, message: '请选择事件类型' }]}>
            <Select mode="multiple" options={EVENT_TYPE_OPTIONS} placeholder="选择要订阅的事件类型" />
          </Form.Item>
          {editing && (
            <Form.Item name="status" label="状态">
              <Select options={[{ value: 1, label: '启用' }, { value: 0, label: '禁用' }]} />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title="Webhook 已创建"
        open={secretModalOpen}
        onOk={() => setSecretModalOpen(false)}
        onCancel={() => setSecretModalOpen(false)}
        cancelButtonProps={{ style: { display: 'none' } }}
      >
        <p>请保存以下签名密钥，用于验证 Webhook 请求的 HMAC-SHA256 签名：</p>
        <p style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, wordBreak: 'break-all' }}>
          <code>{newSecret}</code>
        </p>
        <p style={{ color: '#999' }}>此密钥仅显示一次，请妥善保管。</p>
      </Modal>

      <Drawer
        title="投递日志"
        open={logsDrawerOpen}
        onClose={() => setLogsDrawerOpen(false)}
        width={700}
      >
        <Table
          rowKey="id"
          columns={logColumns}
          dataSource={logs}
          loading={logsLoading}
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Drawer>
    </div>
  )
}
