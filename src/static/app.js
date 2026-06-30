// --- Theme Toggle Logic ---
const themeToggle = document.getElementById('theme-toggle');
themeToggle.addEventListener('click', () => {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    document.body.setAttribute('data-theme', isDark ? 'light' : 'dark');
    themeToggle.innerText = isDark ? '🌙' : '☀️';

    // Update Three.js background to match theme
    scene.background = new THREE.Color(isDark ? 0xe0e5ec : 0x2a2a2a);
});

// --- Three.js Scene Setup ---
const container = document.getElementById('scene-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe0e5ec);

const aspect = container.clientWidth / container.clientHeight;
const camera = new THREE.PerspectiveCamera(45, aspect, 1, 5000);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);
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

// --- Application Logic ---
let currentMesh = null;
let cachedBlueprint = null;

const uploadForm = document.getElementById('upload-form');
const modeSelector = document.getElementById('render-mode');
const inventoryContainer = document.getElementById('inventory-container');
const inventoryGrid = document.getElementById('inventory-grid');

modeSelector.addEventListener('change', () => {
    if (cachedBlueprint) buildLegoScene(cachedBlueprint);
});

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById('image-input');
    const statusBox = document.getElementById('status');
    const loadingOverlay = document.getElementById('loading-overlay');

    if (fileInput.files.length === 0) return;

    statusBox.style.display = 'block';
    inventoryContainer.style.display = 'none';
    statusBox.innerText = 'Uploading and computing heuristics...';
    loadingOverlay.style.display = 'flex';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || 'Processing failed');

        const rawPath = data.mosaic_data.scene_data;
        const filename = rawPath.split('/').pop();
        const sceneDataPath = '/outputs/' + filename;

        const blueprintRes = await fetch(sceneDataPath);
        if (!blueprintRes.ok) throw new Error('Failed to fetch 3D blueprint data.');

        cachedBlueprint = await blueprintRes.json();
        buildLegoScene(cachedBlueprint);

        // Update Status Box
        const total = cachedBlueprint.width * cachedBlueprint.height;
        const layers = data.mosaic_data.layers;
        statusBox.innerText = `Done — ${total} studs, ${layers} depth layers, backend: luminance + edge heuristic.`;

        // Render Inventory
        renderInventory(data.mosaic_data.inventory);

    } catch (error) {
        statusBox.innerText = 'Error: ' + error.message;
    } finally {
        loadingOverlay.style.display = 'none';
    }
});

function renderInventory(inventory) {
    inventoryContainer.style.display = 'block';
    inventoryGrid.innerHTML = ''; // Clear previous

    inventory.forEach(item => {
        const div = document.createElement('div');
        div.className = 'inventory-item';
        div.innerHTML = `
            <div class="color-swatch" style="background-color: ${item.hex};"></div>
            <span>${item.name} <b>×${item.count}</b></span>
        `;
        inventoryGrid.appendChild(div);
    });
}

function buildLegoScene(blueprint) {
    if (currentMesh) {
        scene.remove(currentMesh);
        currentMesh.dispose();
    }

    const { width, height, layers, colors } = blueprint;
    const totalBlocks = width * height;
    const mode = modeSelector.value;

    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshLambertMaterial({ color: 0xffffff });
    currentMesh = new THREE.InstancedMesh(geometry, material, totalBlocks);

    const dummy = new THREE.Object3D();
    const colorObj = new THREE.Color();
    let instanceId = 0;
    const zScale = 4;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const zLayer = layers[y][x] + 1;
            const [b, g, r] = colors[y * width + x];

            const posX = x - (width / 2);
            const posY = -(y - (height / 2));
            let posZ = 0;

            if (mode === 'solid') {
                const totalDepth = zLayer * zScale;
                posZ = totalDepth / 2;
                dummy.scale.set(0.95, 0.95, totalDepth);
            } else if (mode === 'floating') {
                posZ = zLayer * zScale;
                dummy.scale.set(0.9, 0.9, 1.0);
            } else if (mode === 'flat') {
                posZ = 0;
                dummy.scale.set(0.95, 0.95, 0.5);
            }

            dummy.position.set(posX, posY, posZ);
            dummy.updateMatrix();
            currentMesh.setMatrixAt(instanceId, dummy.matrix);

            colorObj.setRGB(r / 255, g / 255, b / 255);
            currentMesh.setColorAt(instanceId, colorObj);

            instanceId++;
        }
    }

    currentMesh.instanceMatrix.needsUpdate = true;
    currentMesh.instanceColor.needsUpdate = true;
    scene.add(currentMesh);

    camera.position.set(width * 0.8, height * 0.8, width * 1.2);
    controls.target.set(0, 0, 0);
    controls.update();
}
