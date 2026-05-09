import { Tag, Row, Col, Table, Image } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, QuestionCircleOutlined } from '@ant-design/icons'

const statusConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  present: { color: 'success', text: '在位', icon: <CheckCircleOutlined /> },
  missing: { color: 'error', text: '缺失', icon: <CloseCircleOutlined /> },
  displaced: { color: 'warning', text: '位移', icon: <WarningOutlined /> },
  uncertain: { color: 'default', text: '不确定', icon: <QuestionCircleOutlined /> },
}

interface ResultItem {
  id: number
  collection_id: number
  collection_name: string
  collection_code: string
  status: string
  confidence: number
  description: string
  frame_path: string | null
}

interface Props {
  results: ResultItem[]
  framePath?: string | null
}

export default function InventoryCompare({ results, framePath }: Props) {
  const columns = [
    { title: '藏品编号', dataIndex: 'collection_code', width: 100 },
    { title: '藏品名称', dataIndex: 'collection_name', width: 150, ellipsis: true },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => {
        const cfg = statusConfig[v] || statusConfig.uncertain
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.text}</Tag>
      },
    },
    {
      title: '置信度', dataIndex: 'confidence', width: 80,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    { title: '说明', dataIndex: 'description', ellipsis: true },
  ]

  const alertItems = results.filter(r => r.status === 'missing' || r.status === 'displaced')

  return (
    <div>
      <Row gutter={16}>
        <Col span={10}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>摄像头截图</div>
          {framePath ? (
            <Image
              src={`/api/v1/static/${framePath}`}
              alt="inventory frame"
              style={{ width: '100%', borderRadius: 8, border: '1px solid #f0f0f0' }}
              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN8/+F/PQAJpAN42kzLmAAAAABJRU5ErkJggg=="
            />
          ) : (
            <div style={{ height: 200, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 8 }}>
              <span style={{ color: '#999' }}>暂无截图</span>
            </div>
          )}
          {alertItems.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#ff4d4f' }}>异常藏品</div>
              {alertItems.map(item => (
                <div key={item.id} style={{ marginBottom: 4, padding: '4px 8px', background: item.status === 'missing' ? '#fff2f0' : '#fffbe6', borderRadius: 4 }}>
                  <Tag color={statusConfig[item.status]?.color}>{statusConfig[item.status]?.text}</Tag>
                  <span>{item.collection_name} ({item.collection_code})</span>
                </div>
              ))}
            </div>
          )}
        </Col>

        <Col span={14}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>藏品清单 + 状态</div>
          <Table
            rowKey="id"
            size="small"
            columns={columns}
            dataSource={results}
            pagination={false}
            scroll={{ y: 400 }}
            rowClassName={(record) => {
              if (record.status === 'missing') return 'row-missing'
              if (record.status === 'displaced') return 'row-displaced'
              return ''
            }}
          />
        </Col>
      </Row>

      <style>{`
        .row-missing td { background: #fff2f0 !important; }
        .row-displaced td { background: #fffbe6 !important; }
      `}</style>
    </div>
  )
}
