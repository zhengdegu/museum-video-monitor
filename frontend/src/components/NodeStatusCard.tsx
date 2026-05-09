import { Card, Tag, Typography, Tooltip } from 'antd'
import {
  VideoCameraOutlined, AlertOutlined, WarningOutlined,
  ClockCircleOutlined, DesktopOutlined,
} from '@ant-design/icons'
import { wanderMapColors } from '../theme'

const { Text, Title } = Typography

interface NodeStats {
  cameras?: number
  cameras_online?: number
  events_today?: number
  warnings_active?: number
  disk_usage_pct?: number
  gpu_usage_pct?: number
}

export interface NodeData {
  id: number
  name: string
  location?: string
  node_url?: string
  api_key: string
  status: string
  version?: string
  last_heartbeat_at?: string
  system_info?: Record<string, any>
  stats?: NodeStats
  created_at?: string
}

interface NodeStatusCardProps {
  node: NodeData
  onClick?: () => void
}

const statusConfig: Record<string, { color: string; text: string; tagColor: string }> = {
  online: { color: wanderMapColors.success, text: '在线', tagColor: 'success' },
  offline: { color: wanderMapColors.error, text: '离线', tagColor: 'error' },
  warning: { color: wanderMapColors.warning, text: '警告', tagColor: 'warning' },
}

function formatTime(timeStr?: string) {
  if (!timeStr) return '从未上报'
  const d = new Date(timeStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return diff + '秒前'
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + '小时前'
  return d.toLocaleString('zh-CN')
}

function MiniBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div style={{ width: '100%', height: 4, borderRadius: 2, background: '#f0f0f0', overflow: 'hidden' }}>
      <div style={{
        width: pct + '%',
        height: '100%',
        borderRadius: 2,
        background: pct > 80 ? wanderMapColors.warning : wanderMapColors.primary,
        transition: 'width 0.3s',
      }} />
    </div>
  )
}

export default function NodeStatusCard({ node, onClick }: NodeStatusCardProps) {
  const cfg = statusConfig[node.status] || statusConfig.offline
  const stats = node.stats || {}

  return (
    <Card
      hoverable
      onClick={onClick}
      style={{ borderRadius: 12, cursor: 'pointer' }}
      styles={{ body: { padding: 20 } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>{node.name}</Title>
          {node.location && <Text type="secondary" style={{ fontSize: 12 }}>{node.location}</Text>}
        </div>
        <Tag color={cfg.tagColor} style={{ margin: 0 }}>
          <span style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: cfg.color,
            marginRight: 4,
            animation: node.status === 'online' ? 'pulse 2s infinite' : 'none',
          }} />
          {cfg.text}
        </Tag>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <VideoCameraOutlined style={{ color: wanderMapColors.primary }} />
          <Text style={{ fontSize: 13 }}>
            {'摄像头 ' + (stats.cameras_online ?? 0) + '/' + (stats.cameras ?? 0)}
          </Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertOutlined style={{ color: wanderMapColors.tertiary }} />
          <Text style={{ fontSize: 13 }}>{'今日事件 ' + (stats.events_today ?? 0)}</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <WarningOutlined style={{ color: wanderMapColors.warning }} />
          <Text style={{ fontSize: 13 }}>{'活跃预警 ' + (stats.warnings_active ?? 0)}</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <DesktopOutlined style={{ color: wanderMapColors.textSecondary }} />
          <Text style={{ fontSize: 13 }}>{node.version || '-'}</Text>
        </div>
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
          <Text style={{ fontSize: 12 }} type="secondary">磁盘</Text>
          <Text style={{ fontSize: 12 }} type="secondary">{(stats.disk_usage_pct ?? 0) + '%'}</Text>
        </div>
        <MiniBar value={stats.disk_usage_pct ?? 0} max={100} />
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
          <Text style={{ fontSize: 12 }} type="secondary">GPU</Text>
          <Text style={{ fontSize: 12 }} type="secondary">{(stats.gpu_usage_pct ?? 0) + '%'}</Text>
        </div>
        <MiniBar value={stats.gpu_usage_pct ?? 0} max={100} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <ClockCircleOutlined style={{ fontSize: 12, color: wanderMapColors.textSecondary }} />
        <Tooltip title={node.last_heartbeat_at}>
          <Text style={{ fontSize: 12 }} type="secondary">
            {'最后心跳: ' + formatTime(node.last_heartbeat_at)}
          </Text>
        </Tooltip>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </Card>
  )
}
