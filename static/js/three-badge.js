/* ========================================================
   NCC 3D Badge - Three.js Renderer
   ======================================================== */

(function () {
  const canvas = document.getElementById('badge-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const scene    = new THREE.Scene();
  const camera   = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  const renderer = new THREE.WebGLRenderer({ canvas, alpha:true, antialias:true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(canvas.clientWidth, canvas.clientHeight);
  renderer.setClearColor(0x000000, 0);
  camera.position.z = 3.5;

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);
  const dLight1 = new THREE.DirectionalLight(0x4fc3e8, 2.5);
  dLight1.position.set(2, 3, 4);
  scene.add(dLight1);
  const dLight2 = new THREE.DirectionalLight(0xff4444, 1.5);
  dLight2.position.set(-3, -2, 2);
  scene.add(dLight2);
  const dLight3 = new THREE.DirectionalLight(0x0d2b5e, 1.2);
  dLight3.position.set(0, -4, -2);
  scene.add(dLight3);
  const pointLight = new THREE.PointLight(0xffffff, 1, 8);
  pointLight.position.set(0, 0, 3);
  scene.add(pointLight);

  // Badge Group
  const badge = new THREE.Group();
  scene.add(badge);

  // Outer ring
  const ringGeo = new THREE.TorusGeometry(1.1, 0.06, 16, 80);
  const ringMat = new THREE.MeshStandardMaterial({
    color: 0x0d2b5e, metalness: 0.8, roughness: 0.2
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  badge.add(ring);

  // Inner ring
  const ring2Geo = new THREE.TorusGeometry(0.96, 0.03, 16, 80);
  const ring2Mat = new THREE.MeshStandardMaterial({
    color: 0xC0392B, metalness: 0.9, roughness: 0.15
  });
  const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
  badge.add(ring2);

  // Main disc
  const discGeo = new THREE.CylinderGeometry(0.9, 0.9, 0.08, 64);
  const discMat = new THREE.MeshStandardMaterial({
    color: 0xfafafa, metalness: 0.3, roughness: 0.5
  });
  const disc = new THREE.Mesh(discGeo, discMat);
  disc.rotation.x = Math.PI / 2;
  badge.add(disc);

  // NCC Letters (3 petals / lotus shapes)
  const petalColors = [0xC0392B, 0x0D2B5E, 0x3498db];
  for (let i = 0; i < 3; i++) {
    const angle = (i / 3) * Math.PI * 2 - Math.PI/2;
    const geo = new THREE.SphereGeometry(0.22, 16, 12);
    const mat = new THREE.MeshStandardMaterial({
      color: petalColors[i], metalness: 0.6, roughness: 0.3
    });
    const petal = new THREE.Mesh(geo, mat);
    petal.position.x = Math.cos(angle) * 0.42;
    petal.position.y = Math.sin(angle) * 0.42;
    petal.position.z = 0.08;
    petal.scale.set(1, 0.65, 0.5);
    badge.add(petal);
  }

  // Center sphere
  const centerGeo = new THREE.SphereGeometry(0.15, 24, 24);
  const centerMat = new THREE.MeshStandardMaterial({
    color: 0xffd700, metalness: 0.9, roughness: 0.1
  });
  const center = new THREE.Mesh(centerGeo, centerMat);
  center.position.z = 0.1;
  badge.add(center);

  // Decorative dots on ring
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2;
    const geo = new THREE.SphereGeometry(0.03, 8, 8);
    const mat = new THREE.MeshStandardMaterial({
      color: i % 2 === 0 ? 0xffd700 : 0xC0392B,
      metalness: 0.9, roughness: 0.1
    });
    const dot = new THREE.Mesh(geo, mat);
    dot.position.x = Math.cos(angle) * 1.1;
    dot.position.y = Math.sin(angle) * 1.1;
    dot.position.z = 0.05;
    badge.add(dot);
  }

  // Particles
  const particleGeo = new THREE.BufferGeometry();
  const count = 180;
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count * 3; i++) {
    pos[i] = (Math.random() - 0.5) * 6;
  }
  particleGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const particleMat = new THREE.PointsMaterial({
    size: 0.025,
    color: 0x3498db,
    transparent: true,
    opacity: 0.5,
    sizeAttenuation: true
  });
  const particles = new THREE.Points(particleGeo, particleMat);
  scene.add(particles);

  // Mouse interaction
  let mouseX = 0, mouseY = 0;
  document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseY = -(e.clientY / window.innerHeight - 0.5) * 2;
  });

  // Animation loop
  const clock = new THREE.Clock();
  const animate = () => {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    badge.rotation.y = t * 0.5 + mouseX * 0.3;
    badge.rotation.x = Math.sin(t * 0.4) * 0.2 + mouseY * 0.2;
    center.scale.setScalar(1 + Math.sin(t * 2) * 0.1);
    particles.rotation.y = t * 0.05;
    renderer.render(scene, camera);
  };
  animate();

  // Resize
  const resizeObserver = new ResizeObserver(() => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w/h;
    camera.updateProjectionMatrix();
  });
  resizeObserver.observe(canvas);
})();
