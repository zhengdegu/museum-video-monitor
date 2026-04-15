import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Avatar, Dropdown, theme } from 'antd'
import {
  DashboardOutlined, VideoCameraOutlined, BankOutlined,
  AlertOutlined, SafetyCertificateOutlined, MessageOutlined,
  GoldOutlined, UserOutlined, CameraOutlined, LogoutOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, AuditOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import { wanderMapColors } from '../theme'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/rooms', icon: <BankOutlined />, label: '库房管理' },
  { key: '/cameras', icon: <CameraOutlined />, label: '摄像头管理' },
  { key: '/videos', icon: <VideoCameraOutlined />, label: '视频管理' },
  { key: '/events', icon: <AlertOutlined />, label: '事件中心' },
  { key: '/rules', icon: <SafetyCertificateOutlined />, label: '规则管理' },
  { key: '/chat', icon: <MessageOutlined />, label: '智能交互' },
  { key: '/collections', icon: <GoldOutlined />, label: '藏品管理' },
  { key: '/inventory', icon: <AuditOutlined />, label: '盘点进出库' },
  { key: '/users', icon: <UserOutlined />, label: '用户管理' },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user } = useAuthStore()
  const { token: { borderRadiusLG } } = theme.useToken()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        theme="dark"
        style={{
          background: `linear-gradient(180deg, ${wanderMapColors.primary} 0%, ${wanderMapColors.siderDarkBg} 100%)`,
          overflow: 'auto',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            padding: '0 16px',
            borderBottom: '1px solid rgba(255,255,255,0.12)',
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            🏛
          </div>
          {!collapsed && (
            <span style={{ color: '#fff', fontSize: 15, fontWeight: 600, whiteSpace: 'nowrap' }}>
              智能监控平台
            </span>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderRight: 'none',
            marginTop: 8,
          }}
    />
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: wanderMapColors.surface,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
            position: 'sticky',
            top: 0,
            zIndex: 9,
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16, width: 40, height: 40 }}
          />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: () => { logout(); navigate('/login') },
                },
              ],
            }}
            placement="bottomRight"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <Avatar
                size={34}
                style={{ background: wanderMapColors.primary }}
                icon={<UserOutlined />}
              />
              <span style={{ color: wanderMapColors.textPrimary, fontSize: 14 }}>
                {user?.username || '管理员'}
              </span>
            </div>
          </Dropdown>
        </Header>

        <Content
          style={{
            margin: 20,
            padding: 24,
            background: wanderMapColors.surface,
            borderRadius: borderRadiusLG,
            minHeight: 280,
            boxShadow: '0 1px 6px rgba(0,0,0,0.05)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
