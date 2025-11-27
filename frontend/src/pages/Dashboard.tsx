import { useEffect, useState } from 'react'
import { Tabs, Tab, Box, Button, Typography, Paper, Chip } from '@mui/material'
import { Add as AddIcon, Download as DownloadIcon } from '@mui/icons-material'
import api from '../services/api'
import Header from '../components/Header'
import { useNavigate } from 'react-router-dom'

interface Application {
  id: number
  number: number
  need_type: string
  state: string
  created_at: string
}

const stateLabels: Record<string, string> = {
  draft: 'Черновик',
  submitted: 'Подана',
  pre_approved: 'Предодобрена',
  bank_discussed: 'После банка',
  final_approved: 'Окончательно одобрена'
}

const stateColors: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'warning'> = {
  draft: 'default',
  submitted: 'primary',
  pre_approved: 'secondary',
  bank_discussed: 'warning',
  final_approved: 'success'
}

export default function Dashboard() {
  const [tab, setTab] = useState(0)
  const [applications, setApplications] = useState<Application[]>([])
  const navigate = useNavigate()

  const states = ['draft', 'submitted', 'pre_approved', 'bank_discussed', 'final_approved']

  useEffect(() => {
    loadApplications()
  }, [tab])

  const loadApplications = async () => {
    try {
      const res = await api.get('/applications', { params: { state: states[tab] || undefined } })
      setApplications(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const downloadDocx = async (id: number) => {
    try {
      const res = await api.get(`/applications/${id}/download-docx`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Заявка_${id}.docx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      alert('Ошибка скачивания')
    }
  }

  return (
    <>
      <Header />
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h5">Мои заявки</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/application/new')}
          >
            Новая заявка
          </Button>
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
          <Tab label="Черновики" />
          <Tab label="Поданные" />
          <Tab label="Предодобренные" />
          <Tab label="После банка" />
          <Tab label="Одобренные" />
        </Tabs>

        <Box>
          {applications.length === 0 ? (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography>Нет заявок в этом статусе</Typography>
            </Paper>
          ) : (
            applications.map(app => (
              <Paper key={app.id} sx={{ p: 3, mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="h6">Заявка №{app.number}</Typography>
                    <Typography>Вид: {app.need_type || '—'}</Typography>
                    <Typography color="text.secondary">
                      Создано: {new Date(app.created_at).toLocaleDateString('ru-RU')}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip
                      label={stateLabels[app.state]}
                      color={stateColors[app.state]}
                      size="small"
                    />
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => navigate(`/application/${app.id}`)}
                    >
                      Открыть
                    </Button>
                    {(app.state === 'pre_approved' || app.state === 'bank_discussed') && (
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => downloadDocx(app.id)}
                      >
                        DOCX
                      </Button>
                    )}
                  </Box>
                </Box>
              </Paper>
            ))
          )}
        </Box>
      </Box>
    </>
  )
}