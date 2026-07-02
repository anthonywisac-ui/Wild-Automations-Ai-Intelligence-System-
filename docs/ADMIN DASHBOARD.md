ADMIN DASHBOARD
1. Admin Dashboard Architecture
1.1 Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADMIN DASHBOARD ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DASHBOARD WIDGETS                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   System    │  │   Scraper   │  │   AI Cost   │  │   User    │  │  │
│  │  │   Health    │  │   Status    │  │   Analytics │  │   Stats   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  API Usage  │  │  Database   │  │  Cache      │  │   Queue   │  │  │
│  │  │   Metrics   │  │   Metrics   │  │   Metrics   │  │   Metrics │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MANAGEMENT SECTIONS                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Source    │  │   User      │  │   Logs      │  │   System  │  │  │
│  │  │   Manager   │  │   Manager   │  │   Viewer    │  │   Settings│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    ANALYTICS DASHBOARD                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Charts    │  │   Reports   │  │   Trends    │  │   Export  │  │  │
│  │  │   & Graphs  │  │   & Stats   │  │   & Patterns│  │   & Reports│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
2. Admin Controllers
2.1 Admin API
python
# admin/api.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/health")
async def get_system_health(current_user: AdminUser) -> Dict:
    """Get system health status"""
    
    health = await AdminService.get_system_health()
    return health

@router.get("/sources")
async def get_sources(
    current_user: AdminUser,
    status: Optional[str] = None,
    domain: Optional[str] = None
) -> Dict:
    """Get all sources with status"""
    
    sources = await AdminService.get_sources(status=status, domain=domain)
    return sources

@router.post("/sources/{source_id}/scrape")
async def trigger_scrape(
    source_id: str,
    current_user: AdminUser
) -> Dict:
    """Trigger manual scraping for a source"""
    
    try:
        result = await AdminService.trigger_scrape(source_id)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")

@router.put("/sources/{source_id}")
async def update_source(
    source_id: str,
    config: Dict,
    current_user: AdminUser
) -> Dict:
    """Update source configuration"""
    
    try:
        result = await AdminService.update_source(source_id, config)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")

@router.get("/users")
async def get_users(
    current_user: AdminUser,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None
) -> Dict:
    """Get users with pagination"""
    
    users = await AdminService.get_users(page=page, limit=limit, search=search)
    return users

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: AdminUser
) -> Dict:
    """Get user details"""
    
    try:
        user = await AdminService.get_user_details(user_id)
        return user
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: Dict,
    current_user: AdminUser
) -> Dict:
    """Update user by admin"""
    
    try:
        result = await AdminService.update_user(user_id, updates)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

@router.get("/metrics")
async def get_metrics(
    current_user: AdminUser,
    period: str = "day",
    metric_type: Optional[str] = None
) -> Dict:
    """Get system metrics"""
    
    metrics = await AdminService.get_metrics(period=period, metric_type=metric_type)
    return metrics

@router.get("/logs")
async def get_logs(
    current_user: AdminUser,
    level: Optional[str] = None,
    component: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict]:
    """Get system logs"""
    
    logs = await AdminService.get_logs(
        level=level,
        component=component,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    return logs

@router.get("/analytics")
async def get_analytics(
    current_user: AdminUser,
    metric: str,
    start_date: datetime,
    end_date: datetime,
    aggregation: str = "day"
) -> Dict:
    """Get analytics data"""
    
    analytics = await AdminService.get_analytics(
        metric=metric,
        start_date=start_date,
        end_date=end_date,
        aggregation=aggregation
    )
    return analytics
2.2 Admin Service
python
# admin/service.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class AdminService:
    def __init__(
        self,
        user_repo: UserRepository,
        source_repo: SourceRepository,
        metric_service: MetricService,
        logger: Logger
    ):
        self.user_repo = user_repo
        self.source_repo = source_repo
        self.metric_service = metric_service
        self.logger = logger
    
    async def get_system_health(self) -> Dict:
        """Get comprehensive system health"""
        
        # Check database
        db_health = await self._check_database()
        
        # Check Redis
        redis_health = await self._check_redis()
        
        # Check Celery
        celery_health = await self._check_celery()
        
        # Check AI services
        ai_health = await self._check_ai_services()
        
        # Check scrapers
        scraper_health = await self._check_scrapers()
        
        # Overall status
        overall_health = all([
            db_health['status'] == 'healthy',
            redis_health['status'] == 'healthy',
            celery_health['status'] == 'healthy',
            ai_health['status'] == 'healthy',
            scraper_health['status'] == 'healthy'
        ])
        
        return {
            'status': 'healthy' if overall_health else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_health,
                'redis': redis_health,
                'celery': celery_health,
                'ai_services': ai_health,
                'scrapers': scraper_health
            }
        }
    
    async def _check_database(self) -> Dict:
        """Check database health"""
        
        try:
            # Test connection
            await self.user_repo.health_check()
            
            # Get connection stats
            stats = await self.user_repo.get_connection_stats()
            
            return {
                'status': 'healthy',
                'connections': stats.get('connections', 0),
                'max_connections': stats.get('max_connections', 100),
                'latency_ms': stats.get('latency_ms', 0)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_redis(self) -> Dict:
        """Check Redis health"""
        
        try:
            # Test connection
            await self.metric_service.redis_health_check()
            
            # Get stats
            stats = await self.metric_service.get_redis_stats()
            
            return {
                'status': 'healthy',
                'connections': stats.get('connections', 0),
                'memory_usage': stats.get('memory_usage', 0),
                'hit_rate': stats.get('hit_rate', 0)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def get_sources(self, status: Optional[str] = None, domain: Optional[str] = None) -> Dict:
        """Get all sources with status"""
        
        sources = await self.source_repo.get_all(
            status=status,
            domain=domain
        )
        
        # Add current status
        for source in sources:
            source['current_status'] = await self._get_source_status(source['id'])
        
        return {
            'sources': sources,
            'total': len(sources)
        }
    
    async def trigger_scrape(self, source_id: str) -> Dict:
        """Trigger manual scrape"""
        
        source = await self.source_repo.get(source_id)
        if not source:
            raise NotFoundError(f"Source not found: {source_id}")
        
        # Trigger scrape
        job_id = await self._trigger_scrape_job(source_id)
        
        return {
            'status': 'started',
            'job_id': job_id,
            'source_id': source_id,
            'started_at': datetime.utcnow().isoformat()
        }
    
    async def get_metrics(self, period: str = "day", metric_type: Optional[str] = None) -> Dict:
        """Get system metrics"""
        
        # Determine time range
        end_time = datetime.utcnow()
        if period == "hour":
            start_time = end_time - timedelta(hours=1)
        elif period == "day":
            start_time = end_time - timedelta(days=1)
        elif period == "week":
            start_time = end_time - timedelta(days=7)
        elif period == "month":
            start_time = end_time - timedelta(days=30)
        else:
            raise ValueError(f"Invalid period: {period}")
        
        # Get metrics
        metrics = await self.metric_service.get_metrics(
            start_time=start_time,
            end_time=end_time,
            metric_type=metric_type
        )
        
        return {
            'period': period,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'metrics': metrics
        }
3. Dashboard Widgets
3.1 React Components
typescript
// src/components/admin/HealthWidget.tsx
import { useEffect, useState } from 'react'
import { useAdminApi } from '@/hooks/useAdminApi'
import { Card, CardContent, Typography, Grid, Chip } from '@mui/material'
import { CheckCircle, Error, Warning } from '@mui/icons-material'

export const HealthWidget = () => {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const { getHealth } = useAdminApi()
  
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth()
        setHealth(data)
      } catch (error) {
        console.error('Failed to fetch health:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchHealth()
    const interval = setInterval(fetchHealth, 60000) // Refresh every minute
    
    return () => clearInterval(interval)
  }, [])
  
  if (loading) {
    return <LoadingSpinner />
  }
  
  if (!health) {
    return <ErrorWidget message="Failed to load health data" />
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle style={{ color: '#4caf50' }} />
      case 'degraded':
        return <Warning style={{ color: '#ff9800' }} />
      default:
        return <Error style={{ color: '#f44336' }} />
    }
  }
  
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          System Health
        </Typography>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getStatusIcon(health.status)}
          <Typography variant="body1">
            {health.status.charAt(0).toUpperCase() + health.status.slice(1)}
          </Typography>
          <Chip
            label={`Last checked: ${new Date(health.timestamp).toLocaleTimeString()}`}
            size="small"
            variant="outlined"
          />
        </div>
        <Grid container spacing={2} style={{ marginTop: 16 }}>
          {Object.entries(health.components).map(([name, data]) => (
            <Grid item xs={6} key={name}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {getStatusIcon(data.status)}
                <Typography variant="body2">
                  <strong>{name}</strong>
                </Typography>
                <Chip
                  label={data.status}
                  size="small"
                  color={data.status === 'healthy' ? 'success' : 'error'}
                />
              </div>
              {data.error && (
                <Typography variant="caption" color="error">
                  Error: {data.error}
                </Typography>
              )}
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  )
}
3.2 Source Manager
typescript
// src/components/admin/SourceManager.tsx
import { useState, useEffect } from 'react'
import { useAdminApi } from '@/hooks/useAdminApi'
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material'
import { Refresh, PlayArrow, Stop, Settings } from '@mui/icons-material'

export const SourceManager = () => {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedSource, setSelectedSource] = useState(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const { getSources, triggerScrape, updateSource } = useAdminApi()
  
  useEffect(() => {
    fetchSources()
    const interval = setInterval(fetchSources, 30000) // Refresh every 30 seconds
    
    return () => clearInterval(interval)
  }, [])
  
  const fetchSources = async () => {
    try {
      const data = await getSources()
      setSources(data.sources)
    } catch (error) {
      console.error('Failed to fetch sources:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleTriggerScrape = async (sourceId: string) => {
    try {
      await triggerScrape(sourceId)
      await fetchSources() // Refresh after triggering
    } catch (error) {
      console.error('Failed to trigger scrape:', error)
    }
  }
  
  const handleEditSource = (source: any) => {
    setSelectedSource(source)
    setEditDialogOpen(true)
  }
  
  const handleSaveSource = async (updatedConfig: any) => {
    try {
      await updateSource(selectedSource.id, updatedConfig)
      setEditDialogOpen(false)
      await fetchSources()
    } catch (error) {
      console.error('Failed to update source:', error)
    }
  }
  
  const getStatusChip = (status: string) => {
    const colors = {
      idle: 'default',
      running: 'primary',
      completed: 'success',
      failed: 'error',
      retrying: 'warning',
      throttled: 'info'
    }
    return <Chip label={status} color={colors[status] || 'default'} size="small" />
  }
  
  return (
    <>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Source Manager
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Domain</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Scrape</TableCell>
                  <TableCell>Items</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sources.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell>{source.name}</TableCell>
                    <TableCell>
                      <Chip label={source.domain} size="small" />
                    </TableCell>
                    <TableCell>{source.type}</TableCell>
                    <TableCell>{getStatusChip(source.current_status)}</TableCell>
                    <TableCell>
                      {source.last_scrape
                        ? new Date(source.last_scrape).toLocaleString()
                        : 'Never'}
                    </TableCell>
                    <TableCell>{source.items_collected || 0}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleTriggerScrape(source.id)}
                        title="Trigger Scrape"
                      >
                        <PlayArrow />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleEditSource(source)}
                        title="Edit Source"
                      >
                        <Settings />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {}}
                        title="Toggle Source"
                      >
                        {source.enabled ? <Stop /> : <Refresh />}
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      
      {/* Edit Source Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Source</DialogTitle>
        <DialogContent>
          {selectedSource && (
            <div style={{ paddingTop: 16 }}>
              <TextField
                fullWidth
                label="Name"
                value={selectedSource.name}
                onChange={(e) => setSelectedSource({
                  ...selectedSource,
                  name: e.target.value
                })}
                margin="normal"
              />
              <TextField
                fullWidth
                label="Schedule"
                value={selectedSource.schedule}
                onChange={(e) => setSelectedSource({
                  ...selectedSource,
                  schedule: e.target.value
                })}
                margin="normal"
                helperText="Cron expression (e.g., '0 */6 * * *')"
              />
              <FormControl fullWidth margin="normal">
                <InputLabel>Status</InputLabel>
                <Select
                  value={selectedSource.enabled ? 'enabled' : 'disabled'}
                  onChange={(e) => setSelectedSource({
                    ...selectedSource,
                    enabled: e.target.value === 'enabled'
                  })}
                >
                  <MenuItem value="enabled">Enabled</MenuItem>
                  <MenuItem value="disabled">Disabled</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Throttle Limit"
                type="number"
                value={selectedSource.throttle_limit}
                onChange={(e) => setSelectedSource({
                  ...selectedSource,
                  throttle_limit: parseInt(e.target.value)
                })}
                margin="normal"
              />
              <TextField
                fullWidth
                label="Retry Count"
                type="number"
                value={selectedSource.retry_count}
                onChange={(e) => setSelectedSource({
                  ...selectedSource,
                  retry_count: parseInt(e.target.value)
                })}
                margin="normal"
              />
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => handleSaveSource({
              name: selectedSource.name,
              schedule: selectedSource.schedule,
              enabled: selectedSource.enabled,
              throttle_limit: selectedSource.throttle_limit,
              retry_count: selectedSource.retry_count
            })}
            variant="contained"
            color="primary"
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
4. Metrics Dashboard
typescript
// src/components/admin/MetricsDashboard.tsx
import { useEffect, useState } from 'react'
import { useAdminApi } from '@/hooks/useAdminApi'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box
} from '@mui/material'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts'

export const MetricsDashboard = () => {
  const [metrics, setMetrics] = useState(null)
  const [period, setPeriod] = useState('day')
  const [loading, setLoading] = useState(true)
  const { getMetrics } = useAdminApi()
  
  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 60000) // Refresh every minute
    
    return () => clearInterval(interval)
  }, [period])
  
  const fetchMetrics = async () => {
    try {
      const data = await getMetrics({ period })
      setMetrics(data)
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    } finally {
      setLoading(false)
    }
  }
  
  if (loading) {
    return <LoadingSpinner />
  }
  
  if (!metrics) {
    return <div>Failed to load metrics</div>
  }
  
  const { general, performance, cost } = metrics
  
  // Colors for pie chart
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']
  
  // Format data for charts
  const domainData = Object.entries(general.opportunities.domains).map(([name, value]) => ({
    name,
    value
  }))
  
  const modelUsageData = Object.entries(performance.ai.model_usage).map(([name, value]) => ({
    name,
    value: value * 100 // Convert to percentage
  }))
  
  return (
    <div style={{ padding: 24 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Analytics Dashboard</Typography>
        <FormControl variant="outlined" size="small">
          <InputLabel>Period</InputLabel>
          <Select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            label="Period"
          >
            <MenuItem value="hour">Last Hour</MenuItem>
            <MenuItem value="day">Last Day</MenuItem>
            <MenuItem value="week">Last Week</MenuItem>
            <MenuItem value="month">Last Month</MenuItem>
          </Select>
        </FormControl>
      </Box>
      
      <Grid container spacing={3}>
        {/* General Statistics */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Users
              </Typography>
              <Typography variant="h4">
                {general.users.total.toLocaleString()}
              </Typography>
              <Typography color="textSecondary" variant="body2">
                {general.users.active.toLocaleString()} active
              </Typography>
              <Typography color="textSecondary" variant="body2">
                +{general.users.new_today} today
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Opportunities
              </Typography>
              <Typography variant="h4">
                {general.opportunities.total.toLocaleString()}
              </Typography>
              <Typography color="textSecondary" variant="body2">
                {general.opportunities.new_today.toLocaleString()} new today
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                API Requests
              </Typography>
              <Typography variant="h4">
                {performance.api.requests_per_second.toFixed(1)}/s
              </Typography>
              <Typography color="textSecondary" variant="body2">
                Avg: {performance.api.avg_response_time_ms}ms
              </Typography>
              <Typography color="textSecondary" variant="body2">
                Error Rate: {(performance.api.error_rate * 100).toFixed(2)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Daily Cost
              </Typography>
              <Typography variant="h4">
                ${cost.today.toFixed(2)}
              </Typography>
              <Typography color="textSecondary" variant="body2">
                Week: ${cost.week.toFixed(2)}
              </Typography>
              <Typography color="textSecondary" variant="body2">
                Month: ${cost.month.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Domain Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Opportunities by Domain
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={domainData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {domainData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* AI Model Usage */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                AI Model Usage
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={modelUsageData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" label="Usage %" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Scraper Performance */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Scraper Performance
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performance.scrapers.history}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="items_collected"
                    stroke="#8884d8"
                    name="Items Collected"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="success_rate"
                    stroke="#82ca9d"
                    name="Success Rate (%)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </div>
  )
}

