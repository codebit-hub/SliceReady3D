*This project has been created as part of the 42 curriculum by dporhomo.*

# SliceReady3D: 2D to 3D LEGO Voxel Constructor

## Description
**Goal:** To build a full-stack web application that transforms a flat 2D image into an interactive, 3D LEGO-style web scene.

**Overview:** SliceReady3D is an end-to-end pipeline that takes user-uploaded images and estimates their physical depth using a custom, lightweight OpenCV heuristic. The pipeline collapses this continuous depth map into discrete spatial layers, repaints the image strictly using an official LEGO color palette (via Euclidean distance color quantization), and optimizes the resulting 1x1 studs into larger, efficient LEGO bricks. The final output is served to the frontend as a highly interactive, rotatable 3D instanced mesh using Three.js, complete with layer-by-layer assembly guides and 3D mesh export capabilities.

---

## Features

### Mandatory Features
* **Robust Image Upload:** Accepts PNG, JPEG, and WEBP formats with strict 5MB size validation and graceful error handling.
* **Local Depth Estimation:** Extracts luminance and edge gradients to build a coherent depth map without relying on heavy ML models.
* **Depth Layer Extraction:** Collapses the continuous depth map into user-defined discrete layers (3 to 10).
* **LEGO Color Quantization:** Maps every pixel to the nearest valid color in an official LEGO palette.
* **Interactive 3D UI:** A fully responsive web interface where users can rotate, pan, and zoom around the generated 3D volume.
* **Seamless UX:** Real-time UI updates, dynamic status boxes detailing stud/brick counts, and asynchronous loading states.

### Bonus Features Implemented
* **Bonus 1 (Real-World Instructions):** Generates a layer-by-layer, step-by-step 2D visual assembly guide natively in the browser, optimized for PDF printing. Includes a full parts inventory.
* **Bonus 2 (Brick Optimization):** Implements a greedy 1D meshing algorithm to merge adjacent identical 1x1 studs into larger bricks (up to 1x8), drastically cutting down the physical brick count.
* **Bonus 3 (Scene Export):** Allows the user to download the generated geometry as a standard GLTF 3D mesh (ready for PrusaSlicer/Blender), a JSON blueprint, and a PNG snapshot.
* **Bonus 4 (Artistic Modes):** Includes switchable render modes: Solid Voxel Sculpture, Floating 2.5D Heightmap, and Traditional Flat Mosaic.

### Incomplete / Future Work
* **Bonus 5 (Built-in AI Image Generator):** I attempted to integrate the Hugging Face Inference API (`stable-diffusion-xl-base-1.0`) to allow text-to-image generation prior to LEGO-fication. While the standalone Python test script successfully connected via a local `.env` token, the feature was intentionally omitted from the core FastAPI application. Free-tier inference APIs suffer from severe "cold start" timeouts (often taking minutes to load model weights into VRAM), which posed an unacceptable risk of hanging the web application during evaluation. Upgrading to a dedicated, always-on inference endpoint would make this viable in the future.

---

## Technical Choices
Given the hardware constraints of the development environment (Ubuntu, 4GB RAM), the architecture prioritizes performance, strict typing, and memory efficiency:
1. **Backend (Python / FastAPI):** Selected for its speed, robust file handling, and clean MVC separation. All Python code strictly adheres to PEP 8 standards and MyPy static typing.
2. **Depth Processing (OpenCV):** Instead of using a memory-heavy monocular depth ML model (like MiDaS), depth is calculated using a local `cv2.Sobel` edge and luminance heuristic. This guarantees instant generation times without out-of-memory crashes.
3. **Frontend Rendering (Three.js `InstancedMesh`):** Rather than rendering thousands of individual 3D box geometries (which destroys browser framerates), the scene uses a single `InstancedMesh` to render the entire mosaic in one draw call, keeping the UI highly responsive.

---

## Instructions (Compilation & Execution)

### Prerequisites
* Python 3
* `pip` and `venv` (Virtual Environments)

### Installation
1. Clone the repository and navigate to the project root.
2. Install the required Python dependencies in a new virtual environment that will be created in the parent directory ../.venv:
```bash
make install
```

### Running the App End-to-End

1. Launch the FastAPI development server:
```bash
make run
```
#### Expected Operation

Running 'make run' starts the web server, which makes the operation of the web application at the specified URL possible. When you finish using the web application, return to the terminal, press Ctr+C to abort its operation.

```bash
make run

Starting SliceReady3D development server...
../.venv/bin/uvicorn src.main:app --reload
INFO:     Will watch for changes in these directories: ['/data/PROJECTS/ML03/BrickDepth/Code_']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [345171] using WatchFiles
INFO:     Started server process [345173]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:36220 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:36230 - "POST /api/upload HTTP/1.1" 200 OK
INFO:     127.0.0.1:36230 - "GET /outputs/01_radial_gradient_data.json HTTP/1.1" 200 OK
[Triggerred termination of the server by pressing CTRL+C]^C
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [345173]
INFO:     Stopping reloader process [345171]

```


2. Open a modern web browser and navigate to the URL provided by Uvicorn

    (`http://127.0.0.1:8000`).

3. **Usage Example:**
* On the left sidebar, click "Upload Image" and select a small test PNG/JPG.
* Adjust the "Depth layers" and "Studs" sliders if desired.
* Click the red **Build Mosaic** button.
* The status box will appear detailing the optimization metrics (e.g., "Done - 2304 studs, 6 depth layers...").
* The 3D scene will appear in the main container. Use your mouse to rotate (left-click drag), pan (right-click drag), and zoom (scroll).
* Explore the export options or print the assembly guide using the buttons in the sidebar.



---

## External Services & Libraries Used

* **Depth Estimator:** Custom OpenCV luminance/edge heuristic (No external API or credentials required).
* **3D Library:** Three.js (Served via CDN in `index.html`).
* **Image Generator (Tested for Bonus 5):** Hugging Face Inference API (`stabilityai/stable-diffusion-xl-base-1.0`). Requires an `HF_API_TOKEN` set in a local `.env` file to run the isolated `hf_test.py` script. In development - not submitted with this project.

---

## Team Work Split

* **dporhomo:** As a solo developer on this project, I architected and implemented the entire end-to-end pipeline. This includes the FastAPI backend controller, the OpenCV depth/quantization mathematical logic, the 1D greedy meshing optimization algorithm, the HTML/CSS user interface, and the Three.js 3D rendering integration.

---

## Resources & AI Usage

**Classic References:**

* [FastAPI Documentation](https://fastapi.tiangolo.com/)
* [Three.js InstancedMesh Documentation](https://threejs.org/docs/#api/en/objects/InstancedMesh)
* [OpenCV Python Tutorials](https://www.google.com/search?q=https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)

**AI Partner (Gemini 3.1 Pro):**
This project was developed with an AI co-pilot. The AI was utilized to:

1. Brainstorm lightweight alternatives to heavy ML depth models.
2. Draft boilerplate for the Three.js `InstancedMesh` setup and GLTF exporting logic.
3. Help debug a JavaScript race condition (`DOMContentLoaded`) where UI sliders failed to attach event listeners.
4. Refactor and enforce strict PEP 8 and MyPy type-hinting across the Python backend to meet submission standards.
