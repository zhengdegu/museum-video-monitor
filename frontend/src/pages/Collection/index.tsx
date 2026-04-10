import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Popconfirm, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { getCollections, createCollection, updateCollection, deleteCollection, getRooms } from '../../services/api'

const statusMap: Record<number, { color: string; text: string }> = {
  1: { color: 'green', text: '在库' },
  2: { color: 'orange', text: '出库' },
  3: { color: 'blue', text: '展览中' },
}

export default function CollectionList() {
  const [data, setData] = useState<any[]>([])
  const [rooms, setRooms] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getCollections({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    getRooms({ page: 1, size: 100 }).then((r: any) => { if (r.code === 200) setRooms(r.data.items) })
  }, [page])

  const handleSave = async () => {
    const values = await form.validateFields()
    const res: any = editing ? await updateCollection(editing.id, values) : await createCollection(values)
    if (res.code === 200) { message.success('保存成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '藏品名称', dataIndex: 'name' },
    { title: '编号', dataIndex: 'code' },
    { title: '分类', dataIndex: 'category' },
    { title: '状态', dataIndex: 'status', render: (v: number) => <Tag color={statusMap[v]?.color}>{statusMap[v]?.text}</Tag> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => deleteCollection(record.id).then(() => { message.success('已删除'); fetchData() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>藏品管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增藏品</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title={editing ? '编辑藏品' : '新增藏品'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="藏品名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="code" label="编号"><Input /></Form.Item>
          <Form.Item name="room_id" label="所属库房">
            <Select allowClear options={rooms.map((r: any) => ({ value: r.id, label: r.name }))} placeholder="选择库房" />
          </Form.Item>
          <Form.Item name="category" label="分类"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[{ value: 1, label: '在库' }, { value: 2, label: '出库' }, { value: 3, label: '展览中' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
