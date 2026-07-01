// Global variables for Three.js so they remain accessible everywhere
let scene, camera, renderer, controls;
let currentMesh = null;
let cachedBlueprint = null;
let currentFilename = "mosaic";

document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Toggle ---
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle.addEventListener('click', () => {
        const isDark = document.body.getAttribute('data-theme') === 'dark';
        document.body.setAttribute('data-theme', isDark ? 'light' : 'dark');
        themeToggle.innerText = isDark ? '🌙' : '☀️';
        if (scene) scene.background = new THREE.Color(isDark ? 0xe0e5ec : 0x2a2a2a);
    });

    // --- Three.js Setup ---
    const container = document.getElementById('scene-container');
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xe0e5ec);

    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(45, aspect, 1, 5000);

    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(200, 300, 400);
    scene.add(dirLight);

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });

    // --- Dynamic Slider Values & Reset Logic ---
    const inputLayers = document.getElementById('input-layers');
    const valLayers = document.getElementById('val-layers');
    const inputStuds = document.getElementById('input-studs');
    const valStuds = document.getElementById('val-studs');
    const btnReset = document.getElementById('btn-reset-sliders');

    if (inputLayers && valLayers) {
        inputLayers.addEventListener('input', (e) => { valLayers.innerText = e.target.value; });
    }
    if (inputStuds && valStuds) {
        inputStuds.addEventListener('input', (e) => { valStuds.innerText = e.target.value; });
    }

    if (btnReset) {
        btnReset.addEventListener('click', () => {
            inputLayers.value = 6;
            valLayers.innerText = '6';
            inputStuds.value = 48;
            valStuds.innerText = '48';
        });
    }

    // --- App Logic ---
    const uploadForm = document.getElementById('upload-form');
    const modeSelector = document.getElementById('render-mode');
    const inventoryContainer = document.getElementById('inventory-container');
    const exportContainer = document.getElementById('export-container');
    const statusBox = document.getElementById('status');
    const loadOverlay = document.getElementById('loading-overlay');
    const fileInput = document.getElementById('image-input');

    if (modeSelector) {
        modeSelector.addEventListener('change', () => {
            if (cachedBlueprint) buildLegoScene(cachedBlueprint);
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (fileInput.files.length === 0) return;
            currentFilename = fileInput.files[0].name.split('.')[0];

            // Explicitly show the status box during loading
            statusBox.style.display = 'block';
            statusBox.style.color = "var(--text-main)";
            inventoryContainer.style.display = 'none';
            exportContainer.style.display = 'none';
            statusBox.innerText = 'Uploading and computing heuristics...';
            loadOverlay.style.display = 'flex';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('depth_layers', inputLayers.value);
            formData.append('max_studs', inputStuds.value);

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();

                if (!res.ok) throw new Error(data.detail || 'Processing failed');

                const rawPath = data.mosaic_data.scene_data;
                const blueprintRes = await fetch('/outputs/' + rawPath.split('/').pop());

                if (!blueprintRes.ok) throw new Error('Failed to fetch 3D data.');

                cachedBlueprint = await blueprintRes.json();
                buildLegoScene(cachedBlueprint);

                // Populate the Status box with correct success metrics
                const studs = data.mosaic_data.original_count || 0;
                const layers = data.mosaic_data.layers || inputLayers.value;

                statusBox.innerHTML = `
                    <span style="color: #2e7d32;">
                        Done - ${studs} studs, ${layers} depth layers, depth backend: luminance + edge heuristic.
                    </span>
                `;

                renderInventory(data.mosaic_data.inventory);
                exportContainer.style.display = 'block';

            } catch (err) {
                // Ensure the status box remains visible to show the error
                statusBox.style.display = 'block';
                statusBox.innerHTML = `<span style="color: #d32f2f;">Error: ${err.message}</span>`;
            } finally {
                loadOverlay.style.display = 'none';
            }
        });
    }

    // --- Export Logic ---
    function downloadFile(blob, filename) {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    }

    document.getElementById('btn-export-png').addEventListener('click', () => {
        renderer.render(scene, camera);
        const link = document.createElement('a');
        link.href = renderer.domElement.toDataURL('image/png');
        link.download = `${currentFilename}_3d_snapshot.png`;
        link.click();
    });

    document.getElementById('btn-export-json').addEventListener('click', () => {
        if (!cachedBlueprint) return;
        const blob = new Blob([JSON.stringify(cachedBlueprint, null, 2)], { type: 'application/json' });
        downloadFile(blob, `${currentFilename}_blueprint.json`);
    });

    document.getElementById('btn-export-mesh').addEventListener('click', () => {
        if (!currentMesh) return;
        new THREE.GLTFExporter().parse(scene, (gltf) => {
            const blob = new Blob([JSON.stringify(gltf)], { type: 'text/plain' });
            downloadFile(blob, `${currentFilename}_3d_mesh.gltf`);
        }, { binary: false });
    });
});

function renderInventory(inventory) {
    const inventoryContainer = document.getElementById('inventory-container');
    const grid = document.getElementById('inventory-grid');
    if (!inventoryContainer || !grid) return;

    inventoryContainer.style.display = 'block';
    grid.innerHTML = '';

    inventory.forEach(item => {
        const div = document.createElement('div');
        div.className = 'inventory-item';
        div.innerHTML = `
            <div class="color-swatch" style="background-color: ${item.hex};"></div>
            <span>${item.name} <b>×${item.count}</b></span>
        `;
        grid.appendChild(div);
    });
}

function buildLegoScene(blueprint) {
    const modeSelector = document.getElementById('render-mode');

    if (currentMesh) {
        scene.remove(currentMesh);
        currentMesh.dispose();
    }

    const { width, height, blocks } = blueprint;
    const mode = modeSelector ? modeSelector.value : 'solid';

    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshLambertMaterial({ color: 0xffffff });
    currentMesh = new THREE.InstancedMesh(geo, mat, blocks.length);

    const dummy = new THREE.Object3D();
    const col = new THREE.Color();
    const zScale = 4;

    blocks.forEach((block, id) => {
        const zLayer = block.z + 1;
        const posX = (block.x + (block.w - 1) / 2) - (width / 2);
        const posY = -(block.y - (height / 2));
        let posZ = 0;

        if (mode === 'solid') {
            const depth = zLayer * zScale;
            posZ = depth / 2;
            dummy.scale.set(block.w * 0.95, 0.95, depth);
        } else if (mode === 'floating') {
            posZ = zLayer * zScale;
            dummy.scale.set(block.w * 0.95, 0.95, 1.0);
        } else {
            posZ = 0;
            dummy.scale.set(block.w * 0.95, 0.95, 0.5);
        }

        dummy.position.set(posX, posY, posZ);
        dummy.updateMatrix();
        currentMesh.setMatrixAt(id, dummy.matrix);

        col.setRGB(block.color[0]/255, block.color[1]/255, block.color[2]/255);
        currentMesh.setColorAt(id, col);
    });

    currentMesh.instanceMatrix.needsUpdate = true;
    currentMesh.instanceColor.needsUpdate = true;
    scene.add(currentMesh);

    camera.position.set(width * 0.8, height * 0.8, width * 1.2);
    controls.target.set(0, 0, 0);
    controls.update();
}
