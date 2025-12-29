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
        <div class="report-header">
          <div class="score-circle">
            <svg viewBox="0 0 36 36" class="circular-chart">
              <path class="circle-bg"
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path class="circle"
                :stroke-dasharray="getScorePercentage() + ', 100'"
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <text x="18" y="20.35" class="percentage">{{ getTotalScore() }}</text>
            </svg>
            <span class="score-label">总分</span>
          </div>

          <div class="grade-info">
            <span class="grade-label">健康等级</span>
            <span class="grade-value">{{ getGrade() }}</span>
          </div>
        </div>

        <div v-if="fallWarning" class="warning-box">
          <span class="warning-icon">⚠️</span>
          {{ fallWarning }}
        </div>

        <div class="metrics-grid">
          <div class="metric-item" v-for="(row, index) in filteredData" :key="index">
            <div class="metric-header">
              <span class="metric-name">{{ row['参数'] }}</span>
              <span class="metric-score" :class="getScoreClass(row['评分'])">
                {{ row['评分'] }}分
              </span>
            </div>
            <div class="metric-value">{{ row['测量值'] }}</div>
          </div>
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
      fallWarning: ''
    };
  },
  computed: {
    filteredData() {
      if (!this.analysisData) return [];
      return this.analysisData.filter(row =>
        row['参数'] &&
        row['参数'] !== '总分' &&
        row['参数'] !== '综合健康状况'
      );
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
    getGrade() {
      const row = this.analysisData?.find(r => r['参数'] === '综合健康状况');
      return row ? row['测量值'] : '-';
    },
    getTotalScore() {
      const row = this.analysisData?.find(r => r['参数'] === '总分');
      return row ? row['测量值'] : 0;
    },
    getScorePercentage() {
      const score = this.getTotalScore();
      return (score / 12) * 100;
    },
    getScoreClass(score) {
      if (score == 3) return 'score-high';
      if (score == 2) return 'score-med';
      return 'score-low';
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
  max-width: 800px;
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
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Report Card */
.report-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  animation: fadeIn 0.6s ease;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-around;
  margin-bottom: 40px;
  padding-bottom: 40px;
  border-bottom: 1px solid #f0f0f0;
}

.score-circle {
  width: 120px;
  height: 120px;
  position: relative;
}

.circular-chart {
  display: block;
  margin: 0 auto;
  max-width: 100%;
  max-height: 100%;
}

.circle-bg {
  fill: none;
  stroke: #eee;
  stroke-width: 2.5;
}

.circle {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke: #000;
  animation: progress 1s ease-out forwards;
}

.percentage {
  fill: #000;
  font-family: sans-serif;
  font-weight: bold;
  font-size: 10px;
  text-anchor: middle;
}

.score-label {
  position: absolute;
  bottom: -25px;
  left: 0;
  width: 100%;
  text-align: center;
  font-size: 14px;
  color: #666;
}

.grade-info {
  text-align: center;
}

.grade-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.grade-value {
  font-size: 48px;
  font-weight: 700;
  color: #000;
}

/* Warning Box */
.warning-box {
  background-color: #fff5f5;
  border: 1px solid #fed7d7;
  color: #c53030;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.metric-item {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #eee;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.metric-name {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.metric-score {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.score-high { background: #e6fffa; color: #2c7a7b; }
.score-med { background: #fffaf0; color: #c05621; }
.score-low { background: #fff5f5; color: #c53030; }

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: #000;
  font-family: 'Inter', sans-serif;
}

@keyframes progress {
  0% { stroke-dasharray: 0 100; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 600px) {
  .report-header {
    flex-direction: column;
    gap: 40px;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
