import { useRef, useEffect } from 'react'
import { wanderMapColors } from '../theme'

interface TrajectoryPoint {
  x: number
  y: number
  t: number
}

interface TrajectoryData {
  track_id: string
  points: TrajectoryPoint[]
  duration: number
  total_distance: number
  average_speed: number
  movement_pattern: string
}

interface TrajectoryViewProps {
  data: TrajectoryData
  width?: number
  height?: number
}

const PATTERN_LABELS: Record<string, string> = {
  loiter: '徘徊',
  linear: '直线移动',
  back_and_forth: '往返',
}

export default function TrajectoryView({ data, width = 600, height = 400 }: TrajectoryViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !data?.points?.length) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const points = data.points
    if (points.length < 2) return

    // 计算坐标范围并归一化
    const xs = points.map(p => p.x)
    const ys = points.map(p => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)

    const padding = 40
    const drawWidth = width - padding * 2
    const drawHeight = height - padding * 2

    const rangeX = maxX - minX || 1
    const rangeY = maxY - minY || 1

    const scaleX = (x: number) => padding + ((x - minX) / rangeX) * drawWidth
    const scaleY = (y: number) => padding + ((y - minY) / rangeY) * drawHeight

    // 清空画布
    ctx.clearRect(0, 0, width, height)

    // 绘制背景网格
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const x = padding + (drawWidth / 5) * i
      const y = padding + (drawHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(x, padding)
      ctx.lineTo(x, height - padding)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }

    // 绘制轨迹线（带时间渐变色）
    const ts = points.map(p => p.t)
    const minT = Math.min(...ts)
    const maxT = Math.max(...ts)
    const rangeT = maxT - minT || 1

    for (let i = 1; i < points.length; i++) {
      const progress = (points[i].t - minT) / rangeT
      // 从蓝色渐变到红色
      const r = Math.round(progress * 239)
      const g = Math.round((1 - progress) * 100 + 50)
      const b = Math.round((1 - progress) * 233)

      ctx.beginPath()
      ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.moveTo(scaleX(points[i - 1].x), scaleY(points[i - 1].y))
      ctx.lineTo(scaleX(points[i].x), scaleY(points[i].y))
      ctx.stroke()
    }

    // 标注起点（绿色圆点）
    const startX = scaleX(points[0].x)
    const startY = scaleY(points[0].y)
    ctx.beginPath()
    ctx.arc(startX, startY, 8, 0, Math.PI * 2)
    ctx.fillStyle = wanderMapColors.success
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 10px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('起', startX, startY)

    // 标注终点（红色圆点）
    const endX = scaleX(points[points.length - 1].x)
    const endY = scaleY(points[points.length - 1].y)
    ctx.beginPath()
    ctx.arc(endX, endY, 8, 0, Math.PI * 2)
    ctx.fillStyle = wanderMapColors.error
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 10px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('终', endX, endY)

    // 标注停留点（速度为0或极低的点）
    for (let i = 1; i < points.length - 1; i++) {
      const dx = points[i].x - points[i - 1].x
      const dy = points[i].y - points[i - 1].y
      const dt = points[i].t - points[i - 1].t
      if (dt > 0) {
        const speed = Math.sqrt(dx * dx + dy * dy) / dt
        if (speed < 1) {
          const px = scaleX(points[i].x)
          const py = scaleY(points[i].y)
          ctx.beginPath()
          ctx.arc(px, py, 5, 0, Math.PI * 2)
          ctx.fillStyle = wanderMapColors.warning
          ctx.fill()
        }
      }
    }
  }, [data, width, height])

  if (!data?.points?.length) {
    return <div style={{ color: wanderMapColors.textSecondary, padding: 20 }}>无轨迹数据</div>
  }

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{
          border: '1px solid #f0f0f0',
          borderRadius: 8,
          display: 'block',
          margin: '0 auto',
        }}
      />
      <div style={{ display: 'flex', gap: 24, justifyContent: 'center', marginTop: 12, fontSize: 12, color: wanderMapColors.textSecondary }}>
        <span>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: wanderMapColors.success, marginRight: 4 }} />
          起点
        </span>
        <span>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: wanderMapColors.error, marginRight: 4 }} />
          终点
        </span>
        <span>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: wanderMapColors.warning, marginRight: 4 }} />
          停留点
        </span>
        <span>移动模式: {PATTERN_LABELS[data.movement_pattern] || data.movement_pattern}</span>
        <span>持续: {data.duration?.toFixed(0)}s</span>
        <span>距离: {data.total_distance?.toFixed(0)}px</span>
      </div>
    </div>
  )
}
