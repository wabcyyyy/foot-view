<template>
  <nav class="navbar">
    <div class="nav-content">
      <div class="logo" @click="$router.push('/')">
        FOOT VIEW
      </div>
      <div class="user-menu">
        <span class="username" v-if="user">{{ user.username }}</span>
        <button class="logout-btn" @click="logout">退出</button>
      </div>
    </div>
  </nav>
</template>

<script>
import axios from 'axios';

export default {
  name: 'NavBar',
  data() {
    return {
      user: null
    };
  },
  async created() {
    try {
      const response = await axios.get('/api/user/current');
      if (response.data.is_authenticated) {
        this.user = response.data.user;
      }
    } catch (error) {
      console.error(error);
    }
  },
  methods: {
    async logout() {
      try {
        await axios.get('/api/logout');
        this.$router.push('/login');
      } catch (error) {
        console.error(error);
      }
    }
  }
};
</script>

<style scoped>
.navbar {
  background-color: #fff;
  border-bottom: 1px solid #e5e5e5;
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-weight: 700;
  font-size: 18px;
  cursor: pointer;
  letter-spacing: 1px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 20px;
}

.username {
  font-size: 14px;
  color: #333;
}

.logout-btn {
  background: none;
  border: 1px solid #e5e5e5;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  transition: all 0.2s;
}

.logout-btn:hover {
  border-color: #333;
  color: #333;
}
</style>
