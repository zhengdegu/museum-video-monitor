import { useEffect, useState } from 'react'
import { Tabs, Table, Button, Modal, Form, Input, InputNumber, Select, Space, message, Popconfirm, Tag, DatePicker } from 'antd'
import { PlusOutlined, DownloadOutlined } from '@ant-design/icons'
import {
  getInventoryChecks, createInventoryCheck, updateInventoryCheck, deleteInventoryCheck,
  exportInventoryCheck, getMovements, createMovement, getRooms, getCollections,
} from '../../services/api'

const checkStatusMap: Record<number, { color: string; text: string }> = {
  0: { color: 'processing', text: '进行中' },
  1: { color: 'success', text: '已完成' },
}
const moveTypeMap: Record<number, { color: string; text: string }> = {
  1: { color: 'green', text: '入库' },
  2: { color: 'orange', text: '出库' },
  3: { color: 'blue', text: '移库' },
}

export default function InventoryPage() {
  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>盘点与进出库</h2>
      <Tabs items={[
        { key: 'checks', label: '盘点管理', children: <ChecksTab /> },
        { key: 'movements', label: '进出库记录', children: <MovementsTab /> },
      ]} />
    </div>
  )
}

function ChecksTab() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [rooms, setRooms] = useState<any[]>([])
  const [form] = Form.useForm()

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getInventoryChecks({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    getRooms({ page: 1, size: 200 }).then((r: any) => { if (r.code === 200) setRooms(r.data.items) })
  }, [page])

  const handleSave = async () => {
    const values = await form.validateFields()
    if (values.check_date) values.check_date = values.check_date.format('YYYY-MM-DD')
    const res: any = editing
      ? await updateInventoryCheck(editing.id, values)
      : await createInventoryCheck(values)
    if (res.code === 200) { message.success('保存成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '库房ID', dataIndex: 'room_id', width: 80 },
    { title: '盘点日期', dataIndex: 'check_date', width: 120 },
    { title: '应盘', dataIndex: 'total_count', width: 70 },
    { title: '已盘', dataIndex: 'checked_count', width: 70 },
    { title: '一致', dataIndex: 'matched_count', width: 70 },
    { title: '不一致', dataIndex: 'mismatched_count', width: 80 },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: number) => <Tag color={checkStatusMap[v]?.color}>{checkStatusMap[v]?.text}</Tag> },
    { title: '操作人', dataIndex: 'operator', width: 90 },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => window.open(exportInventoryCheck(record.id))}>导出</Button>
          <Popconfirm title="确认删除？" onConfirm={() => deleteInventoryCheck(record.id).then(() => { message.success('已删除'); fetchData() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增盘点</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title={editing ? '编辑盘点' : '新增盘点'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          {!editing && (
            <>
              <Form.Item name="room_id" label="库房" rules={[{ required: true }]}>
                <Select options={rooms.map((r: any) => ({ value: r.id, label: r.name }))} placeholder="选择库房" />
              </Form.Item>
              <Form.Item name="check_date" label="盘点日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="total_count" label="应盘数量"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="operator" label="操作人"><Input /></Form.Item>
            </>
          )}
          <Form.Item name="checked_count" label="已盘数量"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="matched_count" label="一致数量"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="mismatched_count" label="不一致数量"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ value: 0, label: '进行中' }, { value: 1, label: '已完成' }]} />
          </Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

function MovementsTab() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [rooms, setRooms] = useState<any[]>([])
  const [collections, setCollections] = useState<any[]>([])
  const [form] = Form.useForm()

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getMovements({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    getRooms({ page: 1, size: 200 }).then((r: any) => { if (r.code === 200) setRooms(r.data.items) })
    getCollections({ page: 1, size: 500 }).then((r: any) => { if (r.code === 200) setCollections(r.data.items) })
  }, [page])

  const handleSave = async () => {
    const values = await form.validateFields()
    const res: any = await createMovement(values)
    if (res.code === 200) { message.success('记录成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '藏品ID', dataIndex: 'collection_id', width: 80 },
    { title: '库房ID', dataIndex: 'room_id', width: 80 },
    { title: '类型', dataIndex: 'movement_type', width: 80, render: (v: number) => <Tag color={moveTypeMap[v]?.color}>{moveTypeMap[v]?.text}</Tag> },
    { title: '原因', dataIndex: 'reason', ellipsis: true },
    { title: '操作人', dataIndex: 'operator', width: 90 },
    { title: '操作时间', dataIndex: 'moved_at', width: 180 },
  ]

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setModalOpen(true) }}>新增记录</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title="新增进出库记录" open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="collection_id" label="藏品" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label"
              options={collections.map((c: any) => ({ value: c.id, label: `${c.name} (${c.code || c.id})` }))} placeholder="选择藏品" />
          </Form.Item>
          <Form.Item name="movement_type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ value: 1, label: '入库' }, { value: 2, label: '出库' }, { value: 3, label: '移库' }]} />
          </Form.Item>
          <Form.Item name="room_id" label="目标库房">
            <Select allowClear options={rooms.map((r: any) => ({ value: r.id, label: r.name }))} placeholder="选择库房" />
          </Form.Item>
          <Form.Item name="reason" label="原因"><Input /></Form.Item>
          <Form.Item name="operator" label="操作人"><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}
