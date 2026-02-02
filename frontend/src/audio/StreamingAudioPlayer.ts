export class StreamingAudioPlayer {
  private context: AudioContext | null = null;
  private nextStartTime = 0;
  private enabled = false;
  private inUtterance = false;
  private activeSources = new Set<AudioBufferSourceNode>();
  private chunkCounter = 0;  // DEBUG: Track chunks for identification

  async enable(): Promise<boolean> {
    try {
      const ctx = this.ensureContext();
      await ctx.resume();
      this.enabled = true;
      if (this.nextStartTime < ctx.currentTime) {
        this.nextStartTime = ctx.currentTime;
      }
      return true;
    } catch (error) {
      console.warn('[Audio] Failed to enable audio context:', error);
      return false;
    }
  }

  handleChunk(chunkB64: string, sampleRate: number, isFinal: boolean): void {
    const chunkId = ++this.chunkCounter;

    // DEBUG: Compute hash of first few bytes to identify unique audio
    const partialHash = chunkB64 ? chunkB64.slice(0, 32) : '';
    console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: length=${chunkB64?.length || 0}, sampleRate=${sampleRate}, isFinal=${isFinal}, inUtterance=${this.inUtterance}, hash=${partialHash}`);

    if (!chunkB64) {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Empty chunk, returning early`);
      if (isFinal) {
        this.inUtterance = false;
        this.reset();
      }
      return;
    }

    const ctx = this.ensureContext();
    console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: AudioContext state=${ctx.state}, currentTime=${ctx.currentTime.toFixed(3)}, enabled=${this.enabled}`);

    if (!this.enabled && ctx.state === 'suspended') {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Resuming suspended context`);
      ctx.resume().catch(() => undefined);
    }

    // Treat the first non-empty chunk after a completed utterance as a new utterance and
    // stop any previous playback to avoid overlaps.
    if (!this.inUtterance) {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: NEW UTTERANCE - calling stopAll() (${this.activeSources.size} active sources)`);
      this.stopAll();
      this.reset();
      this.inUtterance = true;
    }

    const int16 = base64ToInt16(chunkB64);
    if (!int16.length) {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Decoded to 0 samples, returning early`);
      if (isFinal) {
        this.inUtterance = false;
        this.reset();
      }
      return;
    }

    // DEBUG: Hash first 8 int16 samples to verify unique audio data
    const sampleHash = Array.from(int16.slice(0, 8)).join(',');
    console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Decoded ${int16.length} samples, first 8: [${sampleHash}]`);

    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i += 1) {
      float32[i] = Math.max(-1, Math.min(1, int16[i] / 32768));
    }

    const bufferRate = sampleRate && sampleRate > 0 ? sampleRate : ctx.sampleRate;
    const buffer = ctx.createBuffer(1, float32.length, bufferRate);
    buffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    this.activeSources.add(source);
    source.onended = () => {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Source ended`);
      this.activeSources.delete(source);
    };

    const startTime = Math.max(this.nextStartTime, ctx.currentTime + 0.05);
    console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Scheduling playback - startTime=${startTime.toFixed(3)}, duration=${buffer.duration.toFixed(3)}s, nextStartTime will be=${(startTime + buffer.duration).toFixed(3)}`);
    source.start(startTime);
    this.nextStartTime = startTime + buffer.duration;

    if (isFinal) {
      console.log(`[AudioPlayer DEBUG] Chunk #${chunkId}: Final chunk - setting inUtterance=false`);
      this.inUtterance = false;
      this.reset();
    }
  }

  reset(): void {
    if (this.context) {
      this.nextStartTime = this.context.currentTime;
    } else {
      this.nextStartTime = 0;
    }
  }

  stopAll(): void {
    const count = this.activeSources.size;
    console.log(`[AudioPlayer DEBUG] stopAll() called - stopping ${count} sources`);
    for (const source of this.activeSources) {
      try {
        source.stop();
        console.log(`[AudioPlayer DEBUG] stopAll() - stopped a source`);
      } catch (e) {
        console.log(`[AudioPlayer DEBUG] stopAll() - source already stopped/ended`);
      }
    }
    this.activeSources.clear();
  }

  private ensureContext(): AudioContext {
    if (!this.context) {
      this.context = new AudioContext();
    }
    return this.context;
  }
}

function base64ToInt16(b64: string): Int16Array {
  const binary = atob(b64);
  const length = binary.length;
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}
