<template>
  <div id="app">
    <TestPage />
  </div>
</template>

<script>
import TestPage from './pages/Test.vue'

export default {
  name: 'App',
  components: {
    TestPage
  }
}
</script>

<style>
#app {
  min-height: 100vh;
  background-color: #f5f5f5;
}

body {
  margin: 0;
  padding: 0;
}
</style> 