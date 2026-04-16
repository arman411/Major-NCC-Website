// animations-3d.js
(function() {
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve(); return;
            }
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async function init3D() {
        try {
            // Load libraries
            await Promise.all([
                loadScript('https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.0/vanilla-tilt.min.js'),
                loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js')
            ]);
            await loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js');
            await loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');

            // 1. VanillaTilt
            if (window.VanillaTilt) {
                VanillaTilt.init(document.querySelectorAll(".award-card, .stat-card, .gallery-item, .chart-card, .cadet-spotlight"), {
                    max: 8,
                    speed: 400,
                    glare: true,
                    "max-glare": 0.15,
                    scale: 1.02
                });
            }

            // 2. GSAP ScrollReveal
            if (window.gsap && window.ScrollTrigger) {
                gsap.registerPlugin(ScrollTrigger);
                gsap.utils.toArray('.award-card, .gallery-item, .notice-card, .stat-card').forEach(el => {
                    gsap.from(el, {
                        scrollTrigger: {
                            trigger: el,
                            start: "top 90%",
                            toggleActions: "play none none reverse"
                        },
                        y: 40,
                        rotationX: 10,
                        opacity: 0,
                        duration: 0.7,
                        ease: "power3.out"
                    });
                });
            }

            // 3. Three.js Particle Hero Background
            const hero = document.querySelector('.page-hero');
            if (hero && window.THREE) {
                hero.style.position = 'relative';
                
                // Ensure content is above canvas
                const content = hero.querySelector('.page-hero-content');
                if(content) content.style.zIndex = '2';

                const canvas = document.createElement('canvas');
                canvas.style.position = 'absolute';
                canvas.style.top = '0';
                canvas.style.left = '0';
                canvas.style.width = '100%';
                canvas.style.height = '100%';
                canvas.style.zIndex = '1';
                canvas.style.opacity = '0.7';
                canvas.style.pointerEvents = 'none';
                hero.insertBefore(canvas, hero.firstChild);

                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(75, hero.clientWidth / hero.clientHeight, 0.1, 1000);
                const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
                renderer.setSize(hero.clientWidth, hero.clientHeight);
                renderer.setPixelRatio(window.devicePixelRatio);

                const geometry = new THREE.BufferGeometry();
                const count = window.innerWidth < 768 ? 80 : 250;
                const positions = new Float32Array(count * 3);
                for(let i=0; i<count*3; i++){
                    positions[i] = (Math.random() - 0.5) * 20;
                }
                geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                
                // create star texture
                const canvasTexture = document.createElement('canvas');
                canvasTexture.width = 32; canvasTexture.height = 32;
                const ctx = canvasTexture.getContext('2d');
                ctx.beginPath();
                ctx.arc(16, 16, 14, 0, Math.PI*2);
                ctx.fillStyle = '#ffffff';
                ctx.fill();
                const texture = new THREE.CanvasTexture(canvasTexture);

                const material = new THREE.PointsMaterial({
                    size: 0.1,
                    color: 0x5dade2,
                    transparent: true,
                    opacity: 0.6,
                    map: texture,
                    blending: THREE.AdditiveBlending,
                    depthWrite: false
                });
                const particles = new THREE.Points(geometry, material);
                scene.add(particles);
                camera.position.z = 5;

                let mouseX = 0;
                let mouseY = 0;
                document.addEventListener('mousemove', (e) => {
                    mouseX = (e.clientX / window.innerWidth) - 0.5;
                    mouseY = (e.clientY / window.innerHeight) - 0.5;
                });

                function animate() {
                    requestAnimationFrame(animate);
                    particles.rotation.y += 0.0005;
                    particles.rotation.x += 0.0002;
                    particles.position.x += (mouseX * 0.3 - particles.position.x) * 0.05;
                    particles.position.y += (-mouseY * 0.3 - particles.position.y) * 0.05;
                    renderer.render(scene, camera);
                }
                animate();

                window.addEventListener('resize', () => {
                    if(!hero) return;
                    camera.aspect = hero.clientWidth / hero.clientHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(hero.clientWidth, hero.clientHeight);
                });
            }

        } catch (e) {
            console.error('Failed to load 3D animation libraries', e);
        }

        // Inject Back-to-Top Button
        const btt = document.createElement('button');
        btt.className = 'back-to-top';
        btt.innerHTML = '↑';
        btt.title = "Back to Top";
        btt.style.cssText = `
            position: fixed; bottom: 20px; left: 24px; z-index: 990;
            width: 48px; height: 48px; border-radius: 50%;
            background: var(--navy, #4a8fc8); color: white; border: none;
            font-size: 1.4rem; cursor: pointer; opacity: 0; pointer-events: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: flex; align-items: center; justify-content: center;
        `;
        document.body.appendChild(btt);
        
        window.addEventListener('scroll', () => {
            if(window.scrollY > 400) {
                btt.style.opacity = '1'; 
                btt.style.pointerEvents = 'auto';
                btt.style.transform = 'translateY(0)';
            } else {
                btt.style.opacity = '0'; 
                btt.style.pointerEvents = 'none';
                btt.style.transform = 'translateY(10px)';
            }
        });
        
        btt.addEventListener('click', () => {
            window.scrollTo({top: 0, behavior: 'smooth'});
        });
        
    }

    // Initialize on DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init3D);
    } else {
        init3D();
    }
})();
