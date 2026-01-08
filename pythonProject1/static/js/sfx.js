/* sfx.js - The 8-Bit Sound Engine */
const SoundFX = {
    ctx: new (window.AudioContext || window.webkitAudioContext)(),

    playTone: function(freq, type, duration) {
        if (this.ctx.state === 'suspended') this.ctx.resume(); // Wake up audio engine
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = type; // 'sine', 'square', 'sawtooth', 'triangle'
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

        gain.gain.setValueAtTime(0.1, this.ctx.currentTime); // Volume (0.1 is quiet/polite)
        gain.gain.exponentialRampToValueAtTime(0.00001, this.ctx.currentTime + duration);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start();
        osc.stop(this.ctx.currentTime + duration);
    },

    move: function() {
        // A polite "wood" tap (Triangle wave)
        this.playTone(300, 'triangle', 0.1);
    },

    capture: function() {
        // A sharp "crunch" (Sawtooth wave)
        this.playTone(150, 'sawtooth', 0.15);
        setTimeout(() => this.playTone(100, 'sawtooth', 0.1), 50);
    },

    error: function() {
        // A low "buzz"
        this.playTone(150, 'sawtooth', 0.3);
        this.playTone(100, 'square', 0.3);
    },

    success: function() {
        // A happy "Ding!" (High sine wave)
        this.playTone(600, 'sine', 0.1);
        setTimeout(() => this.playTone(800, 'sine', 0.2), 100);
    },

    start: function() {
        // A "Power On" slide
        this.playTone(200, 'sine', 0.1);
        setTimeout(() => this.playTone(400, 'sine', 0.2), 100);
        setTimeout(() => this.playTone(600, 'sine', 0.4), 200);
    }
};