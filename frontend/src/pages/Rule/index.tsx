import { useEffect, useState } from 'react'
import { Table, Button, Switch, Space, message, Popconfirm } from 'antd'
import { getRules, toggleRule, deleteRule } from '../../services/api'

export default function RuleList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const fetchData = async (p = page) => {
    setLoading(true)
    const res: any = await getRules({ page: p, size: 20 })
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page])

  const handleToggle = async (id: number) => {
    const res: any = await toggleRule(id)
    if (res.code === 200) { message.success('已切换'); fetchData() }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '规则名称', dataIndex: 'name' },
    { title: '编码', dataIndex: 'code' },
    { title: '类型', dataIndex: 'rule_type' },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '启用', dataIndex: 'enabled', render: (v: number, record: any) => <Switch checked={v === 1} onChange={() => handleToggle(record.id)} /> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Popconfirm title="确认删除？" onConfirm={() => deleteRule(record.id).then(() => { message.success('已删除'); fetchData() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}><h2>规则管理</h2></div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  )
}
