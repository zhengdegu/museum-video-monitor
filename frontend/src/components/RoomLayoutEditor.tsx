import { useRef, useState, useCallback, useEffect } from 'react'
import { Button, Select, Space, message, Slider } from 'antd'
import {
  SaveOutlined, DeleteOutlined, DragOutlined,
} from '@ant-design/icons'

interface CameraItem {
  camera_id: number
  x: number
  y: number
  angle: number
  fov: number
}

interface CollectionItem {
  collection_id: number
  x: number
  y: number
  width: number
  height: number
}

interface ZoneItem {
  name: string
  points: number[][]
  type: string
}

interface WallItem {
  x1: number
  y1: number
  x2: number
  y2: number
}

interface LayoutData {
  cameras: CameraItem[]
  collections: CollectionItem[]
  zones: ZoneItem[]
  walls: WallItem[]
}

interface RoomLayoutEditorProps {
  roomWidth: number
  roomHeight: number
  layoutData: LayoutData
  cameras: { id: number; name: string }[]
  collections: { id: number; name: string }[]
  onSave: (data: LayoutData) => void
}

type Tool = 'select' | 'camera' | 'collection' | 'zone' | 'wall'

export default function RoomLayoutEditor({
  roomWidth,
  roomHeight,
  layoutData: initialData,
  cameras,
  collections,
  onSave,
}: RoomLayoutEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [layoutData, setLayoutData] = useState<LayoutData>(initialData)
  const [tool, setTool] = useState<Tool>('select')
  const [selectedItem, setSelectedItem] = useState<{ type: string; index: number } | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [canvasSize, setCanvasSize] = useState({ w: 800, h: 600 })
  const [placingCameraId, setPlacingCameraId] = useState<number | null>(null)
  const [placingCollectionId, setPlacingCollectionId] = useState<number | null>(null)

  // Calculate scale
  const getScale = useCallback(() => {
    if (!roomWidth || !roomHeight) return 1
    const scaleX = canvasSize.w / roomWidth
    const scaleY = canvasSize.h / roomHeight
    return Math.min(scaleX, scaleY) * 0.9
  }, [roomWidth, roomHeight, canvasSize])

  const getOffset = useCallback(() => {
    const baseScale = getScale()
    return {
      x: (canvasSize.w - roomWidth * baseScale) / 2,
      y: (canvasSize.h - roomHeight * baseScale) / 2,
    }
  }, [getScale, roomWidth, roomHeight, canvasSize])

  // Convert canvas coords to room coords
  const toRoom = useCallback((cx: number, cy: number) => {
    const baseScale = getScale()
    const offset = getOffset()
    return {
      x: Math.round((cx - offset.x) / baseScale),
      y: Math.round((cy - offset.y) / baseScale),
    }
  }, [getScale, getOffset])

  // Convert room coords to canvas coords
  const toCanvas = useCallback((rx: number, ry: number) => {
    const baseScale = getScale()
    const offset = getOffset()
    return {
      x: rx * baseScale + offset.x,
      y: ry * baseScale + offset.y,
    }
  }, [getScale, getOffset])

  // Resize observer
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setCanvasSize({ w: entry.contentRect.width, h: entry.contentRect.height })
      }
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  // Draw
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = canvasSize.w
    canvas.height = canvasSize.h
    ctx.clearRect(0, 0, canvasSize.w, canvasSize.h)

    const baseScale = getScale()
    const offset = getOffset()

    // Room background
    ctx.fillStyle = '#fafafa'
    ctx.strokeStyle = '#d9d9d9'
    ctx.lineWidth = 2
    ctx.fillRect(offset.x, offset.y, roomWidth * baseScale, roomHeight * baseScale)
    ctx.strokeRect(offset.x, offset.y, roomWidth * baseScale, roomHeight * baseScale)

    // Grid
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 0.5
    const gridStep = 50
    for (let gx = 0; gx <= roomWidth; gx += gridStep) {
      const cx = gx * baseScale + offset.x
      ctx.beginPath()
      ctx.moveTo(cx, offset.y)
      ctx.lineTo(cx, offset.y + roomHeight * baseScale)
      ctx.stroke()
    }
    for (let gy = 0; gy <= roomHeight; gy += gridStep) {
      const cy = gy * baseScale + offset.y
      ctx.beginPath()
      ctx.moveTo(offset.x, cy)
      ctx.lineTo(offset.x + roomWidth * baseScale, cy)
      ctx.stroke()
    }

    // Walls
    ctx.strokeStyle = '#595959'
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    for (let i = 0; i < layoutData.walls.length; i++) {
      const wall = layoutData.walls[i]
      const isSelected = selectedItem?.type === 'wall' && selectedItem.index === i
      ctx.strokeStyle = isSelected ? '#1890ff' : '#595959'
      ctx.beginPath()
      ctx.moveTo(wall.x1 * baseScale + offset.x, wall.y1 * baseScale + offset.y)
      ctx.lineTo(wall.x2 * baseScale + offset.x, wall.y2 * baseScale + offset.y)
      ctx.stroke()
    }

    // Zones
    for (let i = 0; i < layoutData.zones.length; i++) {
      const zone = layoutData.zones[i]
      const isSelected = selectedItem?.type === 'zone' && selectedItem.index === i
      ctx.beginPath()
      ctx.fillStyle = isSelected ? 'rgba(24, 144, 255, 0.2)' : 'rgba(114, 46, 209, 0.1)'
      if (zone.points.length > 0) {
        ctx.moveTo(zone.points[0][0] * baseScale + offset.x, zone.points[0][1] * baseScale + offset.y)
        for (let j = 1; j < zone.points.length; j++) {
          ctx.lineTo(zone.points[j][0] * baseScale + offset.x, zone.points[j][1] * baseScale + offset.y)
        }
        ctx.closePath()
        ctx.fill()
        ctx.strokeStyle = isSelected ? '#1890ff' : 'rgba(0,0,0,0.3)'
        ctx.lineWidth = 1
        ctx.stroke()
      }
    }

    // Collections
    for (let i = 0; i < layoutData.collections.length; i++) {
      const col = layoutData.collections[i]
      const isSelected = selectedItem?.type === 'collection' && selectedItem.index === i
      const cx = col.x * baseScale + offset.x
      const cy = col.y * baseScale + offset.y
      const cw = col.width * baseScale
      const ch = col.height * baseScale
      ctx.fillStyle = isSelected ? 'rgba(24, 144, 255, 0.3)' : 'rgba(250, 173, 20, 0.3)'
      ctx.strokeStyle = isSelected ? '#1890ff' : '#faad14'
      ctx.lineWidth = isSelected ? 2 : 1.5
      ctx.fillRect(cx - cw / 2, cy - ch / 2, cw, ch)
      ctx.strokeRect(cx - cw / 2, cy - ch / 2, cw, ch)
    }

    // Cameras
    for (let i = 0; i < layoutData.cameras.length; i++) {
      const cam = layoutData.cameras[i]
      const isSelected = selectedItem?.type === 'camera' && selectedItem.index === i
      const cx = cam.x * baseScale + offset.x
      const cy = cam.y * baseScale + offset.y

      // FOV
      const fovRad = (cam.fov * Math.PI) / 180
      const angleRad = ((cam.angle - 90) * Math.PI) / 180
      const coneLength = 60 * baseScale
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, coneLength, angleRad - fovRad / 2, angleRad + fovRad / 2)
      ctx.closePath()
      ctx.fillStyle = isSelected ? 'rgba(24, 144, 255, 0.2)' : 'rgba(24, 144, 255, 0.1)'
      ctx.fill()

      // Icon
      ctx.beginPath()
      ctx.arc(cx, cy, isSelected ? 10 : 8, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? '#096dd9' : '#1890ff'
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
    }
  }, [layoutData, canvasSize, selectedItem, roomWidth, roomHeight, getScale, getOffset])

  // Handle canvas click
  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    const room = toRoom(cx, cy)

    if (tool === 'camera' && placingCameraId) {
      // Place camera
      const existing = layoutData.cameras.findIndex((c) => c.camera_id === placingCameraId)
      const newCameras = [...layoutData.cameras]
      const camData = { camera_id: placingCameraId, x: room.x, y: room.y, angle: 90, fov: 120 }
      if (existing >= 0) {
        newCameras[existing] = camData
      } else {
        newCameras.push(camData)
      }
      setLayoutData({ ...layoutData, cameras: newCameras })
      setPlacingCameraId(null)
      setTool('select')
      message.success('摄像头已放置')
      return
    }

    if (tool === 'collection' && placingCollectionId) {
      const existing = layoutData.collections.findIndex((c) => c.collection_id === placingCollectionId)
      const newCollections = [...layoutData.collections]
      const colData = { collection_id: placingCollectionId, x: room.x, y: room.y, width: 30, height: 30 }
      if (existing >= 0) {
        newCollections[existing] = colData
      } else {
        newCollections.push(colData)
      }
      setLayoutData({ ...layoutData, collections: newCollections })
      setPlacingCollectionId(null)
      setTool('select')
      message.success('藏品已放置')
      return
    }

    if (tool === 'select') {
      // Hit test
      const baseScale = getScale()
      for (let i = 0; i < layoutData.cameras.length; i++) {
        const cam = layoutData.cameras[i]
        const dist = Math.sqrt((room.x - cam.x) ** 2 + (room.y - cam.y) ** 2)
        if (dist < 15) {
          setSelectedItem({ type: 'camera', index: i })
          return
        }
      }
      for (let i = 0; i < layoutData.collections.length; i++) {
        const col = layoutData.collections[i]
        if (Math.abs(room.x - col.x) < col.width / 2 + 5 && Math.abs(room.y - col.y) < col.height / 2 + 5) {
          setSelectedItem({ type: 'collection', index: i })
          return
        }
      }
      setSelectedItem(null)
    }
  }, [tool, placingCameraId, placingCollectionId, layoutData, toRoom, getScale])

  // Handle drag for moving items
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (tool === 'select' && selectedItem) {
      setIsDragging(true)
    }
  }, [tool, selectedItem])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !selectedItem) return
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const room = toRoom(e.clientX - rect.left, e.clientY - rect.top)

    if (selectedItem.type === 'camera') {
      const newCameras = [...layoutData.cameras]
      newCameras[selectedItem.index] = { ...newCameras[selectedItem.index], x: room.x, y: room.y }
      setLayoutData({ ...layoutData, cameras: newCameras })
    } else if (selectedItem.type === 'collection') {
      const newCollections = [...layoutData.collections]
      newCollections[selectedItem.index] = { ...newCollections[selectedItem.index], x: room.x, y: room.y }
      setLayoutData({ ...layoutData, collections: newCollections })
    }
  }, [isDragging, selectedItem, layoutData, toRoom])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  // Delete selected
  const handleDelete = useCallback(() => {
    if (!selectedItem) return
    if (selectedItem.type === 'camera') {
      const newCameras = layoutData.cameras.filter((_, i) => i !== selectedItem.index)
      setLayoutData({ ...layoutData, cameras: newCameras })
    } else if (selectedItem.type === 'collection') {
      const newCollections = layoutData.collections.filter((_, i) => i !== selectedItem.index)
      setLayoutData({ ...layoutData, collections: newCollections })
    }
    setSelectedItem(null)
  }, [selectedItem, layoutData])

  // Update camera angle/fov
  const updateCameraAngle = (angle: number) => {
    if (!selectedItem || selectedItem.type !== 'camera') return
    const newCameras = [...layoutData.cameras]
    newCameras[selectedItem.index] = { ...newCameras[selectedItem.index], angle }
    setLayoutData({ ...layoutData, cameras: newCameras })
  }

  const updateCameraFov = (fov: number) => {
    if (!selectedItem || selectedItem.type !== 'camera') return
    const newCameras = [...layoutData.cameras]
    newCameras[selectedItem.index] = { ...newCameras[selectedItem.index], fov }
    setLayoutData({ ...layoutData, cameras: newCameras })
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* Toolbar */}
      <div style={{ width: 240, flexShrink: 0 }}>
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>工具</h4>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              block
              type={tool === 'select' ? 'primary' : 'default'}
              icon={<DragOutlined />}
              onClick={() => setTool('select')}
            >
              选择/移动
            </Button>
          </Space>
        </div>

        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>放置摄像头</h4>
          <Select
            style={{ width: '100%' }}
            placeholder="选择摄像头"
            value={placingCameraId}
            onChange={(v) => { setPlacingCameraId(v); setTool('camera') }}
            options={cameras.map((c) => ({ label: c.name, value: c.id }))}
            allowClear
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>放置藏品</h4>
          <Select
            style={{ width: '100%' }}
            placeholder="选择藏品"
            value={placingCollectionId}
            onChange={(v) => { setPlacingCollectionId(v); setTool('collection') }}
            options={collections.map((c) => ({ label: c.name, value: c.id }))}
            allowClear
            showSearch
            filterOption={(input, option) => (option?.label as string || '').includes(input)}
          />
        </div>

        {/* Selected item properties */}
        {selectedItem?.type === 'camera' && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ marginBottom: 8 }}>摄像头属性</h4>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12 }}>角度: {layoutData.cameras[selectedItem.index]?.angle}°</span>
              <Slider
                min={0}
                max={360}
                value={layoutData.cameras[selectedItem.index]?.angle}
                onChange={updateCameraAngle}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12 }}>视角范围: {layoutData.cameras[selectedItem.index]?.fov}°</span>
              <Slider
                min={30}
                max={180}
                value={layoutData.cameras[selectedItem.index]?.fov}
                onChange={updateCameraFov}
              />
            </div>
          </div>
        )}

        <Space direction="vertical" style={{ width: '100%' }}>
          {selectedItem && (
            <Button block danger icon={<DeleteOutlined />} onClick={handleDelete}>
              删除选中
            </Button>
          )}
          <Button block type="primary" icon={<SaveOutlined />} onClick={() => onSave(layoutData)}>
            保存布局
          </Button>
        </Space>
      </div>

      {/* Canvas */}
      <div ref={containerRef} style={{ flex: 1, minHeight: 500, position: 'relative', border: '1px solid #d9d9d9', borderRadius: 6 }}>
        <canvas
          ref={canvasRef}
          style={{ cursor: tool === 'select' ? (isDragging ? 'grabbing' : 'default') : 'crosshair', display: 'block', width: '100%', height: '100%' }}
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
        {tool !== 'select' && (
          <div style={{ position: 'absolute', top: 8, left: 8, background: '#1890ff', color: '#fff', padding: '4px 12px', borderRadius: 4, fontSize: 12 }}>
            点击地图放置{tool === 'camera' ? '摄像头' : '藏品'}
          </div>
        )}
      </div>
    </div>
  )
}
