import { useRef, useEffect, useState, useCallback } from 'react'

interface CameraItem {
  camera_id: number
  x: number
  y: number
  angle: number
  fov: number
  name?: string
  status?: number
}

interface CollectionItem {
  collection_id: number
  x: number
  y: number
  width: number
  height: number
  name?: string
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

interface HeatmapPoint {
  camera_id: number
  x: number
  y: number
  count: number
}

interface LayoutData {
  cameras: CameraItem[]
  collections: CollectionItem[]
  zones: ZoneItem[]
  walls: WallItem[]
}

interface RoomMapProps {
  width: number
  height: number
  layoutData: LayoutData | null
  heatmapPoints?: HeatmapPoint[]
  showHeatmap?: boolean
  onCameraClick?: (cameraId: number) => void
  onCollectionClick?: (collectionId: number) => void
}

export default function RoomMap({
  width,
  height,
  layoutData,
  heatmapPoints = [],
  showHeatmap = false,
  onCameraClick,
  onCollectionClick,
}: RoomMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [canvasSize, setCanvasSize] = useState({ w: 800, h: 600 })

  // Calculate scale to fit room in canvas
  const getScale = useCallback(() => {
    if (!width || !height) return 1
    const scaleX = canvasSize.w / width
    const scaleY = canvasSize.h / height
    return Math.min(scaleX, scaleY) * 0.9
  }, [width, height, canvasSize])

  // Convert room coords to canvas coords
  const toCanvas = useCallback((rx: number, ry: number) => {
    const baseScale = getScale()
    const offsetX = (canvasSize.w - width * baseScale) / 2
    const offsetY = (canvasSize.h - height * baseScale) / 2
    return {
      x: (rx * baseScale + offsetX) * transform.scale + transform.x,
      y: (ry * baseScale + offsetY) * transform.scale + transform.y,
    }
  }, [getScale, width, height, canvasSize, transform])

  // Convert canvas coords to room coords
  const toRoom = useCallback((cx: number, cy: number) => {
    const baseScale = getScale()
    const offsetX = (canvasSize.w - width * baseScale) / 2
    const offsetY = (canvasSize.h - height * baseScale) / 2
    return {
      x: ((cx - transform.x) / transform.scale - offsetX) / baseScale,
      y: ((cy - transform.y) / transform.scale - offsetY) / baseScale,
    }
  }, [getScale, width, height, canvasSize, transform])

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

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !layoutData) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = canvasSize.w
    canvas.height = canvasSize.h

    // Clear
    ctx.clearRect(0, 0, canvasSize.w, canvasSize.h)
    ctx.fillStyle = '#f8f9fa'
    ctx.fillRect(0, 0, canvasSize.w, canvasSize.h)

    const baseScale = getScale()
    const offsetX = (canvasSize.w - width * baseScale) / 2
    const offsetY = (canvasSize.h - height * baseScale) / 2

    ctx.save()
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.scale, transform.scale)

    // Draw room background
    ctx.fillStyle = '#ffffff'
    ctx.strokeStyle = '#d9d9d9'
    ctx.lineWidth = 2
    ctx.fillRect(offsetX, offsetY, width * baseScale, height * baseScale)
    ctx.strokeRect(offsetX, offsetY, width * baseScale, height * baseScale)

    // Draw zones
    if (layoutData.zones) {
      for (const zone of layoutData.zones) {
        ctx.beginPath()
        const zoneColors: Record<string, string> = {
          entrance: 'rgba(82, 196, 26, 0.15)',
          storage: 'rgba(24, 144, 255, 0.15)',
          display: 'rgba(250, 173, 20, 0.15)',
          restricted: 'rgba(255, 77, 79, 0.15)',
        }
        ctx.fillStyle = zoneColors[zone.type] || 'rgba(114, 46, 209, 0.1)'
        const points = zone.points
        if (points.length > 0) {
          const first = { x: points[0][0] * baseScale + offsetX, y: points[0][1] * baseScale + offsetY }
          ctx.moveTo(first.x, first.y)
          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0] * baseScale + offsetX, points[i][1] * baseScale + offsetY)
          }
          ctx.closePath()
          ctx.fill()
          ctx.strokeStyle = 'rgba(0,0,0,0.2)'
          ctx.lineWidth = 1
          ctx.stroke()

          // Zone label
          const cx = points.reduce((s, p) => s + p[0], 0) / points.length * baseScale + offsetX
          const cy = points.reduce((s, p) => s + p[1], 0) / points.length * baseScale + offsetY
          ctx.fillStyle = '#666'
          ctx.font = `${11 * Math.max(1, baseScale)}px sans-serif`
          ctx.textAlign = 'center'
          ctx.fillText(zone.name, cx, cy)
        }
      }
    }

    // Draw walls
    if (layoutData.walls) {
      ctx.strokeStyle = '#595959'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      for (const wall of layoutData.walls) {
        ctx.beginPath()
        ctx.moveTo(wall.x1 * baseScale + offsetX, wall.y1 * baseScale + offsetY)
        ctx.lineTo(wall.x2 * baseScale + offsetX, wall.y2 * baseScale + offsetY)
        ctx.stroke()
      }
    }

    // Draw heatmap
    if (showHeatmap && heatmapPoints.length > 0) {
      const maxCount = Math.max(...heatmapPoints.map((p) => p.count))
      for (const point of heatmapPoints) {
        const px = point.x * baseScale + offsetX
        const py = point.y * baseScale + offsetY
        const intensity = point.count / maxCount
        const radius = 30 + intensity * 50

        const gradient = ctx.createRadialGradient(px, py, 0, px, py, radius)
        gradient.addColorStop(0, `rgba(255, 0, 0, ${0.4 * intensity})`)
        gradient.addColorStop(0.5, `rgba(255, 100, 0, ${0.2 * intensity})`)
        gradient.addColorStop(1, 'rgba(255, 200, 0, 0)')
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(px, py, radius, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    // Draw collections
    if (layoutData.collections) {
      for (const col of layoutData.collections) {
        const cx = col.x * baseScale + offsetX
        const cy = col.y * baseScale + offsetY
        const cw = col.width * baseScale
        const ch = col.height * baseScale

        ctx.fillStyle = 'rgba(250, 173, 20, 0.3)'
        ctx.strokeStyle = '#faad14'
        ctx.lineWidth = 1.5
        ctx.fillRect(cx - cw / 2, cy - ch / 2, cw, ch)
        ctx.strokeRect(cx - cw / 2, cy - ch / 2, cw, ch)

        // Label
        if (col.name) {
          ctx.fillStyle = '#8c6d1f'
          ctx.font = `${10 * Math.max(1, baseScale)}px sans-serif`
          ctx.textAlign = 'center'
          ctx.fillText(col.name, cx, cy + ch / 2 + 12)
        }
      }
    }

    // Draw cameras
    if (layoutData.cameras) {
      for (const cam of layoutData.cameras) {
        const cx = cam.x * baseScale + offsetX
        const cy = cam.y * baseScale + offsetY

        // FOV cone
        const fovRad = (cam.fov * Math.PI) / 180
        const angleRad = ((cam.angle - 90) * Math.PI) / 180
        const coneLength = 60 * baseScale

        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.arc(cx, cy, coneLength, angleRad - fovRad / 2, angleRad + fovRad / 2)
        ctx.closePath()
        ctx.fillStyle = 'rgba(24, 144, 255, 0.12)'
        ctx.strokeStyle = 'rgba(24, 144, 255, 0.4)'
        ctx.lineWidth = 1
        ctx.fill()
        ctx.stroke()

        // Camera icon (circle)
        ctx.beginPath()
        ctx.arc(cx, cy, 8, 0, Math.PI * 2)
        const isOnline = cam.status === 1 || cam.status === undefined
        ctx.fillStyle = isOnline ? '#1890ff' : '#ff4d4f'
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.stroke()

        // Camera label
        if (cam.name) {
          ctx.fillStyle = '#1890ff'
          ctx.font = `${10 * Math.max(1, baseScale)}px sans-serif`
          ctx.textAlign = 'center'
          ctx.fillText(cam.name, cx, cy - 14)
        }
      }
    }

    ctx.restore()
  }, [layoutData, canvasSize, transform, showHeatmap, heatmapPoints, width, height, getScale])

  // Mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const newScale = Math.max(0.3, Math.min(5, transform.scale * delta))
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    setTransform({
      scale: newScale,
      x: mx - (mx - transform.x) * (newScale / transform.scale),
      y: my - (my - transform.y) * (newScale / transform.scale),
    })
  }, [transform])

  // Mouse drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y })
    }
  }, [transform])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setTransform((t) => ({ ...t, x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }))
    }
  }, [isDragging, dragStart])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  // Click detection
  const handleClick = useCallback((e: React.MouseEvent) => {
    if (!layoutData) return
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    const roomCoords = toRoom(cx, cy)

    // Check cameras
    for (const cam of layoutData.cameras || []) {
      const dist = Math.sqrt((roomCoords.x - cam.x) ** 2 + (roomCoords.y - cam.y) ** 2)
      if (dist < 15) {
        onCameraClick?.(cam.camera_id)
        return
      }
    }

    // Check collections
    for (const col of layoutData.collections || []) {
      if (
        roomCoords.x >= col.x - col.width / 2 &&
        roomCoords.x <= col.x + col.width / 2 &&
        roomCoords.y >= col.y - col.height / 2 &&
        roomCoords.y <= col.y + col.height / 2
      ) {
        onCollectionClick?.(col.collection_id)
        return
      }
    }
  }, [layoutData, toRoom, onCameraClick, onCollectionClick])

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', minHeight: 500, position: 'relative', overflow: 'hidden' }}
    >
      <canvas
        ref={canvasRef}
        style={{ cursor: isDragging ? 'grabbing' : 'grab', display: 'block', width: '100%', height: '100%' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
      />
      {/* Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          left: 12,
          background: 'rgba(255,255,255,0.92)',
          borderRadius: 6,
          padding: '8px 12px',
          fontSize: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#1890ff', marginRight: 4 }} />摄像头</span>
          <span><span style={{ display: 'inline-block', width: 10, height: 10, background: 'rgba(250,173,20,0.5)', border: '1px solid #faad14', marginRight: 4 }} />藏品</span>
          <span><span style={{ display: 'inline-block', width: 20, height: 3, background: '#595959', marginRight: 4 }} />墙壁</span>
          {showHeatmap && <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: 'rgba(255,0,0,0.4)', marginRight: 4 }} />热力图</span>}
        </div>
      </div>
    </div>
  )
}
