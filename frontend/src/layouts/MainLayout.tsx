import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Avatar, Dropdown, Input } from 'antd'
import {
  DashboardOutlined, VideoCameraOutlined, BankOutlined,
  AlertOutlined, SafetyCertificateOutlined, MessageOutlined,
  GoldOutlined, UserOutlined, CameraOutlined, LogoutOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, AuditOutlined, FileTextOutlined,
  ApiOutlined, LinkOutlined, WarningOutlined, SyncOutlined,
  HeatMapOutlined, ClusterOutlined, SearchOutlined, BellOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import { genesisColors } from '../theme'

const { Header, Sider, Content } = Layout

const menuGroups = [
  {
    label: '概览',
    items: [
      { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
    ],
  },
  {
    label: '资产管理',
    items: [
      { key: '/rooms', icon: <BankOutlined />, label: '库房管理' },
      { key: '/room-map', icon: <HeatMapOutlined />, label: '库房地图' },
      { key: '/cameras', icon: <CameraOutlined />, label: '摄像头管理' },
      { key: '/collections', icon: <GoldOutlined />, label: '藏品管理' },
    ],
  },
  {
    label: '监控分析',
    items: [
      { key: '/videos', icon: <VideoCameraOutlined />, label: '视频管理' },
      { key: '/events', icon: <AlertOutlined />, label: '事件中心' },
      { key: '/warnings', icon: <WarningOutlined />, label: '预警中心' },
      { key: '/rules', icon: <SafetyCertificateOutlined />, label: '规则管理' },
      { key: '/chat', icon: <MessageOutlined />, label: '智能交互' },
    ],
  },
  {
    label: '运营管理',
    items: [
      { key: '/inventory', icon: <AuditOutlined />, label: '盘点进出库' },
      { key: '/ai-inventory', icon: <SyncOutlined />, label: 'AI 盘点' },
      { key: '/reports', icon: <FileTextOutlined />, label: '合规报告' },
      { key: '/nodes', icon: <ClusterOutlined />, label: '多馆管控' },
    ],
  },
  {
    label: '系统设置',
    items: [
      { key: '/users', icon: <UserOutlined />, label: '用户管理' },
      { key: '/push-channels', icon: <BellOutlined />, label: '推送渠道' },
      { key: '/api-keys', icon: <ApiOutlined />, label: 'API Key' },
      { key: '/webhooks', icon: <LinkOutlined />, label: 'Webhook' },
    ],
  },
]

// Build flat menu items with group labels for Ant Design Menu
const menuItems = menuGroups.flatMap((group) => [
  { type: 'group' as const, label: group.label, key: `group-${group.label}`, children: group.items },
])

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user } = useAuthStore()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        collapsedWidth={72}
        style={{
          background: genesisColors.surface,
          borderRight: `1px solid ${genesisColors.border}`,
          overflow: 'auto',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: 10,
            padding: collapsed ? '0' : '0 20px',
            borderBottom: `1px solid ${genesisColors.border}`,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: genesisColors.primary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18L20 8v8l-8 4-8-4V8l8-3.82z" />
            </svg>
          </div>
          {!collapsed && (
            <span style={{ color: genesisColors.textPrimary, fontSize: 15, fontWeight: 700, letterSpacing: '-0.03em', whiteSpace: 'nowrap' }}>
              智能监控平台
            </span>
          )}
        </div>

        {/* Navigation */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderRight: 'none',
            marginTop: 8,
            fontSize: 13.5,
          }}
        />
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 72 : 240, transition: 'margin-left 0.2s' }}>
        {/* Header */}
        <Header
          style={{
            padding: '0 24px',
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${genesisColors.border}`,
            position: 'sticky',
            top: 0,
            zIndex: 9,
            height: 56,
            lineHeight: '56px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: 16, width: 36, height: 36, color: genesisColors.textSecondary }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Input
              prefix={<SearchOutlined style={{ color: genesisColors.neutral }} />}
              placeholder="搜索..."
              style={{
                width: 220,
                borderRadius: 6,
                background: genesisColors.background,
              }}
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
                  size={32}
                  style={{ background: genesisColors.primary, fontSize: 13, fontWeight: 600 }}
                  icon={<UserOutlined />}
                />
                <span style={{ color: genesisColors.textPrimary, fontSize: 14, fontWeight: 500 }}>
                  {user?.username || '管理员'}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* Content */}
        <Content
          style={{
            padding: 24,
            minHeight: 280,
            background: genesisColors.background,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
