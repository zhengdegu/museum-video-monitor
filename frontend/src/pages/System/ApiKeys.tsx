import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Space, message, Tag, Typography, Alert } from 'antd'
import { PlusOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons'
import { getApiKeys, createApiKey, deleteApiKey, updateApiKey } from '../../services/api'

const { Paragraph } = Typography

export default function ApiKeys() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    const res: any = await getApiKeys()
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    const res: any = await createApiKey(values)
    if (res.code === 200) {
      setNewKey(res.data.key)
      message.success('API Key 创建成功')
      setCreateModalOpen(false)
      form.resetFields()
      fetchData()
    } else {
      message.error(res.message)
    }
  }

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除此 API Key 吗？',
      onOk: async () => {
        const res: any = await deleteApiKey(id)
        if (res.code === 200) { message.success('删除成功'); fetchData() }
        else message.error(res.message)
      },
    })
  }

  const handleToggle = async (id: number, currentStatus: number) => {
    const newStatus = currentStatus === 1 ? 0 : 1
    const res: any = await updateApiKey(id, { status: newStatus })
    if (res.code === 200) { message.success('操作成功'); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    { title: 'Key 前缀', dataIndex: 'key_prefix', render: (v: string) => <code>{v}...</code> },
    {
      title: '状态', dataIndex: 'status',
      render: (v: number) => <Tag color={v === 1 ? 'green' : 'red'}>{v === 1 ? '启用' : '禁用'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
    { title: '最后使用', dataIndex: 'last_used_at', render: (v: string) => v ? new Date(v).toLocaleString() : '从未使用' },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => handleToggle(record.id, record.status)}>
            {record.status === 1 ? '禁用' : '启用'}
          </Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>API Key 管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          创建 API Key
        </Button>
      </div>

      <Alert
        message="API Key 用于第三方系统对接，通过 X-API-Key 请求头进行认证"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} />

      <Modal
        title="创建 API Key"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Key 名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：第三方监控系统" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="API Key 已创建"
        open={!!newKey}
        onOk={() => setNewKey(null)}
        onCancel={() => setNewKey(null)}
        cancelButtonProps={{ style: { display: 'none' } }}
      >
        <Alert
          message="请立即复制保存此 Key，关闭后将无法再次查看！"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Paragraph copyable={{ text: newKey || '' }} style={{ background: '#f5f5f5', padding: 12, borderRadius: 6 }}>
          <code>{newKey}</code>
        </Paragraph>
      </Modal>
    </div>
  )
}
