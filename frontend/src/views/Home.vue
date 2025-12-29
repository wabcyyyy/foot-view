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

      <div class="history-section" v-if="history.length > 0">
        <h2 class="section-title">最近记录</h2>
        <div class="history-list">
          <div
            v-for="record in history"
            :key="record.id"
            class="history-item"
            @click="viewRecord(record.filename)"
          >
            <span class="record-name">{{ record.filename }}</span>
            <span class="record-date">{{ record.upload_date }}</span>
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
      history: []
    }
  },
  async created() {
    this.fetchHistory();
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
    viewRecord(filename) {
      this.$router.push({ name: 'Result', params: { filename } });
    }
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: #f5f5f7; /* 浅色背景 */
}

.main-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 60px 20px;
  text-align: center;
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
  margin-bottom: 60px;
}

.section-title {
  font-size: 20px;
  font-weight: 500;
  margin-bottom: 20px;
  text-align: left;
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
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s;
}

.history-item:last-child {
  border-bottom: none;
}

.history-item:hover {
  background-color: #fafafa;
}

.record-name {
  font-weight: 500;
  color: #333;
}

.record-date {
  font-size: 14px;
  color: #999;
}
</style>
