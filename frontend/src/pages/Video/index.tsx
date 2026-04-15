import { useEffect, useState, useRef } from 'react'
import { Table, Tag, Button, Space, message, Popconfirm, Select, Modal, Upload, Form, InputNumber, Progress } from 'antd'
import { PlayCircleOutlined, UploadOutlined, FileSearchOutlined } from '@ant-design/icons'
import { getVideos, deleteVideo, triggerAnalyze, uploadInit, uploadChunk, uploadComplete, getCameras, getVideoSegments } from '../../services/api'
import VideoPlayer from '../../components/VideoPlayer'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB per chunk

const statusMap: Record<number, { color: string; text: string }> = {
  0: { color: 'default', text: '待分析' },
  1: { color: 'processing', text: '分析中' },
  2: { color: 'success', text: '已完成' },
  3: { color: 'error', text: '异常' },
}

export default function VideoList() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<number | undefined>()
  const [playVideo, setPlayVideo] = useState<{ src: string } | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [cameras, setCameras] = useState<any[]>([])
  const [uploadForm] = Form.useForm()
  const fileRef = useRef<File | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailData, setDetailData] = useState<any[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const fetchData = async (p = page) => {
    setLoading(true)
    const params: any = { page: p, size: 20 }
    if (statusFilter !== undefined) params.analysis_status = statusFilter
    const res: any = await getVideos(params)
    if (res.code === 200) { setData(res.data.items); setTotal(res.data.total) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [page, statusFilter])

  const handleAnalyze = async (id: number) => {
    const res: any = await triggerAnalyze(id)
    if (res.code === 200) { message.success('已提交分析'); fetchData() }
    else message.error(res.message)
  }

  const openUpload = async () => {
    const res: any = await getCameras({ page: 1, size: 200 })
    if (res.code === 200) setCameras(res.data.items)
    uploadForm.resetFields()
    fileRef.current = null
    setUploadProgress(0)
    setUploadOpen(true)
  }

  const handleUpload = async () => {
    const values = await uploadForm.validateFields()
    const file = fileRef.current
    if (!file) { message.error('请选择视频文件'); return }

    setUploading(true)
    setUploadProgress(0)
    try {
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
      const initRes: any = await uploadInit({
        camera_id: values.camera_id,
        filename: file.name,
        file_size: file.size,
        total_chunks: totalChunks,
      })
      if (initRes.code !== 200) { message.error(initRes.message); setUploading(false); return }

      const { upload_id } = initRes.data
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size)
        const blob = file.slice(start, end)
        const fd = new FormData()
        fd.append('upload_id', upload_id)
        fd.append('chunk_index', String(i))
        fd.append('file', blob)
        await uploadChunk(fd)
        setUploadProgress(Math.round(((i + 1) / totalChunks) * 100))
      }

      const completeFd = new FormData()
      completeFd.append('upload_id', upload_id)
      const completeRes: any = await uploadComplete(completeFd)
      if (completeRes.code === 200) {
        message.success('上传成功')
        setUploadOpen(false)
        fetchData()
      } else {
        message.error(completeRes.message)
      }
    } catch (e) {
      message.error('上传失败')
    }
    setUploading(false)
  }

  const showDetail = async (videoId: number) => {
    setDetailLoading(true)
    setDetailOpen(true)
    const res: any = await getVideoSegments(videoId)
    if (res.code === 200) setDetailData(res.data || [])
    else setDetailData([])
    setDetailLoading(false)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '摄像头ID', dataIndex: 'camera_id', width: 100 },
    { title: '来源', dataIndex: 'source_type', render: (v: number) => v === 1 ? '自动拉取' : '手动上传' },
    { title: '时长(秒)', dataIndex: 'duration' },
    { title: '大小', dataIndex: 'file_size', render: (v: number) => v ? `${(v / 1024 / 1024).toFixed(1)} MB` : '-' },
    { title: '分析状态', dataIndex: 'analysis_status', render: (v: number) => <Tag color={statusMap[v]?.color}>{statusMap[v]?.text}</Tag> },
    {
      title: '操作', render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => setPlayVideo({ src: record.remote_url || `/api/videos/${record.id}/stream` })}>播放</Button>
          {record.analysis_status === 2 && <Button size="small" icon={<FileSearchOutlined />} onClick={() => showDetail(record.id)}>分析详情</Button>}
          {record.analysis_status === 0 && <Button size="small" type="primary" onClick={() => handleAnalyze(record.id)}>开始分析</Button>}
          <Popconfirm title="确认删除？" onConfirm={() => deleteVideo(record.id).then(() => { message.success('已删除'); fetchData() })}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>视频管理</h2>
        <Space>
          <Select allowClear placeholder="按状态筛选" style={{ width: 150 }} onChange={(v) => setStatusFilter(v)}
            options={Object.entries(statusMap).map(([k, v]) => ({ value: Number(k), label: v.text }))} />
          <Button type="primary" icon={<UploadOutlined />} onClick={openUpload}>上传视频</Button>
        </Space>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      {/* 播放弹窗 */}
      <Modal open={!!playVideo} onCancel={() => setPlayVideo(null)} footer={null} width={800} destroyOnClose title="视频播放">
        {playVideo && <VideoPlayer src={playVideo.src} />}
      </Modal>

      {/* 上传弹窗 */}
      <Modal title="上传视频" open={uploadOpen} onOk={handleUpload} onCancel={() => setUploadOpen(false)} confirmLoading={uploading} okText="开始上传">
        <Form form={uploadForm} layout="vertical">
          <Form.Item name="camera_id" label="关联摄像头" rules={[{ required: true, message: '请选择摄像头' }]}>
            <Select options={cameras.map((c: any) => ({ value: c.id, label: `${c.name} (ID:${c.id})` }))} placeholder="选择摄像头" />
          </Form.Item>
          <Form.Item label="视频文件" required>
            <Upload
              beforeUpload={(file) => { fileRef.current = file; return false }}
              maxCount={1}
              accept="video/*"
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
          {uploading && <Progress percent={uploadProgress} />}
        </Form>
      </Modal>

      {/* 分析详情弹窗 */}
      <Modal title="分析详情" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={700}>
        {detailLoading ? <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div> : (
          detailData.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无分析数据</div> : (
            detailData.map((ps: any) => (
              <div key={ps.id} style={{ marginBottom: 24, border: '1px solid #f0f0f0', borderRadius: 8, padding: 16 }}>
                <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
                  人物片段 #{ps.id} — {ps.start_time?.toFixed(1)}s ~ {ps.end_time?.toFixed(1)}s
                  <Tag style={{ marginLeft: 8 }}>{ps.person_count ?? '?'} 人</Tag>
                </div>
                {ps.segments?.map((seg: any) => (
                  <div key={seg.id} style={{ marginLeft: 16, marginBottom: 12, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                    <div style={{ fontSize: 13, color: '#666' }}>
                      片段 #{seg.segment_index} — {seg.start_time?.toFixed(1)}s ~ {seg.end_time?.toFixed(1)}s | 抽帧: {seg.frame_count ?? '-'}
                    </div>
                    {seg.merged_summary && <div style={{ marginTop: 4, fontSize: 13 }}><b>AI结论：</b>{seg.merged_summary}</div>}
                  </div>
                ))}
              </div>
            ))
          )
        )}
      </Modal>
    </div>
  )
}
