<template>
  <div class="avatar" :class="[`avatar--${size}`, { 'avatar--rounded': rounded }]">
    <img 
      v-if="src" 
      :src="src" 
      :alt="alt || name"
      class="avatar__image"
      @error="showFallback = true"
      v-show="!showFallback"
    />
    <div v-if="!src || showFallback" class="avatar__fallback">
      {{ initials }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'Avatar',
  props: {
    name: {
      type: String,
      default: 'Usuario'
    },
    src: {
      type: String,
      default: null
    },
    alt: {
      type: String,
      default: null
    },
    size: {
      type: String,
      default: 'md',
      validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value)
    },
    rounded: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      showFallback: false
    }
  },
  computed: {
    initials() {
      if (!this.name) return '?'
      
      const words = this.name.trim().split(' ')
      if (words.length === 1) {
        return words[0].charAt(0).toUpperCase()
      }
      return (words[0].charAt(0) + words[words.length - 1].charAt(0)).toUpperCase()
    }
  }
}
</script>

<style scoped>
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #e2e8f0;
  color: #4a5568;
  font-weight: 600;
  overflow: hidden;
  position: relative;
}

.avatar--rounded {
  border-radius: 50%;
}

.avatar--sm {
  width: 32px;
  height: 32px;
  font-size: 14px;
}

.avatar--md {
  width: 48px;
  height: 48px;
  font-size: 16px;
}

.avatar--lg {
  width: 64px;
  height: 64px;
  font-size: 20px;
}

.avatar--xl {
  width: 96px;
  height: 96px;
  font-size: 28px;
}

.avatar__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar__fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}
</style>
