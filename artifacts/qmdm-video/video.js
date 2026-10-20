(() => {
  const duration = 20;
  const scenes = [
    { name: 'problem', start: 0, end: 4 },
    { name: 'capture', start: 4, end: 8 },
    { name: 'change', start: 8, end: 12 },
    { name: 'recall', start: 12, end: 17 },
    { name: 'end', start: 17, end: 20 },
  ];
  const root = document.querySelector('#video');
  const fill = document.querySelector('#progress-fill');
  const timeLabel = document.querySelector('#progress-time');
  const sceneElements = new Map([...document.querySelectorAll('.scene')].map(node => [node.dataset.scene, node]));

  const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
  const ease = value => value * value * (3 - 2 * value);
  const fade = (value, from, to) => clamp((value - from) / (to - from));
  const formatTime = seconds => `00:${String(Math.min(20, Math.floor(seconds))).padStart(2, '0')}`;

  function setSceneStyles(name, progress) {
    const scene = sceneElements.get(name);
    scene.style.setProperty('--p', progress);
    if (name === 'problem') {
      scene.querySelector('.card-left').style.transform = `translateX(${(1 - ease(fade(progress, 0, .7))) * -34}px)`;
      scene.querySelector('.card-right').style.transform = `translateX(${(1 - ease(fade(progress, 0, .7))) * 34}px)`;
      scene.querySelector('.broken-bridge').style.opacity = fade(progress, .28, .8);
      scene.querySelector('.missing').style.opacity = fade(progress, .5, .9);
    }
    if (name === 'capture') {
      const p = ease(fade(progress, .05, .8));
      scene.querySelector('.source-message').style.transform = `translateX(${(1 - p) * -78}px)`;
      scene.querySelector('.source-message').style.opacity = p;
      scene.querySelector('.capture-arrow').style.opacity = fade(progress, .3, .7);
      scene.querySelector('.memory-node').style.transform = `scale(${.72 + p * .28})`;
      scene.querySelector('.memory-node').style.opacity = fade(progress, .25, .72);
      scene.querySelector('.proof-strip').style.opacity = fade(progress, .62, .95);
    }
    if (name === 'change') {
      const p = ease(fade(progress, 0, .8));
      scene.querySelector('.line-fill').style.width = `${p * 68}%`;
      scene.querySelector('.old-version').style.opacity = .42 + p * .25;
      scene.querySelector('.current-version').style.transform = `translateY(${(1 - p) * 20}px)`;
      scene.querySelector('.current-version').style.opacity = p;
      scene.querySelector('.change-label').style.opacity = fade(progress, .58, .95);
    }
    if (name === 'recall') {
      const p = ease(fade(progress, 0, .86));
      scene.querySelector('.agent-question').style.transform = `translateX(${(1 - p) * -35}px)`;
      scene.querySelector('.agent-question').style.opacity = p;
      scene.querySelector('.signal-graph').style.opacity = fade(progress, .22, .75);
      scene.querySelector('.signal-graph').style.transform = `scale(${.88 + p * .12})`;
      scene.querySelector('.evidence-card').style.transform = `translateX(${(1 - p) * 35}px)`;
      scene.querySelector('.evidence-card').style.opacity = fade(progress, .38, .92);
    }
    if (name === 'end') {
      const p = ease(fade(progress, 0, .7));
      scene.querySelector('.end-core').style.opacity = p;
      scene.querySelector('h1').style.opacity = fade(progress, .12, .75);
      scene.querySelector('.end-copy').style.opacity = fade(progress, .3, .8);
      scene.querySelector('.end-tags').style.opacity = fade(progress, .5, .95);
      scene.querySelectorAll('.end-orbit').forEach((orbit, index) => {
        orbit.style.transform = `rotate(${[-17, 51, 16][index] + p * 18}deg) scale(${.75 + p * .25})`;
        orbit.style.opacity = .35 + p * .65;
      });
    }
  }

  function setTime(seconds) {
    const current = clamp(Number(seconds) || 0, 0, duration - 0.001);
    const active = scenes.find(item => current >= item.start && current < item.end) || scenes[scenes.length - 1];
    sceneElements.forEach((scene, name) => scene.classList.toggle('active', name === active.name));
    setSceneStyles(active.name, (current - active.start) / (active.end - active.start));
    fill.style.width = `${current / duration * 100}%`;
    timeLabel.textContent = `${formatTime(current)} / 00:20`;
    root.dataset.scene = active.name;
    root.dataset.time = current.toFixed(3);
  }

  window.QMDMVideo = { duration, setTime };
  setTime(new URLSearchParams(location.search).has('t') ? Number(new URLSearchParams(location.search).get('t')) : 0);

  if (!new URLSearchParams(location.search).has('render')) {
    let started = performance.now();
    const tick = now => {
      setTime((now - started) / 1000);
      if ((now - started) / 1000 < duration) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
})();
