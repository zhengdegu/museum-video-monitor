import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, Space, message, Popconfirm, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { getCameras, createCamera, updateCamera, deleteCamera, getRooms } from '../../services/api'

export default function CameraList() {
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
    const res: any = await getCameras({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    getRooms({ page: 1, size: 100 }).then((r: any) => { if (r.code === 200) setRooms(r.data.items) })
  }, [page])

  const handleSave = async () => {
    const values = await form.validateFields()
    const res: any = editing ? await updateCamera(editing.id, values) : await createCamera(values)
    if (res.code === 200) { message.success('保存成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const statusMap: Record<number, { color: string; text: string }> = {
    1: { color: 'green', text: '在线' },
    2: { color: 'red', text: '离线' },
    3: { color: 'blue', text: '拉流中' },
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '摄像头名称', dataIndex: 'name' },
    { title: 'RTSP地址', dataIndex: 'rtsp_url', ellipsis: true },
    { title: '分段时长(秒)', dataIndex: 'segment_duration' },
    { title: '状态', dataIndex: 'status', render: (v: number) => <Tag color={statusMap[v]?.color}>{statusMap[v]?.text}</Tag> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => deleteCamera(record.id).then(() => { message.success('已删除'); fetchData() })}><Button size="small" danger>删除</Button></Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>摄像头管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增摄像头</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title={editing ? '编辑摄像头' : '新增摄像头'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="room_id" label="所属库房" rules={[{ required: true }]}>
            <Select options={rooms.map((r: any) => ({ value: r.id, label: r.name }))} placeholder="选择库房" />
          </Form.Item>
          <Form.Item name="name" label="摄像头名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="rtsp_url" label="RTSP地址" rules={[{ required: true }]}><Input placeholder="rtsp://..." /></Form.Item>
          <Form.Item name="segment_duration" label="分段时长(秒)" initialValue={10800}><InputNumber min={60} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
