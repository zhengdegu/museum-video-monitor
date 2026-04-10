import { useEffect, useRef, useState } from 'react'

interface VideoPlayerProps {
  src: string
  startTime?: number
  poster?: string
}

export default function VideoPlayer({ src, startTime, poster }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [currentTime, setCurrentTime] = useState(0)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    const onLoaded = () => {
      if (startTime) video.currentTime = startTime
    }
    video.addEventListener('loadedmetadata', onLoaded)
    return () => video.removeEventListener('loadedmetadata', onLoaded)
  }, [src, startTime])

  const fmt = (s: number) => {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = Math.floor(s % 60)
    return h > 0
      ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
      : `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  return (
    <div style={{ position: 'relative', background: '#000', borderRadius: 4, overflow: 'hidden' }}>
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        controls
        style={{ width: '100%', display: 'block' }}
        onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime ?? 0)}
      />
      <div style={{
        position: 'absolute', bottom: 40, right: 8,
        background: 'rgba(0,0,0,0.55)', color: '#fff',
        fontSize: 12, padding: '2px 6px', borderRadius: 3, pointerEvents: 'none',
      }}>
        {fmt(currentTime)}
      </div>
    </div>
  )
}
