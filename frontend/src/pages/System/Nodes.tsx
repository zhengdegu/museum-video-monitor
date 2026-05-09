import { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Modal, Form, Input, Space, message, Drawer, Descriptions, Typography, Statistic, Empty, Spin, Popconfirm } from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  GlobalOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined,
} from '@ant-design/icons'
import NodeStatusCard, { type NodeData } from '../../components/NodeStatusCard'
import { getNodes, getNodesOverview, createNode, deleteNode } from '../../services/api'
import { wanderMapColors } from '../../theme'

const { Title, Text, Paragraph } = Typography

export default function Nodes() {
  const [nodes, setNodes] = useState<NodeData[]>([])
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false)
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const [nodesRes, overviewRes]: any[] = await Promise.all([
        getNodes(),
        getNodesOverview(),
      ])
      if (nodesRes.code === 200) setNodes(nodesRes.data)
      if (overviewRes.code === 200) setOverview(overviewRes.data)
    } catch (e) {
      message.error('加载节点数据失败')
    }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  useEffect(() => {
    const timer = setInterval(fetchData, 30000)
    return () => clearInterval(timer)
  }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    const res: any = await createNode(values)
    if (res.code === 200) {
      message.success('节点注册成功')
      Modal.info({
        title: '节点 API Key',
        content: (
          <div>
            <Paragraph>请妥善保存以下 API Key，用于节点心跳认证：</Paragraph>
            <Paragraph copyable strong style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
              {res.data.api_key}
            </Paragraph>
            <Paragraph type="secondary">此 Key 仅显示一次，请立即复制保存。</Paragraph>
          </div>
        ),
        width: 500,
      })
      setCreateModalOpen(false)
      form.resetFields()
      fetchData()
    } else {
      message.error(res.message || '注册失败')
    }
  }

  const handleDelete = async (id: number) => {
    const res: any = await deleteNode(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
      if (selectedNode?.id === id) {
        setDetailDrawerOpen(false)
        setSelectedNode(null)
      }
    }
  }

  const handleNodeClick = (node: NodeData) => {
    setSelectedNode(node)
    setDetailDrawerOpen(true)
  }

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总节点数"
              value={overview?.total_nodes ?? 0}
              prefix={<GlobalOutlined style={{ color: wanderMapColors.primary }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在线节点"
              value={overview?.online ?? 0}
              prefix={<CheckCircleOutlined style={{ color: wanderMapColors.success }} />}
              valueStyle={{ color: wanderMapColors.success }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="离线节点"
              value={overview?.offline ?? 0}
              prefix={<CloseCircleOutlined style={{ color: wanderMapColors.error }} />}
              valueStyle={{ color: wanderMapColors.error }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日总事件"
              value={overview?.total_events_today ?? 0}
              prefix={<WarningOutlined style={{ color: wanderMapColors.warning }} />}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>节点列表</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            注册节点
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {nodes.length === 0 ? (
          <Empty description="暂无注册节点" style={{ marginTop: 60 }} />
        ) : (
          <Row gutter={[16, 16]}>
            {nodes.map((node) => (
              <Col key={node.id} xs={24} sm={12} xl={6}>
                <NodeStatusCard node={node} onClick={() => handleNodeClick(node)} />
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      <Modal
        title="注册新节点"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateModalOpen(false); form.resetFields() }}
        okText="注册"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="节点名称" rules={[{ required: true, message: '请输入节点名称' }]}>
            <Input placeholder="如：北京故宫博物院" />
          </Form.Item>
          <Form.Item name="location" label="节点位置">
            <Input placeholder="如：北京市东城区" />
          </Form.Item>
          <Form.Item name="node_url" label="节点地址">
            <Input placeholder="如：https://node1.example.com" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={selectedNode?.name || '节点详情'}
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
        width={480}
        extra={
          <Popconfirm
            title="确定删除该节点？"
            onConfirm={() => selectedNode && handleDelete(selectedNode.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        }
      >
        {selectedNode && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="节点ID">{selectedNode.id}</Descriptions.Item>
              <Descriptions.Item label="名称">{selectedNode.name}</Descriptions.Item>
              <Descriptions.Item label="位置">{selectedNode.location || '-'}</Descriptions.Item>
              <Descriptions.Item label="地址">{selectedNode.node_url || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">{selectedNode.status}</Descriptions.Item>
              <Descriptions.Item label="版本">{selectedNode.version || '-'}</Descriptions.Item>
              <Descriptions.Item label="最后心跳">{selectedNode.last_heartbeat_at || '从未上报'}</Descriptions.Item>
              <Descriptions.Item label="注册时间">{selectedNode.created_at || '-'}</Descriptions.Item>
            </Descriptions>

            {selectedNode.system_info && (
              <>
                <Title level={5}>系统信息</Title>
                <Descriptions column={1} bordered size="small" style={{ marginBottom: 24 }}>
                  {Object.entries(selectedNode.system_info).map(([key, val]) => (
                    <Descriptions.Item key={key} label={key}>{String(val)}</Descriptions.Item>
                  ))}
                </Descriptions>
              </>
            )}

            {selectedNode.stats && (
              <>
                <Title level={5}>运行统计</Title>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="摄像头">{selectedNode.stats.cameras ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="在线">{selectedNode.stats.cameras_online ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="今日事件">{selectedNode.stats.events_today ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="活跃预警">{selectedNode.stats.warnings_active ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="磁盘使用">{(selectedNode.stats.disk_usage_pct ?? 0) + '%'}</Descriptions.Item>
                  <Descriptions.Item label="GPU使用">{(selectedNode.stats.gpu_usage_pct ?? 0) + '%'}</Descriptions.Item>
                </Descriptions>
              </>
            )}

            <div style={{ marginTop: 24 }}>
              <Text type="secondary">{'API Key: ' + selectedNode.api_key.slice(0, 8) + '...'}</Text>
            </div>
          </>
        )}
      </Drawer>
    </div>
  )
}
