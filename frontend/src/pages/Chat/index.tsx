import { useState, useRef, useEffect } from 'react'
import { Input, Button, List, Card, Spin } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { sendChat } from '../../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | undefined>()
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)
    try {
      const res: any = await sendChat({ message: userMsg, session_id: sessionId })
      if (res.code === 200) {
        setMessages((prev) => [...prev, { role: 'assistant', content: res.data.answer, sources: res.data.sources }])
        if (res.data.session_id) setSessionId(res.data.session_id)
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: `错误: ${res.message}` }])
      }
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: '网络错误，请重试' }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
      <h2 style={{ marginBottom: 16 }}>智能交互</h2>
      <Card style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }} styles={{ body: { flex: 1, overflow: 'auto', padding: 16 } }}>
        <div ref={listRef} style={{ flex: 1, overflow: 'auto' }}>
          <List
            dataSource={messages}
            renderItem={(msg) => (
              <List.Item style={{ justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', border: 'none', padding: '4px 0' }}>
                <div style={{
                  maxWidth: '70%', padding: '8px 12px', borderRadius: 8,
                  background: msg.role === 'user' ? '#1677ff' : '#f0f0f0',
                  color: msg.role === 'user' ? '#fff' : '#000',
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.content}
                </div>
              </List.Item>
            )}
          />
          {loading && <div style={{ textAlign: 'center', padding: 8 }}><Spin size="small" /> 思考中...</div>}
        </div>
      </Card>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={handleSend}
          placeholder="输入问题，如：昨天3号库房有没有人进出？"
          size="large"
        />
        <Button type="primary" icon={<SendOutlined />} size="large" onClick={handleSend} loading={loading}>发送</Button>
      </div>
    </div>
  )
}
