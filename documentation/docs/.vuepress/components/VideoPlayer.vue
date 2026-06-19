<template>
  <video
    :src="resolvedSrc"
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
import { computed } from 'vue'
import { withBase } from 'vuepress/client'

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

// Resolve absolute (public) paths against the site `base` so the video URL
// stays correct on GitHub Pages (e.g. /videos/x.mp4 -> /opensynod/videos/x.mp4).
const resolvedSrc = computed(() =>
  props.src.startsWith('/') ? withBase(props.src) : props.src
)
</script>
