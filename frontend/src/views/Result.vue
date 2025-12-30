<template>
  <div class="result-page">
    <NavBar />

    <div class="content-container">
      <div class="breadcrumb">
        <button class="back-btn" @click="$router.push('/')">
          <span class="arrow">←</span> 返回首页
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>正在进行生物力学分析...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <div class="error-icon">!</div>
        <p>{{ error }}</p>
        <button class="btn-retry" @click="$router.push('/')">重试</button>
      </div>

      <div v-else-if="analysisData" class="report-card">
        <!-- 视频播放区域 -->
        <div class="video-section">
          <h3 class="section-title">骨架检测视频</h3>
          <div class="video-container">
            <video 
              :key="'skeleton-' + filename"
              controls 
              playsinline
              class="result-video"
              :src="`/api/video/${encodeURIComponent(filename)}`"
              @error="handleVideoError"
            >
              您的浏览器不支持视频播放
            </video>
            <p v-if="videoError" class="video-error">{{ videoError }}</p>
          </div>
        </div>

        <div class="report-header">
          <h2 class="report-title">步态分析报告</h2>
          <p class="report-subtitle">基于 AI 姿态估计的客观数据测量</p>
        </div>

        <div v-if="fallWarning" class="warning-box">
          <span class="warning-icon">⚠️</span>
          {{ fallWarning }}
        </div>

        <div class="metrics-grid">
          <div class="metric-item" v-for="(row, index) in filteredData" :key="index">
            <div class="metric-header">
              <span class="metric-name">{{ getMetricName(row) }}</span>
              <span class="metric-unit">{{ getMetricUnit(row) }}</span>
            </div>
            <div class="metric-value" :class="{ 'no-data': !hasValidValue(row) }">
              {{ formatMetricValue(row) }}
            </div>
          </div>
        </div>

        <div class="data-note">
          <p>💡 数据说明：以上为客观测量数据，可用于历史趋势对比分析</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import NavBar from '@/components/NavBar.vue';

export default {
  name: 'Result',
  components: {
    NavBar
  },
  props: {
    filename: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      loading: true,
      error: null,
      analysisData: null,
      fallWarning: '',
      videoError: null
    };
  },
  computed: {
    filteredData() {
      if (!this.analysisData) return [];
      // 支持新格式（指标）和旧格式（参数）
      return this.analysisData.filter(row => {
        const name = row['指标'] || row['参数'];
        return name && name !== '总分' && name !== '综合健康状况';
      });
    }
  },
  async created() {
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      const response = await axios.get(`/api/analysis/${this.filename}`);
      if (response.data.success) {
        this.analysisData = response.data.data;
        this.fallWarning = response.data.fall_warning;
      } else {
        this.error = response.data.message;
      }
    } catch (err) {
      this.error = '无法获取分析结果';
      console.error(err);
    } finally {
      this.loading = false;
    }
  },
  methods: {
    // 获取指标名称（兼容新旧格式）
    getMetricName(row) {
      return row['指标'] || row['参数'] || '';
    },
    // 获取单位
    getMetricUnit(row) {
      return row['单位'] || '';
    },
    // 检查是否有有效值
    hasValidValue(row) {
      const value = row['数值'] ?? row['测量值'];
      return value !== '' && value !== null && value !== undefined && value !== '无';
    },
    // 格式化指标值显示
    formatMetricValue(row) {
      // 新格式
      if ('数值' in row) {
        const value = row['数值'];
        if (value === '' || value === null || value === undefined) {
          return '暂无数据';
        }
        return value;
      }
      // 旧格式兼容
      const value = row['测量值'];
      if (value === '' || value === null || value === undefined || value === '无') {
        return '暂无数据';
      }
      return value;
    },
    handleVideoError(event) {
      console.error('视频加载失败:', event);
      this.videoError = '视频加载失败，请刷新页面重试';
    }
  }
};
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background-color: #f5f5f7;
}

.content-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.breadcrumb {
  margin-bottom: 20px;
}

.back-btn {
  background: none;
  font-size: 14px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 0;
  transition: color 0.3s;
}

.back-btn:hover {
  color: #000;
}

/* Loading State */
.loading-state {
  text-align: center;
  padding: 60px 0;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0,0,0,0.1);
  border-top-color: #333;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  text-align: center;
  padding: 60px;
  background: #fff;
  border-radius: 12px;
  color: #c53030;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}

.error-icon {
  width: 60px;
  height: 60px;
  background: #fed7d7;
  color: #c53030;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
  margin: 0 auto 20px;
}

.btn-retry {
  background: #333;
  color: #fff;
  padding: 10px 24px;
  border-radius: 8px;
  margin-top: 20px;
  transition: background 0.3s;
}

.btn-retry:hover {
  background: #000;
}

/* Report Card */
.report-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  animation: fadeIn 0.6s ease;
}

/* Video Section */
.video-section {
  margin-bottom: 40px;
  padding-bottom: 30px;
  border-bottom: 1px solid #e2e8f0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 15px;
}

.video-container {
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
  background: #1a1a2e;
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
}

.result-video {
  width: 100%;
  max-height: 500px;
  display: block;
}

.video-error {
  color: #c53030;
  text-align: center;
  padding: 20px;
  background: #fff5f5;
  margin-top: 10px;
  border-radius: 8px;
}

/* Report Header */
.report-header {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 30px;
  border-bottom: 1px solid #e2e8f0;
}

.report-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.report-subtitle {
  font-size: 14px;
  color: #718096;
}

/* Warning Box */
.warning-box {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  color: #c53030;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.warning-icon {
  font-size: 20px;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-item {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #eee;
  transition: all 0.2s ease;
}

.metric-item:hover {
  background: #f5f5f5;
  border-color: #ddd;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-name {
  font-size: 13px;
  color: #4a5568;
  font-weight: 600;
}

.metric-unit {
  font-size: 11px;
  color: #a0aec0;
  background: #edf2f7;
  padding: 2px 8px;
  border-radius: 10px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #2d3748;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}

.metric-value.no-data {
  font-size: 14px;
  color: #a0aec0;
  font-weight: 500;
}

/* Data Note */
.data-note {
  margin-top: 30px;
  padding: 15px 20px;
  background: #f0f7ff;
  border-radius: 8px;
  text-align: center;
}

.data-note p {
  font-size: 13px;
  color: #0066cc;
  margin: 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 600px) {
  .report-card {
    padding: 24px;
  }

  .report-title {
    font-size: 22px;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metric-value {
    font-size: 20px;
  }
}
</style>
