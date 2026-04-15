import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { login, getMe } from '../../services/api'
import { useAuthStore } from '../../store/auth'
import { wanderMapColors } from '../../theme'

export default function Login() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const res: any = await login(values)
      if (res.code === 200) {
        setToken(res.data.access_token)
        const me: any = await getMe()
        if (me.code === 200) setUser(me.data)
        message.success('登录成功')
        navigate('/')
      } else {
        message.error(res.message || '登录失败')
      }
    } catch {
      message.error('网络错误')
    }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Left decorative panel */}
      <div
        style={{
          flex: 1,
          background: `linear-gradient(135deg, ${wanderMapColors.primary} 0%, ${wanderMapColors.siderDarkBg} 60%, #064E3B 100%)`,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 60,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative circles */}
        <div
          style={{
            position: 'absolute',
            width: 400,
            height: 400,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.04)',
            top: -100,
            left: -100,
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: 300,
            height: 300,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.03)',
            bottom: -50,
            right: -50,
          }}
        />

        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 420 }}>
          <div style={{ fontSize: 56, marginBottom: 24 }}>🏛</div>
          <h1 style={{ color: '#fff', fontSize: 32, fontWeight: 700, marginBottom: 16, lineHeight: 1.3 }}>
            博物馆视频智能监控分析平台
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 16, lineHeight: 1.8 }}>
            AI 驱动的智能视频分析，实时守护文物安全
          </p>
        </div>
      </div>

      {/* Right login form */}
      <div
        style={{
          width: 480,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '60px 48px',
          background: wanderMapColors.surface,
        }}
      >
        <div style={{ width: '100%', maxWidth: 360 }}>
          <h2
            style={{
              fontSize: 26,
              fontWeight: 700,
              color: wanderMapColors.textPrimary,
              marginBottom: 8,
            }}
          >
            欢迎回来
          </h2>
          <p style={{ color: wanderMapColors.textSecondary, marginBottom: 40, fontSize: 15 }}>
            请登录您的账号以继续
          </p>

          <Form onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="username"
              label={<span style={{ fontWeight: 500 }}>用户名</span>}
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: wanderMapColors.textSecondary }} />}
                placeholder="请输入用户名"
                style={{ borderRadius: 10, height: 48 }}
              />
            </Form.Item>
            <Form.Item
              name="password"
              label={<span style={{ fontWeight: 500 }}>密码</span>}
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: wanderMapColors.textSecondary }} />}
                placeholder="请输入密码"
                style={{ borderRadius: 10, height: 48 }}
              />
            </Form.Item>
            <Form.Item style={{ marginTop: 32 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 48,
                  borderRadius: 10,
                  fontSize: 16,
                  fontWeight: 600,
                  background: wanderMapColors.secondary,
                  borderColor: wanderMapColors.secondary,
                }}
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        </div>
      </div>
    </div>
  )
}
