<template>
  <div class="metric-detail-page">
    <NavBar />

    <div class="content-container">
      <div class="breadcrumb">
        <button class="back-btn" @click="$router.push('/')">
          <span class="arrow">←</span> 返回首页
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载数据中...</p>
      </div>

      <div v-else class="detail-content">
        <!-- 指标头部 -->
        <div class="metric-header">
          <div class="metric-icon">{{ metricInfo.icon }}</div>
          <div class="metric-title-area">
            <h1 class="metric-name">{{ metricName }}</h1>
            <span class="metric-unit">单位：{{ metricConfig.unit }}</span>
          </div>
        </div>

        <!-- 数据展示维度选择 -->
        <div class="dimension-selector">
          <span class="selector-label">展示范围：</span>
          <div class="selector-buttons">
            <button 
              v-for="option in dimensionOptions" 
              :key="option.value"
              :class="['dimension-btn', { active: selectedDimension === option.value }]"
              @click="selectedDimension = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <!-- 数据图表区域 -->
        <div class="chart-section">
          <h2 class="section-title">📈 历史趋势</h2>
          
          <div class="chart-container">
            <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="line-chart">
              <!-- 网格线 -->
              <g class="grid-lines">
                <line 
                  v-for="i in 5" 
                  :key="'h'+i"
                  :x1="padding"
                  :y1="padding + (i-1) * (chartHeight - 2*padding) / 4"
                  :x2="chartWidth - padding"
                  :y2="padding + (i-1) * (chartHeight - 2*padding) / 4"
                  stroke="#f0f0f0"
                  stroke-width="1"
                />
              </g>
              
              <!-- Y轴标签 -->
              <g class="y-labels">
                <text 
                  v-for="(label, i) in yLabels" 
                  :key="'y'+i"
                  :x="padding - 10"
                  :y="padding + i * (chartHeight - 2*padding) / 4 + 4"
                  text-anchor="end"
                  font-size="11"
                  fill="#999"
                >
                  {{ label }}
                </text>
              </g>

              <!-- 正常范围区域 -->
              <rect
                v-if="metricConfig.normal_range"
                :x="padding"
                :y="getNormalRangeY().top"
                :width="chartWidth - 2*padding"
                :height="getNormalRangeY().height"
                fill="#e8f5e9"
                opacity="0.5"
              />

              <!-- 数据折线 -->
              <polyline
                :points="chartPoints"
                fill="none"
                stroke="#667eea"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />

              <!-- 数据点 -->
              <g class="data-points">
                <circle
                  v-for="(point, idx) in chartPointsArray"
                  :key="idx"
                  :cx="point.x"
                  :cy="point.y"
                  r="5"
                  fill="#667eea"
                  stroke="#fff"
                  stroke-width="2"
                  class="data-point"
                  @mouseenter="showTooltip(idx, $event)"
                  @mouseleave="hideTooltip"
                />
              </g>

              <!-- X轴标签 -->
              <g class="x-labels">
                <text 
                  v-for="(point, i) in displayedData" 
                  :key="'x'+i"
                  :x="getXPosition(i)"
                  :y="chartHeight - 10"
                  text-anchor="middle"
                  font-size="10"
                  fill="#999"
                >
                  {{ point.date }}
                </text>
              </g>
            </svg>

            <!-- 提示框 -->
            <div 
              v-if="tooltip.visible" 
              class="chart-tooltip"
              :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
            >
              <div class="tooltip-date">{{ tooltip.date }}</div>
              <div class="tooltip-value">{{ tooltip.value }} {{ metricConfig.unit }}</div>
            </div>
          </div>

          <!-- 统计摘要 -->
          <div class="stats-summary">
            <div class="stat-item">
              <span class="stat-label">最新值</span>
              <span class="stat-value">{{ latestValue }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均值</span>
              <span class="stat-value">{{ averageValue }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最大值</span>
              <span class="stat-value">{{ maxValue }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最小值</span>
              <span class="stat-value">{{ minValue }}</span>
            </div>
          </div>
        </div>

        <!-- 数据列表 -->
        <div class="data-list-section">
          <h2 class="section-title">📋 详细记录</h2>
          <div class="data-table">
            <div class="table-header">
              <span class="col-date">日期</span>
              <span class="col-value">数值</span>
              <span class="col-status">状态</span>
              <span class="col-action">操作</span>
            </div>
            <div 
              class="table-row" 
              v-for="record in displayedData" 
              :key="record.id"
            >
              <span class="col-date">{{ record.full_date }}</span>
              <span class="col-value">
                {{ record.value !== null ? record.value : '--' }} 
                <small>{{ metricConfig.unit }}</small>
              </span>
              <span class="col-status">
                <span :class="['status-badge', getValueStatus(record.value)]">
                  {{ getStatusText(record.value) }}
                </span>
              </span>
              <span class="col-action">
                <button class="view-btn" @click="viewRecord(record.filename)">查看</button>
                <button class="delete-btn-small" @click="confirmDelete(record)">删除</button>
              </span>
            </div>
          </div>
        </div>

        <!-- 删除确认对话框 -->
        <div class="modal-overlay" v-if="showDeleteModal" @click="showDeleteModal = false">
          <div class="modal-content" @click.stop>
            <h3 class="modal-title">确认删除</h3>
            <p class="modal-text">确定要删除此记录吗？</p>
            <p class="modal-warning">此操作将同时删除视频文件和分析结果，且不可恢复。</p>
            <div class="modal-actions">
              <button class="btn-cancel" @click="showDeleteModal = false">取消</button>
              <button class="btn-confirm" @click="deleteRecord" :disabled="deleting">
                {{ deleting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 指标说明 -->
        <div class="info-section">
          <h2 class="section-title">📖 指标说明</h2>
          
          <div class="info-card">
            <h3 class="info-title">🔬 指标来源</h3>
            <p class="info-content">{{ metricInfo.source }}</p>
          </div>

          <div class="info-card">
            <h3 class="info-title">💡 临床意义</h3>
            <p class="info-content">{{ metricInfo.meaning }}</p>
          </div>

          <div class="info-card">
            <h3 class="info-title">📊 参考范围</h3>
            <p class="info-content">{{ metricInfo.normalRange }}</p>
            
            <!-- 动态区间说明 -->
            <div class="dynamic-range-info" v-if="metricConfig.normal_range">
              <div class="range-display">
                <span class="range-label">当前参考区间：</span>
                <span class="range-value">
                  {{ metricConfig.normal_range[0] }} - {{ metricConfig.normal_range[1] }} {{ metricConfig.unit }}
                </span>
              </div>
              <div class="range-note" v-if="metricConfig.stats && metricConfig.stats.count >= 5">
                <span class="dynamic-badge">📈 个性化区间</span>
                基于您的 {{ metricConfig.stats.count }} 次有效数据动态计算
                <span v-if="metricConfig.stats.outliers_filtered > 0" class="outlier-info">
                  （已自动过滤 {{ metricConfig.stats.outliers_filtered }} 个异常值）
                </span>
              </div>
              <div class="range-note" v-else-if="metricConfig.stats">
                <span class="base-badge">📋 基准区间</span>
                有效数据不足5次（共 {{ metricConfig.stats.count }} 次），使用中老年人通用参考范围
              </div>
              <div class="range-note" v-else>
                <span class="base-badge">📋 基准区间</span>
                暂无历史数据，使用中老年人通用参考范围
              </div>
            </div>
          </div>

          <div class="info-card">
            <h3 class="info-title">⚠️ 异常提示</h3>
            <div class="warning-list">
              <div class="warning-item high" v-if="metricInfo.highWarning">
                <span class="warning-label">偏高：</span>
                <span>{{ metricInfo.highWarning }}</span>
              </div>
              <div class="warning-item low" v-if="metricInfo.lowWarning">
                <span class="warning-label">偏低：</span>
                <span>{{ metricInfo.lowWarning }}</span>
              </div>
            </div>
          </div>

          <div class="info-card">
            <h3 class="info-title">📝 注意事项</h3>
            <ul class="notes-list">
              <li v-for="(note, idx) in metricInfo.notes" :key="idx">{{ note }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import NavBar from '@/components/NavBar.vue';

// 指标详细信息配置（针对中老年人群体调整）
const METRIC_INFO = {
  '步频': {
    icon: '👣',
    source: '步频是通过检测视频中脚踝关键点的周期性运动计算得出。系统识别每只脚落地的时刻（脚踝Y坐标达到最大值），统计单位时间内的步数，换算为每分钟步数。',
    meaning: '步频反映行走的节奏和速度。中老年人的步频通常比年轻人略低，这是正常的生理变化。步频受年龄、身高、体力状况等因素影响。',
    normalRange: '中老年人正常步频范围约为 70-130 步/分钟。60岁以上人群步频在80-110步/分属于正常范围。系统会根据您的历史数据动态调整个人参考区间。',
    highWarning: '步频明显偏高可能表示步幅过小，常见于帕金森病患者的"小碎步"症状。如果感觉自己"小步快走"，建议关注。',
    lowWarning: '步频过低可能表示行动迟缓、体力下降。但中老年人步频略低是正常现象，不必过于担心，重点关注趋势变化。',
    notes: [
      '测量时应保持日常正常行走速度',
      '中老年人步频略低于年轻人是正常的',
      '重点关注自己的历史趋势变化',
      '如果步频突然明显下降，建议咨询医生',
      '穿着舒适的鞋子，在平坦地面测试效果更好'
    ]
  },
  '步态周期': {
    icon: '⏱️',
    source: '步态周期是指同一只脚从一次着地到下一次着地的时间间隔。通过检测脚踝关键点Y坐标的周期性波峰（落地时刻），计算相邻波峰之间的时间差得出。',
    meaning: '步态周期反映单步所需时间。中老年人由于肌肉力量和关节灵活性的自然下降，步态周期通常会略长，这属于正常生理变化。',
    normalRange: '中老年人正常步态周期约为 0.6-1.6 秒。步态周期略长于年轻人标准是正常的。系统会根据您的历史数据计算个人参考区间。',
    highWarning: '步态周期明显延长可能与肌肉力量下降、关节不适有关。如果感觉行走明显变慢，建议适当锻炼或咨询医生。',
    lowWarning: '步态周期过短可能是代偿性快走。保持舒适的行走节奏即可。',
    notes: [
      '左右腿的步态周期应该接近相等',
      '随年龄增长步态周期略微延长是正常的',
      '保持自然舒适的行走节奏最重要',
      '定期监测，关注变化趋势'
    ]
  },
  '对称性指数': {
    icon: '⚖️',
    source: '对称性指数通过比较左右腿步态周期的差异计算得出。公式为：|左腿周期 - 右腿周期| / 平均周期 × 100%。值越小表示左右对称性越好。',
    meaning: '对称性指数反映双腿运动的协调程度。健康人行走时左右腿应该基本对称，明显不对称可能提示一侧肢体存在不适。',
    normalRange: '中老年人对称性指数 < 10% 属于正常范围。轻微不对称（5-10%）在老年人中较常见，无需过度担心。系统会根据您的历史数据动态调整参考区间。',
    highWarning: '对称性指数明显偏高（>15%）表示左右腿运动不协调，可能原因：一侧下肢疼痛、肌肉力量不对称、关节问题等。建议检查是否有一侧腿不舒服。',
    lowWarning: null,
    notes: [
      '轻微的不对称在中老年人中较常见',
      '对称性指数升高时应检查是否有一侧下肢不适',
      '鞋子磨损不均也可能导致步态不对称',
      '如果一直较高但稳定，问题不大',
      '突然升高需要关注，建议检查'
    ]
  },
  '变异系数': {
    icon: '📉',
    source: '变异系数（CV）是步态周期标准差与平均值的比值，以百分比表示。反映步态周期的稳定性，即每一步的节奏是否一致。',
    meaning: '变异系数衡量步态的稳定性。较低的变异系数表示步态稳定有节奏，较高则表示步态节奏不太规则。由于视频检测的局限性，中老年人的变异系数普遍偏高，这是正常现象。',
    normalRange: '中老年人变异系数 < 50% 属于可接受范围。由于视频检测算法的特性，测量值通常高于临床标准。系统会根据您的历史数据动态调整个人参考区间，重点关注相对变化趋势。',
    highWarning: '变异系数明显偏高（>80%）可能提示步态节奏不规则，但也可能是视频检测误差。建议多次测量，关注平均趋势。',
    lowWarning: null,
    notes: [
      '本系统测量值通常高于临床标准，属于正常现象',
      '重点关注个人历史数据的变化趋势',
      '边走边说话、疲劳等状态会增加变异系数',
      '建议定期监测，观察趋势变化',
      '如数值持续大幅上升，建议咨询医生'
    ]
  },
  '躯干稳定性': {
    icon: '🧍',
    source: '躯干稳定性通过追踪肩部和髋部中点连线与垂直方向的夹角变化来计算。测量每帧之间躯干倾斜角的变化量，取平均值。',
    meaning: '躯干稳定性反映行走时上半身的控制能力。稳定的躯干可以提高行走效率，减少跌倒风险。',
    normalRange: '中老年人躯干稳定性（角度变化）< 1.0 度/帧属于正常范围。略高于年轻人标准是正常的。系统会根据您的历史数据调整参考区间。',
    highWarning: '躯干稳定性数值明显偏高（>1.5度/帧）表示行走时上半身晃动较大，可能需要加强核心肌群锻炼。',
    lowWarning: null,
    notes: [
      '适当的核心肌群锻炼可以改善躯干稳定性',
      '太极拳、瑜伽等运动有助于提高稳定性',
      '躯干稳定性与跌倒预防密切相关',
      '使用拐杖或助行器时数值可能不准确',
      '建议在无辅助行走时测量'
    ]
  },
  '躯干倾斜角': {
    icon: '📐',
    source: '躯干倾斜角是通过计算肩部中点和髋部中点连线与垂直方向的夹角得出。取整个行走过程中的平均值。',
    meaning: '躯干倾斜角反映行走姿态。正常行走时躯干应接近垂直或轻微前倾。中老年人由于脊柱的自然变化，可能有轻度前倾。',
    normalRange: '躯干倾斜角约 0-15 度属于中老年人正常范围。轻度前倾是常见的，不必担心。',
    highWarning: '躯干倾斜角过大（明显前倾）可能见于：驼背、腰椎问题等。如果感觉自己弯腰驼背，可以尝试姿势矫正练习。',
    lowWarning: null,
    notes: [
      '轻度前倾在中老年人中较常见',
      '长期不良姿势可以通过锻炼改善',
      '背部肌肉锻炼有助于改善姿势',
      '如果有腰背疼痛，建议就医检查'
    ]
  },
  '平均步长': {
    icon: '📏',
    source: '平均步长通过计算相邻两次脚落地时，脚踝在水平方向的位移得出。显示为相对值，用于纵向对比个人变化趋势。',
    meaning: '步长反映每一步迈出的距离。中老年人步长通常比年轻人略短，这是正常的。重点关注个人的变化趋势。',
    normalRange: '此为相对值，无固定正常范围。系统会根据您的历史数据建立个人基线，关注趋势变化比绝对值更重要。',
    highWarning: null,
    lowWarning: '步长持续明显下降可能提示下肢功能下降。建议适当进行腿部力量锻炼，如有不适请咨询医生。',
    notes: [
      '主要用于观察个人变化趋势',
      '步长略短于年轻时是正常的',
      '腿部力量锻炼有助于维持步长',
      '如果步长突然明显缩短，需要关注'
    ]
  },
  '摆动幅度': {
    icon: '🦵',
    source: '摆动幅度通过测量脚踝在垂直方向的变化范围得出，反映腿部抬起的高度。数值为相对值，用于纵向对比。',
    meaning: '摆动幅度反映行走时腿部抬起的程度。适当的摆动幅度可以避免绊倒。这是评估跌倒风险的重要指标。',
    normalRange: '此为相对值，无固定正常范围。系统会根据您的历史数据建立个人基线。摆动幅度下降趋势需要关注。',
    highWarning: null,
    lowWarning: '摆动幅度过小（拖步现象）是跌倒的高风险因素。如果发现自己走路时脚抬得越来越低，建议加强腿部锻炼。',
    notes: [
      '拖步是跌倒的重要预警信号',
      '适当的腿部力量训练可以改善',
      '避免穿过重的鞋子',
      '如发现拖步现象明显，建议就医检查'
    ]
  },
  '膝关节活动度': {
    icon: '🦿',
    source: '膝关节活动度通过计算行走过程中膝关节角度的变化范围得出。测量膝关节在步态周期中从屈曲到伸展的角度差。',
    meaning: '膝关节活动度反映膝关节的灵活性。中老年人由于关节的自然退化，活动度可能略低于年轻人。',
    normalRange: '中老年人行走时膝关节活动度约为 30-80 度属于正常范围。略低于年轻人标准是常见的。系统会根据您的历史数据调整参考区间。',
    highWarning: '膝关节活动度异常大可能是韧带松弛的表现，建议关注。',
    lowWarning: '膝关节活动度明显不足可能由于：关节炎、肌肉紧张、疼痛等。适当的关节活动和拉伸有助于改善。',
    notes: [
      '膝关节活动度随年龄略有下降是正常的',
      '每天适当活动关节有助于维持灵活性',
      '游泳、骑车等低冲击运动对关节友好',
      '如有膝关节疼痛，建议就医检查',
      '保持适当体重可以减轻关节负担'
    ]
  }
};

export default {
  name: 'MetricDetail',
  components: {
    NavBar
  },
  props: {
    metricName: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      loading: true,
      historyData: [],
      metricsConfig: {},
      selectedDimension: 10,
      dimensionOptions: [
        { label: '最近5次', value: 5 },
        { label: '最近10次', value: 10 },
        { label: '最近30次', value: 30 },
        { label: '全部', value: 999 }
      ],
      chartWidth: 600,
      chartHeight: 250,
      padding: 50,
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        date: '',
        value: ''
      },
      showDeleteModal: false,
      deleteTarget: null,
      deleting: false
    };
  },
  computed: {
    metricConfig() {
      return this.metricsConfig[this.metricName] || { unit: '', normal_range: null };
    },
    metricInfo() {
      return METRIC_INFO[this.metricName] || {
        icon: '📊',
        source: '暂无说明',
        meaning: '暂无说明',
        normalRange: '暂无数据',
        highWarning: null,
        lowWarning: null,
        notes: []
      };
    },
    displayedData() {
      const data = this.historyData.map(record => ({
        ...record,
        value: record.metrics[this.metricName]
      }));
      return data.slice(-this.selectedDimension);
    },
    validValues() {
      return this.displayedData
        .map(d => parseFloat(d.value))
        .filter(v => !isNaN(v));
    },
    latestValue() {
      if (this.validValues.length === 0) return '--';
      return this.validValues[this.validValues.length - 1];
    },
    averageValue() {
      if (this.validValues.length === 0) return '--';
      const sum = this.validValues.reduce((a, b) => a + b, 0);
      return (sum / this.validValues.length).toFixed(2);
    },
    maxValue() {
      if (this.validValues.length === 0) return '--';
      return Math.max(...this.validValues).toFixed(2);
    },
    minValue() {
      if (this.validValues.length === 0) return '--';
      return Math.min(...this.validValues).toFixed(2);
    },
    yLabels() {
      if (this.validValues.length === 0) return ['', '', '', '', ''];
      const min = Math.min(...this.validValues);
      const max = Math.max(...this.validValues);
      
      // 如果所有值相同，添加一些边距
      let displayMin = min;
      let displayMax = max;
      if (max === min) {
        const margin = Math.abs(min) * 0.1 || 1;
        displayMin = min - margin;
        displayMax = max + margin;
      }
      
      const range = displayMax - displayMin;
      const step = range / 4;
      return [
        displayMax.toFixed(1),
        (displayMax - step).toFixed(1),
        (displayMax - step * 2).toFixed(1),
        (displayMax - step * 3).toFixed(1),
        displayMin.toFixed(1)
      ];
    },
    chartPoints() {
      return this.chartPointsArray.map(p => `${p.x},${p.y}`).join(' ');
    },
    chartPointsArray() {
      const data = this.displayedData;
      if (data.length === 0) return [];
      
      // 收集有效数值
      const validData = [];
      for (let i = 0; i < data.length; i++) {
        const val = parseFloat(data[i].value);
        if (!isNaN(val)) {
          validData.push({ index: i, value: val, date: data[i].full_date });
        }
      }
      
      if (validData.length === 0) return [];
      
      const values = validData.map(d => d.value);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min;
      
      // 计算绘图区域
      const plotHeight = this.chartHeight - 2 * this.padding;
      const xStep = (this.chartWidth - 2 * this.padding) / Math.max(data.length - 1, 1);
      
      const points = [];
      for (const item of validData) {
        const x = this.padding + item.index * xStep;
        let y;
        if (range === 0) {
          // 所有值相同，放在中间
          y = this.padding + plotHeight / 2;
        } else {
          // 正常计算：最大值在上，最小值在下
          const normalized = (item.value - min) / range;
          y = this.padding + (1 - normalized) * plotHeight;
        }
        points.push({ x, y, value: item.value, date: item.date });
      }
      
      return points;
    }
  },
  async created() {
    await this.fetchData();
  },
  methods: {
    async fetchData() {
      try {
        const response = await axios.get('/api/history/metrics');
        if (response.data.success) {
          this.historyData = response.data.data;
          this.metricsConfig = response.data.metrics_config;
        }
      } catch (error) {
        console.error('Failed to fetch metrics history:', error);
      } finally {
        this.loading = false;
      }
    },
    getXPosition(index) {
      const xStep = (this.chartWidth - 2 * this.padding) / Math.max(this.displayedData.length - 1, 1);
      return this.padding + index * xStep;
    },
    getNormalRangeY() {
      if (!this.metricConfig.normal_range || this.validValues.length === 0) {
        return { top: 0, height: 0 };
      }
      
      const [normalMin, normalMax] = this.metricConfig.normal_range;
      const dataMin = Math.min(...this.validValues);
      const dataMax = Math.max(...this.validValues);
      const range = dataMax - dataMin || 1;
      
      const top = this.padding + (1 - (normalMax - dataMin) / range) * (this.chartHeight - 2 * this.padding);
      const bottom = this.padding + (1 - (normalMin - dataMin) / range) * (this.chartHeight - 2 * this.padding);
      
      return {
        top: Math.max(this.padding, Math.min(top, this.chartHeight - this.padding)),
        height: Math.min(bottom - top, this.chartHeight - 2 * this.padding)
      };
    },
    getValueStatus(value) {
      if (value === null || value === undefined) return 'status-none';
      if (!this.metricConfig.normal_range) return 'status-normal';
      
      const [min, max] = this.metricConfig.normal_range;
      if (value >= min && value <= max) return 'status-normal';
      return 'status-warning';
    },
    getStatusText(value) {
      if (value === null || value === undefined) return '无数据';
      if (!this.metricConfig.normal_range) return '正常';
      
      const [min, max] = this.metricConfig.normal_range;
      if (value >= min && value <= max) return '正常';
      if (value < min) return '偏低';
      return '偏高';
    },
    viewRecord(filename) {
      this.$router.push({ name: 'Result', params: { filename } });
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
          await this.fetchData();
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
    showTooltip(idx, event) {
      const point = this.chartPointsArray[idx];
      if (point) {
        this.tooltip = {
          visible: true,
          x: event.offsetX + 10,
          y: event.offsetY - 40,
          date: point.date,
          value: point.value
        };
      }
    },
    hideTooltip() {
      this.tooltip.visible = false;
    }
  }
};
</script>

<style scoped>
.metric-detail-page {
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
  transition: color 0.3s;
}

.back-btn:hover {
  color: #000;
}

/* Loading */
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

/* Header */
.metric-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
  padding: 30px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.metric-icon {
  font-size: 48px;
}

.metric-title-area {
  flex: 1;
}

.metric-name {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 5px 0;
}

.metric-unit {
  font-size: 14px;
  color: #86868b;
}

/* Dimension Selector */
.dimension-selector {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
}

.selector-label {
  font-size: 14px;
  color: #666;
}

.selector-buttons {
  display: flex;
  gap: 8px;
}

.dimension-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.dimension-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.dimension-btn.active {
  background: #667eea;
  border-color: #667eea;
  color: #fff;
}

/* Chart Section */
.chart-section {
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 20px 0;
}

.chart-container {
  position: relative;
  margin-bottom: 20px;
}

.line-chart {
  width: 100%;
  height: auto;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s;
}

.data-point:hover {
  r: 7;
}

.chart-tooltip {
  position: absolute;
  background: #333;
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  pointer-events: none;
  z-index: 10;
}

.tooltip-date {
  font-size: 11px;
  color: #aaa;
  margin-bottom: 2px;
}

.tooltip-value {
  font-weight: 600;
}

/* Stats Summary */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #86868b;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', monospace;
}

/* Data List */
.data-list-section {
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.data-table {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1fr 1fr;
  padding: 12px 15px;
  background: #f9f9f9;
  font-size: 13px;
  font-weight: 600;
  color: #666;
}

.table-row {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1fr 1fr;
  padding: 12px 15px;
  border-top: 1px solid #f0f0f0;
  font-size: 14px;
  align-items: center;
}

.table-row:hover {
  background: #fafafa;
}

.col-value small {
  color: #999;
  margin-left: 3px;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.status-badge.status-normal {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.status-warning {
  background: #fff3e0;
  color: #e65100;
}

.status-badge.status-none {
  background: #f5f5f5;
  color: #999;
}

.view-btn, .delete-btn-small {
  padding: 5px 10px;
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 5px;
}

.view-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.delete-btn-small:hover {
  border-color: #ff3b30;
  color: #ff3b30;
  background: #fff0f0;
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
}

.btn-confirm:hover {
  background: #e0332a;
}

.btn-confirm:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* Info Section */
.info-section {
  margin-bottom: 40px;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 15px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.info-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px 0;
}

.info-content {
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  margin: 0;
}

.warning-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.warning-item {
  padding: 12px 15px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.warning-item.high {
  background: #fff3e0;
  color: #e65100;
}

.warning-item.low {
  background: #e3f2fd;
  color: #1565c0;
}

.warning-label {
  font-weight: 600;
}

.notes-list {
  margin: 0;
  padding-left: 20px;
}

.notes-list li {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

/* 动态区间样式 */
.dynamic-range-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #e0e0e0;
}

.range-display {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.range-label {
  font-size: 13px;
  color: #666;
}

.range-value {
  font-size: 16px;
  font-weight: 600;
  color: #667eea;
  font-family: 'SF Mono', monospace;
}

.range-note {
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dynamic-badge {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
}

.base-badge {
  background: #f0f0f0;
  color: #666;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
}

.outlier-info {
  color: #ff9500;
  font-size: 12px;
  margin-left: 5px;
}

@media (max-width: 600px) {
  .metric-header {
    flex-direction: column;
    text-align: center;
  }
  
  .stats-summary {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .table-header,
  .table-row {
    grid-template-columns: 1fr 1fr;
  }
  
  .col-status,
  .col-action {
    display: none;
  }
  
  .dimension-selector {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .selector-buttons {
    flex-wrap: wrap;
  }
}
</style>

