import { useEffect, useRef, useState, useCallback } from 'react'
import { Badge, Button, Space, Spin, Typography } from 'antd'
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  CloseOutlined,
  EyeOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface Box {
  x1: number
  y1: number
  x2: number
  y2: number
  confidence: number
  label: string
}

interface DetectionMessage {
  timestamp: string
  person_count: number
  boxes: Box[]
  frame_url: string
  type?: string
}

interface LivePreviewProps {
  cameraId: number
  cameraName?: string
  onClose?: () => void
}

export default function LivePreview({ cameraId, cameraName, onClose }: LivePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const [connected, setConnected] = useState(false)
  const [personCount, setPersonCount] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  // 当前检测框数据
  const boxesRef = useRef<Box[]>([])

  const drawOverlay = useCallback(() => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img || !img.naturalWidth) return

    canvas.width = img.clientWidth
    canvas.height = img.clientHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const scaleX = img.clientWidth / img.naturalWidth
    const scaleY = img.clientHeight / img.naturalHeight

    boxesRef.current.forEach((box) => {
      const x = box.x1 * scaleX
      const y = box.y1 * scaleY
      const w = (box.x2 - box.x1) * scaleX
      const h = (box.y2 - box.y1) * scaleY

      // 绘制检测框
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 2
      ctx.strokeRect(x, y, w, h)

      // 绘制标签背景
      const label = `${box.label} ${(box.confidence * 100).toFixed(0)}%`
      ctx.font = '12px Arial'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = 'rgba(0, 255, 0, 0.7)'
      ctx.fillRect(x, y - 18, textWidth + 8, 18)

      // 绘制标签文字
      ctx.fillStyle = '#000'
      ctx.fillText(label, x + 4, y - 4)
    })
  }, [])

  // 建立 WebSocket 连接
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/live/${cameraId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setLoading(false)
    }

    ws.onmessage = (event) => {
      try {
        const data: DetectionMessage = JSON.parse(event.data)
        if (data.type === 'heartbeat') return

        setPersonCount(data.person_count)
        setLastUpdate(new Date(data.timestamp).toLocaleTimeString())
        boxesRef.current = data.boxes || []

        // 刷新截图
        if (imgRef.current && data.frame_url) {
          imgRef.current.src = `${data.frame_url}?t=${Date.now()}`
        }
      } catch (e) {
        console.error('解析 WebSocket 消息失败:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    ws.onerror = () => {
      setConnected(false)
      setLoading(false)
    }

    return () => {
      ws.close()
    }
  }, [cameraId])

  // 图片加载后绘制叠加层
  const handleImageLoad = useCallback(() => {
    setLoading(false)
    drawOverlay()
  }, [drawOverlay])

  // 全屏切换
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }, [])

  // 监听全屏变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // 窗口大小变化时重绘
  useEffect(() => {
    const handleResize = () => drawOverlay()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [drawOverlay])

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        background: '#000',
        borderRadius: 4,
        overflow: 'hidden',
        width: '100%',
        height: isFullscreen ? '100vh' : 480,
      }}
    >
      {/* 顶部状态栏 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: 'rgba(0,0,0,0.6)',
        }}
      >
        <Space>
          <Badge status={connected ? 'success' : 'error'} />
          <Text style={{ color: '#fff', fontSize: 14 }}>
            {cameraName || `摄像头 ${cameraId}`}
          </Text>
          <Text style={{ color: '#aaa', fontSize: 12 }}>
            {connected ? '实时预览中' : '未连接'}
          </Text>
        </Space>
        <Space>
          <Button
            type="text"
            size="small"
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={toggleFullscreen}
            style={{ color: '#fff' }}
          />
          {onClose && (
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={onClose}
              style={{ color: '#fff' }}
            />
          )}
        </Space>
      </div>

      {/* 视频画面 */}
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        {loading && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 5,
          }}>
            <Spin tip="连接中..." size="large" />
          </div>
        )}
        <img
          ref={imgRef}
          src={`/api/v1/live/${cameraId}/snapshot?t=${Date.now()}`}
          onLoad={handleImageLoad}
          onError={() => setLoading(false)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            display: 'block',
          }}
          alt="实时预览"
        />
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
          }}
        />
      </div>

      {/* 底部信息栏 */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 12px',
          background: 'rgba(0,0,0,0.6)',
        }}
      >
        <Space>
          <EyeOutlined style={{ color: '#00ff00' }} />
          <Text style={{ color: '#fff', fontSize: 13 }}>
            实时人数: <span style={{ color: '#00ff00', fontWeight: 'bold' }}>{personCount}</span>
          </Text>
        </Space>
        <Text style={{ color: '#aaa', fontSize: 12 }}>
          {lastUpdate && `更新: ${lastUpdate}`}
        </Text>
      </div>
    </div>
  )
}
