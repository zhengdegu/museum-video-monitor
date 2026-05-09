import { useState, useEffect, useCallback } from 'react'
import { Card, Select, Switch, Space, Button, Modal, Descriptions, Badge, List, Tag, message } from 'antd'
import {
  EditOutlined, HeatMapOutlined,
  VideoCameraOutlined, ReloadOutlined,
} from '@ant-design/icons'
import RoomMap from '../../components/RoomMap'
import RoomLayoutEditor from '../../components/RoomLayoutEditor'
import { getRooms, getCameras, getCollections, getRoomLayout, saveRoomLayout, getRoomHeatmap, getRoomLiveStatus } from '../../services/api'

interface RoomOption {
  id: number
  name: string
}

interface LayoutData {
  cameras: any[]
  collections: any[]
  zones: any[]
  walls: any[]
}

export default function RoomMapPage() {
  const [rooms, setRooms] = useState<RoomOption[]>([])
  const [selectedRoomId, setSelectedRoomId] = useState<number | null>(null)
  const [layoutData, setLayoutData] = useState<LayoutData | null>(null)
  const [roomWidth, setRoomWidth] = useState(1000)
  const [roomHeight, setRoomHeight] = useState(800)
  const [heatmapPoints, setHeatmapPoints] = useState<any[]>([])
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [heatmapHours, setHeatmapHours] = useState(24)
  const [editMode, setEditMode] = useState(false)
  const [liveStatus, setLiveStatus] = useState<any>(null)
  const [cameras, setCameras] = useState<{ id: number; name: string }[]>([])
  const [collections, setCollections] = useState<{ id: number; name: string }[]>([])
  const [cameraPreviewId, setCameraPreviewId] = useState<number | null>(null)
  const [collectionDetailId, setCollectionDetailId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  // Load rooms
  useEffect(() => {
    getRooms({ page: 1, size: 100 }).then((res: any) => {
      const items = res?.data?.data?.items || []
      setRooms(items.map((r: any) => ({ id: r.id, name: r.name })))
      if (items.length > 0 && !selectedRoomId) {
        setSelectedRoomId(items[0].id)
      }
    })
  }, [])

  // Load layout when room changes
  useEffect(() => {
    if (!selectedRoomId) return
    setLoading(true)
    getRoomLayout(selectedRoomId).then((res: any) => {
      const data = res?.data?.data
      if (data) {
        setRoomWidth(data.width || 1000)
        setRoomHeight(data.height || 800)
        setLayoutData(data.layout_data || { cameras: [], collections: [], zones: [], walls: [] })
      } else {
        setRoomWidth(1000)
        setRoomHeight(800)
        setLayoutData({ cameras: [], collections: [], zones: [], walls: [] })
      }
    }).finally(() => setLoading(false))

    // Load cameras and collections for this room
    getCameras({ room_id: selectedRoomId, page: 1, size: 100 }).then((res: any) => {
      const items = res?.data?.data?.items || []
      setCameras(items.map((c: any) => ({ id: c.id, name: c.name })))
    })
    getCollections({ room_id: selectedRoomId, page: 1, size: 200 }).then((res: any) => {
      const items = res?.data?.data?.items || []
      setCollections(items.map((c: any) => ({ id: c.id, name: c.name })))
    })

    // Load live status
    loadLiveStatus()
  }, [selectedRoomId])

  // Load heatmap when toggled
  useEffect(() => {
    if (showHeatmap && selectedRoomId) {
      getRoomHeatmap(selectedRoomId, heatmapHours).then((res: any) => {
        setHeatmapPoints(res?.data?.data?.points || [])
      })
    }
  }, [showHeatmap, heatmapHours, selectedRoomId])

  const loadLiveStatus = useCallback(() => {
    if (!selectedRoomId) return
    getRoomLiveStatus(selectedRoomId).then((res: any) => {
      setLiveStatus(res?.data?.data || null)
    })
  }, [selectedRoomId])

  // Auto refresh live status
  useEffect(() => {
    if (!selectedRoomId) return
    const timer = setInterval(loadLiveStatus, 30000)
    return () => clearInterval(timer)
  }, [selectedRoomId, loadLiveStatus])

  const handleSaveLayout = async (data: LayoutData) => {
    if (!selectedRoomId) return
    try {
      await saveRoomLayout(selectedRoomId, {
        width: roomWidth,
        height: roomHeight,
        layout_data: data,
      })
      setLayoutData(data)
      setEditMode(false)
      message.success('布局保存成功')
    } catch {
      message.error('保存失败')
    }
  }

  const handleCameraClick = (cameraId: number) => {
    setCameraPreviewId(cameraId)
  }

  const handleCollectionClick = (collectionId: number) => {
    setCollectionDetailId(collectionId)
  }

  const statusColor = (status: number) => {
    if (status === 1) return 'green'
    if (status === 3) return 'blue'
    return 'red'
  }

  const statusText = (status: number) => {
    if (status === 1) return '在线'
    if (status === 3) return '拉流中'
    return '离线'
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 180px)' }}>
      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Toolbar */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <Space wrap>
            <Select
              style={{ width: 180 }}
              placeholder="选择库房"
              value={selectedRoomId}
              onChange={setSelectedRoomId}
              options={rooms.map((r) => ({ label: r.name, value: r.id }))}
            />
            <Button
              type={editMode ? 'primary' : 'default'}
              icon={<EditOutlined />}
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? '退出编辑' : '编辑布局'}
            </Button>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <HeatMapOutlined />
              <Switch
                checked={showHeatmap}
                onChange={setShowHeatmap}
                size="small"
              />
              <span style={{ fontSize: 12 }}>热力图</span>
            </span>
            {showHeatmap && (
              <Select
                size="small"
                style={{ width: 100 }}
                value={heatmapHours}
                onChange={setHeatmapHours}
                options={[
                  { label: '1小时', value: 1 },
                  { label: '6小时', value: 6 },
                  { label: '24小时', value: 24 },
                  { label: '7天', value: 168 },
                ]}
              />
            )}
            <Button icon={<ReloadOutlined />} size="small" onClick={loadLiveStatus}>
              刷新状态
            </Button>
          </Space>
        </Card>

        {/* Map or Editor */}
        <Card
          style={{ flex: 1, overflow: 'hidden' }}
          bodyStyle={{ height: '100%', padding: editMode ? 16 : 0 }}
          loading={loading}
        >
          {editMode ? (
            <RoomLayoutEditor
              roomWidth={roomWidth}
              roomHeight={roomHeight}
              layoutData={layoutData || { cameras: [], collections: [], zones: [], walls: [] }}
              cameras={cameras}
              collections={collections}
              onSave={handleSaveLayout}
            />
          ) : (
            <RoomMap
              width={roomWidth}
              height={roomHeight}
              layoutData={layoutData}
              heatmapPoints={heatmapPoints}
              showHeatmap={showHeatmap}
              onCameraClick={handleCameraClick}
              onCollectionClick={handleCollectionClick}
            />
          )}
        </Card>
      </div>

      {/* Right panel - Live Status */}
      <div style={{ width: 280, flexShrink: 0 }}>
        <Card title="库房实时状态" size="small" style={{ height: '100%', overflow: 'auto' }}>
          {liveStatus ? (
            <>
              <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
                <Descriptions.Item label="摄像头总数">{liveStatus.total_cameras}</Descriptions.Item>
                <Descriptions.Item label="在线数">
                  <Badge status="success" text={liveStatus.online_cameras} />
                </Descriptions.Item>
                <Descriptions.Item label="当前人数">
                  <Tag color="blue">{liveStatus.total_person_count}</Tag>
                </Descriptions.Item>
              </Descriptions>

              <h4 style={{ fontSize: 13, marginBottom: 8 }}>摄像头列表</h4>
              <List
                size="small"
                dataSource={liveStatus.cameras || []}
                renderItem={(cam: any) => (
                  <List.Item
                    style={{ padding: '6px 0', cursor: 'pointer' }}
                    onClick={() => setCameraPreviewId(cam.camera_id)}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>
                          <Badge color={statusColor(cam.status)} />
                          <span style={{ fontSize: 13 }}>{cam.camera_name}</span>
                        </span>
                        <Tag color={statusColor(cam.status)} style={{ fontSize: 11 }}>
                          {statusText(cam.status)}
                        </Tag>
                      </div>
                      {cam.latest_event && (
                        <div style={{ fontSize: 11, color: '#999', marginTop: 2, paddingLeft: 14 }}>
                          {cam.latest_event.event_type} - {cam.latest_event.event_time?.slice(11, 16)}
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>
              请选择库房查看实时状态
            </div>
          )}
        </Card>
      </div>

      {/* Camera Preview Modal */}
      <Modal
        title="摄像头实时预览"
        open={cameraPreviewId !== null}
        onCancel={() => setCameraPreviewId(null)}
        footer={null}
        width={640}
      >
        <div style={{ textAlign: 'center', padding: 20 }}>
          <VideoCameraOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <p style={{ marginTop: 12, color: '#666' }}>
            摄像头 ID: {cameraPreviewId}
          </p>
          <p style={{ color: '#999', fontSize: 12 }}>
            实时预览功能需要 RTSP 流支持
          </p>
        </div>
      </Modal>

      {/* Collection Detail Modal */}
      <Modal
        title="藏品详情"
        open={collectionDetailId !== null}
        onCancel={() => setCollectionDetailId(null)}
        footer={null}
      >
        <Descriptions column={1}>
          <Descriptions.Item label="藏品ID">{collectionDetailId}</Descriptions.Item>
        </Descriptions>
        <p style={{ color: '#999', fontSize: 12 }}>
          点击藏品管理页面查看完整信息
        </p>
      </Modal>
    </div>
  )
}
