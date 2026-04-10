import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { getUsers, createUser, updateUser, getRoles } from '../../services/api'

export default function UserList() {
  const [data, setData] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    const res: any = await getUsers()
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    getRoles().then((r: any) => { if (r.code === 200) setRoles(r.data) })
  }, [])

  const handleSave = async () => {
    const values = await form.validateFields()
    const res: any = editing ? await updateUser(editing.id, values) : await createUser(values)
    if (res.code === 200) { message.success('保存成功'); setModalOpen(false); fetchData() }
    else message.error(res.message)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username' },
    { title: '姓名', dataIndex: 'real_name' },
    { title: '角色', dataIndex: 'role_id', render: (v: number) => roles.find((r) => r.id === v)?.name || '-' },
    { title: '状态', dataIndex: 'status', render: (v: number) => <Tag color={v === 1 ? 'green' : 'red'}>{v === 1 ? '启用' : '禁用'}</Tag> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>用户管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增用户</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} />
      <Modal title={editing ? '编辑用户' : '新增用户'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          {!editing && <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input /></Form.Item>}
          {!editing && <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password /></Form.Item>}
          <Form.Item name="real_name" label="姓名"><Input /></Form.Item>
          <Form.Item name="role_id" label="角色">
            <Select options={roles.map((r: any) => ({ value: r.id, label: r.name }))} placeholder="选择角色" />
          </Form.Item>
          {editing && (
            <Form.Item name="status" label="状态">
              <Select options={[{ value: 1, label: '启用' }, { value: 0, label: '禁用' }]} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
