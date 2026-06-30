// --- Theme Toggle Logic ---
const themeToggle = document.getElementById('theme-toggle');
themeToggle.addEventListener('click', () => {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    document.body.setAttribute('data-theme', isDark ? 'light' : 'dark');
    themeToggle.innerText = isDark ? '🌙' : '☀️';
    scene.background = new THREE.Color(isDark ? 0xe0e5ec : 0x2a2a2a);
});

// --- Three.js Scene Setup ---
const container = document.getElementById('scene-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe0e5ec);

const aspect = container.clientWidth / container.clientHeight;
const camera = new THREE.PerspectiveCamera(45, aspect, 1, 5000);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
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

// --- Application Logic & Variables ---
let currentMesh = null;
let cachedBlueprint = null;
let currentFilename = "mosaic";

const uploadForm = document.getElementById('upload-form');
const modeSelector = document.getElementById('render-mode');
const inventoryContainer = document.getElementById('inventory-container');
const exportContainer = document.getElementById('export-container');
const inventoryGrid = document.getElementById('inventory-grid');

modeSelector.addEventListener('change', () => {
    if (cachedBlueprint) buildLegoScene(cachedBlueprint);
});

uploadForm.addEventListener('submit', async (e) => {
    // This stops the page from refreshing!
    e.preventDefault();

    const fileInput = document.getElementById('image-input');
    const statusBox = document.getElementById('status');
    const loadingOverlay = document.getElementById('loading-overlay');

    if (fileInput.files.length === 0) return;

    currentFilename = fileInput.files[0].name.split('.')[0];

    statusBox.style.display = 'block';
    inventoryContainer.style.display = 'none';
    exportContainer.style.display = 'none';
    statusBox.innerText = 'Uploading and computing optimization heuristics...';
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

        const origCount = data.mosaic_data.original_count;
        const optCount = data.mosaic_data.optimized_count;
        const savedPercent = (((origCount - optCount) / origCount) * 100).toFixed(1);

        statusBox.innerHTML = `
            <b>Optimization Complete</b><br>
            Original 1x1 Studs: ${origCount}<br>
            Optimized Bricks: ${optCount}<br>
            <span style="color: #2e7d32;">Saved ${origCount - optCount} physical bricks (${savedPercent}%)</span>
        `;

        renderInventory(data.mosaic_data.inventory);
        exportContainer.style.display = 'block';

    } catch (error) {
        statusBox.innerText = 'Error: ' + error.message;
    } finally {
        loadingOverlay.style.display = 'none';
    }
});

function renderInventory(inventory) {
    inventoryContainer.style.display = 'block';
    inventoryGrid.innerHTML = '';

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

    const { width, height, blocks } = blueprint;
    const mode = modeSelector.value;

    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshLambertMaterial({ color: 0xffffff });
    currentMesh = new THREE.InstancedMesh(geometry, material, blocks.length);

    const dummy = new THREE.Object3D();
    const colorObj = new THREE.Color();
    let instanceId = 0;
    const zScale = 4;

    for (const block of blocks) {
        const zLayer = block.z + 1;
        const [b, g, r] = block.color;
        const blockWidth = block.w;

        const posX = (block.x + (blockWidth - 1) / 2) - (width / 2);
        const posY = -(block.y - (height / 2));
        let posZ = 0;

        if (mode === 'solid') {
            const totalDepth = zLayer * zScale;
            posZ = totalDepth / 2;
            dummy.scale.set(blockWidth * 0.95, 0.95, totalDepth);
        } else if (mode === 'floating') {
            posZ = zLayer * zScale;
            dummy.scale.set(blockWidth * 0.95, 0.95, 1.0);
        } else if (mode === 'flat') {
            posZ = 0;
            dummy.scale.set(blockWidth * 0.95, 0.95, 0.5);
        }

        dummy.position.set(posX, posY, posZ);
        dummy.updateMatrix();
        currentMesh.setMatrixAt(instanceId, dummy.matrix);

        colorObj.setRGB(r / 255, g / 255, b / 255);
        currentMesh.setColorAt(instanceId, colorObj);

        instanceId++;
    }

    currentMesh.instanceMatrix.needsUpdate = true;
    currentMesh.instanceColor.needsUpdate = true;
    scene.add(currentMesh);

    camera.position.set(width * 0.8, height * 0.8, width * 1.2);
    controls.target.set(0, 0, 0);
    controls.update();
}

// --- Export Logic (Bonus 3) ---
function downloadFile(blob, filename) {
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

document.getElementById('btn-export-png').addEventListener('click', () => {
    renderer.render(scene, camera);
    const dataURL = renderer.domElement.toDataURL('image/png');

    const link = document.createElement('a');
    link.href = dataURL;
    link.download = `${currentFilename}_3d_snapshot.png`;
    link.click();
});

document.getElementById('btn-export-json').addEventListener('click', () => {
    if (!cachedBlueprint) return;
    const jsonStr = JSON.stringify(cachedBlueprint, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    downloadFile(blob, `${currentFilename}_blueprint.json`);
});

document.getElementById('btn-export-mesh').addEventListener('click', () => {
    if (!currentMesh) return;

    const exporter = new THREE.GLTFExporter();
    exporter.parse(scene, (gltf) => {
        const jsonStr = JSON.stringify(gltf);
        const blob = new Blob([jsonStr], { type: 'text/plain' });
        downloadFile(blob, `${currentFilename}_3d_mesh.gltf`);
    }, { binary: false });
});
