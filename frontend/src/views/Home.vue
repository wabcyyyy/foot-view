<template>
  <div class="home-container">
    <NavBar />

    <div class="main-content">
      <div class="hero-section">
        <h1 class="hero-title">开始您的步态分析</h1>
        <p class="hero-subtitle">上传视频，获取专业的生物力学评估报告</p>

        <div class="upload-wrapper">
          <FileUpload @upload-success="onUploadSuccess" />
        </div>
      </div>

      <!-- 历史数据仪表盘 -->
      <div class="dashboard-section" v-if="metricsHistory.length > 0">
        <h2 class="section-title">📊 数据趋势</h2>
        <p class="section-desc">基于 {{ metricsHistory.length }} 次分析记录</p>
        
        <div class="metrics-dashboard">
          <div 
            class="metric-card" 
            v-for="(config, metricName) in metricsConfig" 
            :key="metricName"
            @click="viewMetricDetail(metricName)"
          >
            <div class="metric-card-header">
              <span class="metric-title">{{ metricName }}</span>
              <span class="metric-unit">{{ config.unit }}</span>
            </div>
            
            <!-- 最新值 -->
            <div class="metric-latest">
              <span class="latest-value" :class="getMetricStatus(metricName)">
                {{ getLatestValue(metricName) }}
              </span>
              <span class="trend-indicator" :class="getTrendClass(metricName)">
                {{ getTrendIcon(metricName) }}
              </span>
            </div>
            
            <!-- 迷你趋势图 -->
            <div class="mini-chart">
              <svg viewBox="0 0 100 40" class="trend-line" preserveAspectRatio="xMidYMid meet">
                <!-- 渐变填充 -->
                <defs>
                  <linearGradient :id="'gradient-' + metricName.replace(/\s/g, '')" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#667eea" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="#667eea" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <!-- 填充区域 -->
                <polygon
                  v-if="getChartPointsArray(metricName).length > 1"
                  :points="getAreaPoints(metricName)"
                  :fill="'url(#gradient-' + metricName.replace(/\\s/g, '') + ')'"
                />
                <!-- 折线 -->
                <polyline
                  :points="getChartPoints(metricName)"
                  fill="none"
                  stroke="#667eea"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <!-- 数据点 -->
                <circle
                  v-for="(point, idx) in getChartPointsArray(metricName)"
                  :key="idx"
                  :cx="point.x"
                  :cy="point.y"
                  r="3"
                  fill="#fff"
                  stroke="#667eea"
                  stroke-width="1.5"
                />
              </svg>
            </div>
            
            <div class="metric-footer">
              <span class="metric-desc">{{ config.description }}</span>
              <span class="view-detail">查看详情 →</span>
            </div>
          </div>
        </div>
      </div>

      <div class="history-section" v-if="history.length > 0">
        <h2 class="section-title">📁 最近记录</h2>
        <div class="history-list">
          <div
            v-for="record in history"
            :key="record.id"
            class="history-item"
          >
            <div class="record-info" @click="viewRecord(record.filename)">
              <span class="record-name">{{ formatFilename(record.filename) }}</span>
              <span class="record-date">{{ record.upload_date }}</span>
            </div>
            <button 
              class="delete-btn" 
              @click.stop="confirmDelete(record)"
              title="删除此记录"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      <!-- 删除确认对话框 -->
      <div class="modal-overlay" v-if="showDeleteModal" @click="showDeleteModal = false">
        <div class="modal-content" @click.stop>
          <h3 class="modal-title">确认删除</h3>
          <p class="modal-text">
            确定要删除记录 "<strong>{{ formatFilename(deleteTarget?.filename || '') }}</strong>" 吗？
          </p>
          <p class="modal-warning">此操作将同时删除视频文件和分析结果，且不可恢复。</p>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showDeleteModal = false">取消</button>
            <button class="btn-confirm" @click="deleteRecord" :disabled="deleting">
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FileUpload from '@/components/FileUpload.vue'
import NavBar from '@/components/NavBar.vue'
import axios from 'axios'

export default {
  name: 'Home',
  components: {
    FileUpload,
    NavBar
  },
  data() {
    return {
      history: [],
      metricsHistory: [],
      metricsConfig: {},
      showDeleteModal: false,
      deleteTarget: null,
      deleting: false
    }
  },
  async created() {
    this.fetchHistory();
    this.fetchMetricsHistory();
  },
  methods: {
    onUploadSuccess(filename) {
      this.$router.push({ name: 'Result', params: { filename } })
    },
    async fetchHistory() {
      try {
        const response = await axios.get('/api/history');
        if (response.data.success) {
          this.history = response.data.data;
        }
      } catch (error) {
        console.error('Failed to fetch history:', error);
      }
    },
    async fetchMetricsHistory() {
      try {
        const response = await axios.get('/api/history/metrics');
        if (response.data.success) {
          this.metricsHistory = response.data.data;
          this.metricsConfig = response.data.metrics_config;
        }
      } catch (error) {
        console.error('Failed to fetch metrics history:', error);
      }
    },
    viewRecord(filename) {
      this.$router.push({ name: 'Result', params: { filename } });
    },
    viewMetricDetail(metricName) {
      this.$router.push({ name: 'MetricDetail', params: { metricName } });
    },
    confirmDelete(record) {
      this.deleteTarget = record;
      this.showDeleteModal = true;
    },
    async deleteRecord() {
      if (!this.deleteTarget) return;
      
      this.deleting = true;
      try {
        const response = await axios.delete(`/api/history/${this.deleteTarget.id}`);
        if (response.data.success) {
          // 刷新数据
          this.fetchHistory();
          this.fetchMetricsHistory();
          this.showDeleteModal = false;
          this.deleteTarget = null;
        } else {
          alert(response.data.message || '删除失败');
        }
      } catch (error) {
        console.error('Delete failed:', error);
        alert('删除失败，请重试');
      } finally {
        this.deleting = false;
      }
    },
    formatFilename(filename) {
      // 移除时间戳前缀，显示更友好的名称
      const parts = filename.split('_');
      if (parts.length > 1 && parts[0].length === 14) {
        return parts.slice(1).join('_');
      }
      return filename;
    },
    // 获取指标的最新值
    getLatestValue(metricName) {
      if (this.metricsHistory.length === 0) return '--';
      const latest = this.metricsHistory[this.metricsHistory.length - 1];
      const value = latest.metrics[metricName];
      if (value === null || value === undefined) return '--';
      return value;
    },
    // 获取指标状态（正常/偏高/偏低）
    getMetricStatus(metricName) {
      const value = this.getLatestValue(metricName);
      if (value === '--') return '';
      
      const config = this.metricsConfig[metricName];
      if (!config || !config.normal_range) return '';
      
      const [min, max] = config.normal_range;
      if (value >= min && value <= max) return 'status-normal';
      return 'status-warning';
    },
    // 获取趋势方向
    getTrend(metricName) {
      if (this.metricsHistory.length < 2) return 'stable';
      
      const values = this.metricsHistory
        .map(r => r.metrics[metricName])
        .filter(v => v !== null && v !== undefined);
      
      if (values.length < 2) return 'stable';
      
      const recent = values[values.length - 1];
      const previous = values[values.length - 2];
      const diff = recent - previous;
      const threshold = Math.abs(previous) * 0.05; // 5% 变化阈值
      
      if (diff > threshold) return 'up';
      if (diff < -threshold) return 'down';
      return 'stable';
    },
    getTrendClass(metricName) {
      return 'trend-' + this.getTrend(metricName);
    },
    getTrendIcon(metricName) {
      const trend = this.getTrend(metricName);
      if (trend === 'up') return '↑';
      if (trend === 'down') return '↓';
      return '→';
    },
    // 生成图表点位（固定 viewBox 100x40）
    getChartPoints(metricName) {
      const data = this.metricsHistory.slice(-5); // 最近5条
      if (data.length === 0) return '';
      
      // 收集有效数值（确保转换为数字）
      const validData = [];
      for (const record of data) {
        const val = parseFloat(record.metrics[metricName]);
        if (!isNaN(val)) {
          validData.push(val);
        }
      }
      
      if (validData.length === 0) return '';
      if (validData.length === 1) {
        // 只有一个点，放在中间
        return '50,20';
      }
      
      const min = Math.min(...validData);
      const max = Math.max(...validData);
      const range = max - min;
      
      const points = [];
      const count = validData.length;
      const xStep = 80 / (count - 1); // 10 到 90
      
      for (let i = 0; i < count; i++) {
        const x = 10 + i * xStep;
        let y;
        if (range === 0) {
          y = 20; // 所有值相同，放在中间
        } else {
          // y: 5（顶部，最大值）到 35（底部，最小值）
          const normalized = (validData[i] - min) / range;
          y = 35 - normalized * 30; // 反转：值越大 y 越小
        }
        points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      }
      
      return points.join(' ');
    },
    getChartPointsArray(metricName) {
      const data = this.metricsHistory.slice(-5);
      if (data.length === 0) return [];
      
      // 收集有效数值（确保转换为数字）
      const validData = [];
      for (const record of data) {
        const val = parseFloat(record.metrics[metricName]);
        if (!isNaN(val)) {
          validData.push(val);
        }
      }
      
      if (validData.length === 0) return [];
      if (validData.length === 1) {
        return [{ x: 50, y: 20 }];
      }
      
      const min = Math.min(...validData);
      const max = Math.max(...validData);
      const range = max - min;
      
      const points = [];
      const count = validData.length;
      const xStep = 80 / (count - 1);
      
      for (let i = 0; i < count; i++) {
        const x = 10 + i * xStep;
        let y;
        if (range === 0) {
          y = 20;
        } else {
          const normalized = (validData[i] - min) / range;
          y = 35 - normalized * 30;
        }
        points.push({ x, y });
      }
      
      return points;
    },
    // 生成填充区域点位
    getAreaPoints(metricName) {
      const linePoints = this.getChartPointsArray(metricName);
      if (linePoints.length < 2) return '';
      
      // 起点从左下角开始
      const firstX = linePoints[0].x;
      const lastX = linePoints[linePoints.length - 1].x;
      
      // 构建多边形：左下 -> 所有数据点 -> 右下
      const points = [];
      points.push(`${firstX},40`); // 左下角
      for (const p of linePoints) {
        points.push(`${p.x},${p.y}`);
      }
      points.push(`${lastX},40`); // 右下角
      
      return points.join(' ');
    }
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: #f5f5f7;
}

.main-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
}

.hero-section {
  text-align: center;
  margin-bottom: 50px;
}

.hero-title {
  font-size: 32px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 10px;
}

.hero-subtitle {
  font-size: 16px;
  color: #86868b;
  margin-bottom: 40px;
}

.upload-wrapper {
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  max-width: 600px;
  margin: 0 auto;
}

/* Dashboard Section */
.dashboard-section {
  margin-bottom: 50px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1d1d1f;
}

.section-desc {
  font-size: 14px;
  color: #86868b;
  margin-bottom: 20px;
}

.metrics-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.metric-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  transition: all 0.3s ease;
  cursor: pointer;
}

.metric-card:hover {
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.15);
  transform: translateY(-3px);
  border-color: #667eea;
}

.metric-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.metric-unit {
  font-size: 11px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.metric-latest {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.latest-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', monospace;
}

.latest-value.status-normal {
  color: #34c759;
}

.latest-value.status-warning {
  color: #ff9500;
}

.trend-indicator {
  font-size: 16px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.trend-up {
  color: #ff3b30;
  background: #fff0f0;
}

.trend-down {
  color: #34c759;
  background: #f0fff4;
}

.trend-stable {
  color: #8e8e93;
  background: #f5f5f5;
}

.mini-chart {
  height: 50px;
  margin-bottom: 12px;
  background: linear-gradient(to bottom, #fafafa 0%, #fff 100%);
  border-radius: 8px;
  padding: 5px;
}

.trend-line {
  width: 100%;
  height: 100%;
}

.metric-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-desc {
  font-size: 12px;
  color: #86868b;
}

.view-detail {
  font-size: 12px;
  color: #667eea;
  opacity: 0;
  transition: opacity 0.2s;
}

.metric-card:hover .view-detail {
  opacity: 1;
}

/* History Section */
.history-section {
  margin-bottom: 40px;
}

.history-list {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.history-item:last-child {
  border-bottom: none;
}

.history-item:hover {
  background-color: #fafafa;
}

.record-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding-right: 15px;
}

.delete-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.4;
  transition: all 0.2s;
  border-radius: 6px;
}

.delete-btn:hover {
  opacity: 1;
  background: #fee2e2;
}

.record-name {
  font-weight: 500;
  color: #333;
  font-size: 14px;
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-date {
  font-size: 13px;
  color: #999;
  flex-shrink: 0;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  border-radius: 16px;
  padding: 30px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 15px 0;
  color: #1d1d1f;
}

.modal-text {
  font-size: 14px;
  color: #333;
  margin: 0 0 10px 0;
  line-height: 1.5;
}

.modal-warning {
  font-size: 13px;
  color: #ff3b30;
  margin: 0 0 20px 0;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 10px 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f5f5f5;
}

.btn-confirm {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #ff3b30;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm:hover {
  background: #e0332a;
}

.btn-confirm:disabled {
  background: #ccc;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .metrics-dashboard {
    grid-template-columns: 1fr;
  }
  
  .hero-title {
    font-size: 26px;
  }
  
  .latest-value {
    font-size: 24px;
  }
}
</style>
