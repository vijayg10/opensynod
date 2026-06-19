<template>
  <video
    :src="src"
    :controls="controls"
    :autoplay="autoplay"
    :muted="muted"
    :loop="loop"
    :style="style"
    width="100%"
  >
    Your browser does not support the video tag.
  </video>
</template>

<script setup>
const props = defineProps({
  src: { type: String, required: true },
  controls: { type: Boolean, default: true },
  autoplay: { type: Boolean, default: false },
  muted: { type: Boolean, default: false },
  loop: { type: Boolean, default: false },
  style: {
    type: String,
    default: 'border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.12); margin: 1rem 0;'
  },
})
</script>
