import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Popconfirm } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { getRooms, createRoom, updateRoom, deleteRoom } from '../../services/api'

export default function RoomList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getRooms({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page])

  const handleSave = async () => {
    const values = await form.validateFields()
    const res: any = editing ? await updateRoom(editing.id, values) : await createRoom(values)
    if (res.code === 200) { message.success('保存成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const handleDelete = async (id: number) => {
    const res: any = await deleteRoom(id)
    if (res.code === 200) { message.success('删除成功'); fetchData() }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '库房名称', dataIndex: 'name' },
    { title: '编号', dataIndex: 'code' },
    { title: '位置', dataIndex: 'location' },
    { title: '状态', dataIndex: 'status', render: (v: number) => v === 1 ? '启用' : '禁用' },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}><Button size="small" danger>删除</Button></Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>库房管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增库房</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title={editing ? '编辑库房' : '新增库房'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="库房名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="code" label="编号"><Input /></Form.Item>
          <Form.Item name="location" label="位置"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea /></Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}><Select options={[{ value: 1, label: '启用' }, { value: 0, label: '禁用' }]} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
