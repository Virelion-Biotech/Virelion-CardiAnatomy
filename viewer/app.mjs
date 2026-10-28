import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { VTKLoader } from 'three/addons/loaders/VTKLoader.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const viewport = document.getElementById('viewport');
const statusNode = document.getElementById('status');
const fileInput = document.getElementById('model-file');
const modelName = document.getElementById('model-name');
const vertexCount = document.getElementById('vertex-count');
const triangleCount = document.getElementById('triangle-count');
const boundsNode = document.getElementById('bounds');
const wireframeToggle = document.getElementById('wireframe');
const axesToggle = document.getElementById('show-axes');

const scene = new THREE.Scene();
scene.background = new THREE.Color('#080f1d');
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10000);
camera.position.set(3.5, 2.6, 4.5);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
viewport.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.075;
controls.target.set(0, 0, 0);

scene.add(new THREE.HemisphereLight(0xcfe6ff, 0x24334b, 2.1));
const keyLight = new THREE.DirectionalLight(0xfff3e6, 2.5);
keyLight.position.set(4, 6, 5);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x7eafff, 1.7);
rimLight.position.set(-4, 1, -4);
scene.add(rimLight);

const axes = new THREE.AxesHelper(1.65);
axes.material.depthTest = false;
axes.renderOrder = 4;
scene.add(axes);

let activeModel = null;
let isWireframe = false;

function setStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.classList.toggle('error', isError);
}

function setMaterialWireframe(object, enabled) {
  object.traverse((child) => {
    if (!child.isMesh || !child.material) return;
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => {
      if ('wireframe' in material) material.wireframe = enabled;
      material.needsUpdate = true;
    });
  });
}

function disposeModel(object) {
  if (!object) return;
  object.traverse((child) => {
    if (!child.isMesh) return;
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material) => {
        if (material.map) material.map.dispose();
        material.dispose();
      });
    }
  });
}

function countGeometry(object) {
  let vertices = 0;
  let triangles = 0;
  object.traverse((child) => {
    if (!child.isMesh || !child.geometry) return;
    const geometry = child.geometry;
    const position = geometry.getAttribute('position');
    if (!position) return;
    vertices += position.count;
    const index = geometry.getIndex();
    triangles += index ? Math.floor(index.count / 3) : Math.floor(position.count / 3);
  });
  return { vertices, triangles };
}

function fitModel(object) {
  const bounds = new THREE.Box3().setFromObject(object);
  if (bounds.isEmpty()) throw new Error('The selected file did not contain a renderable 3D surface.');
  const center = bounds.getCenter(new THREE.Vector3());
  object.position.sub(center);
  const centeredBounds = new THREE.Box3().setFromObject(object);
  const size = centeredBounds.getSize(new THREE.Vector3());
  const maxDimension = Math.max(size.x, size.y, size.z, 0.01);
  const sphere = centeredBounds.getBoundingSphere(new THREE.Sphere());
  const distance = Math.max(maxDimension * 1.9, sphere.radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.15);
  camera.near = Math.max(distance / 5000, 0.001);
  camera.far = Math.max(distance * 100, 100);
  camera.position.set(distance * 0.85, distance * 0.62, distance * 1.05);
  camera.updateProjectionMatrix();
  controls.target.set(0, 0, 0);
  controls.minDistance = maxDimension * 0.01;
  controls.maxDistance = maxDimension * 200;
  controls.update();
  return size;
}

function showModel(object, name, detail) {
  if (activeModel) {
    scene.remove(activeModel);
    disposeModel(activeModel);
  }
  activeModel = object;
  scene.add(activeModel);
  isWireframe = false;
  wireframeToggle.checked = false;
  setMaterialWireframe(activeModel, false);
  const size = fitModel(activeModel);
  const counts = countGeometry(activeModel);
  modelName.textContent = name;
  vertexCount.textContent = counts.vertices.toLocaleString();
  triangleCount.textContent = counts.triangles.toLocaleString();
  boundsNode.textContent = [size.x, size.y, size.z].map((v) => Number(v.toPrecision(4))).join(' × ');
  setStatus(detail);
}

function materialMesh(geometry, color = '#d95e7b') {
  if (!geometry.getAttribute('position') || geometry.getAttribute('position').count < 3) {
    throw new Error('The selected file does not contain a surface mesh.');
  }
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
    color,
    roughness: 0.52,
    metalness: 0.02,
    side: THREE.DoubleSide
  }));
}

function createDemoModel() {
  const group = new THREE.Group();
  group.name = 'Synthetic illustrative biventricular geometry';

  const lvGeometry = new THREE.SphereGeometry(0.68, 72, 56);
  const lvPos = lvGeometry.getAttribute('position');
  for (let i = 0; i < lvPos.count; i += 1) {
    const x = lvPos.getX(i);
    const y = lvPos.getY(i);
    const z = lvPos.getZ(i);
    const taper = 1 - 0.16 * y;
    lvPos.setXYZ(i, x * 0.83 * taper, y * 1.40, z * 0.73 * taper);
  }
  lvGeometry.computeVertexNormals();
  const lv = materialMesh(lvGeometry, '#d95e7b');
  lv.name = 'Illustrative LV';
  lv.position.set(-0.22, -0.02, 0);
  group.add(lv);

  const rvGeometry = new THREE.SphereGeometry(0.53, 64, 48);
  const rvPos = rvGeometry.getAttribute('position');
  for (let i = 0; i < rvPos.count; i += 1) {
    const x = rvPos.getX(i);
    const y = rvPos.getY(i);
    const z = rvPos.getZ(i);
    const taper = 1 - 0.1 * y;
    rvPos.setXYZ(i, x * 0.8, y * 1.24 * taper, z * 0.65);
  }
  rvGeometry.computeVertexNormals();
  const rv = materialMesh(rvGeometry, '#5798d9');
  rv.name = 'Illustrative RV';
  rv.position.set(0.39, -0.1, 0.12);
  rv.rotation.z = -0.12;
  group.add(rv);

  const aortaCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.30, 0.75, 0.02),
    new THREE.Vector3(-0.32, 1.00, 0.02),
    new THREE.Vector3(-0.17, 1.20, 0.02),
    new THREE.Vector3(0.03, 1.17, 0.02),
    new THREE.Vector3(0.09, 0.98, 0.02)
  ]);
  const aorta = materialMesh(new THREE.TubeGeometry(aortaCurve, 48, 0.105, 16, false), '#cf5f59');
  aorta.name = 'Illustrative outflow landmark';
  group.add(aorta);

  const pulmonaryCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.22, 0.73, 0.08),
    new THREE.Vector3(0.30, 0.95, 0.10),
    new THREE.Vector3(0.47, 1.06, 0.10),
    new THREE.Vector3(0.68, 1.04, 0.10)
  ]);
  const pulmonary = materialMesh(new THREE.TubeGeometry(pulmonaryCurve, 40, 0.078, 14, false), '#4b91d5');
  pulmonary.name = 'Illustrative outflow landmark';
  group.add(pulmonary);
  return group;
}

function restoreDemo() {
  const demo = createDemoModel();
  showModel(
    demo,
    'Synthetic teaching mesh',
    'Illustrative synthetic biventricular geometry loaded. It is not patient-derived or anatomically validated.'
  );
}

async function parseFile(file) {
  const extension = file.name.split('.').pop().toLowerCase();
  const buffer = await file.arrayBuffer();
  let object;
  if (extension === 'vtk') {
    const geometry = new VTKLoader().parse(buffer);
    object = materialMesh(geometry, '#b2c9ec');
  } else if (extension === 'stl') {
    object = materialMesh(new STLLoader().parse(buffer), '#d8b5a9');
  } else if (extension === 'ply') {
    const geometry = new PLYLoader().parse(buffer);
    if (!geometry.getAttribute('position')) throw new Error('The PLY file has no vertex positions.');
    geometry.computeVertexNormals();
    const hasColor = Boolean(geometry.getAttribute('color'));
    object = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
      color: hasColor ? '#ffffff' : '#b2c9ec',
      vertexColors: hasColor,
      roughness: 0.6,
      side: THREE.DoubleSide
    }));
  } else if (extension === 'obj') {
    object = new OBJLoader().parse(new TextDecoder().decode(buffer));
    object.traverse((child) => {
      if (!child.isMesh) return;
      if (child.geometry && !child.geometry.getAttribute('normal')) child.geometry.computeVertexNormals();
      if (!child.material) {
        child.material = new THREE.MeshStandardMaterial({
          color: '#b2c9ec', roughness: 0.6, side: THREE.DoubleSide
        });
      }
    });
  } else if (extension === 'glb') {
    const gltf = await new Promise((resolve, reject) => {
      new GLTFLoader().parse(buffer, '', resolve, reject);
    });
    object = gltf.scene;
  } else {
    throw new Error('Unsupported file type. Open a legacy ASCII VTK POLYDATA surface (.vtk), STL, OBJ, PLY, or GLB file. Volume meshes must first be converted to their exterior surface.');
  }
  return object;
}

async function handleFile(file) {
  if (!file) return;
  setStatus('Reading ' + file.name + ' locally…');
  try {
    const object = await parseFile(file);
    showModel(object, file.name, 'Loaded locally in this browser. Coordinates and file units are preserved; anatomical meaning is not inferred.');
  } catch (error) {
    setStatus(error instanceof Error ? error.message : 'Could not read this model.', true);
  }
}

fileInput.addEventListener('change', async (event) => {
  const file = event.target.files && event.target.files[0];
  await handleFile(file);
  fileInput.value = '';
});

document.getElementById('load-demo').addEventListener('click', restoreDemo);
document.getElementById('reset-camera').addEventListener('click', () => {
  if (activeModel) fitModel(activeModel);
});
wireframeToggle.addEventListener('change', () => {
  isWireframe = wireframeToggle.checked;
  if (activeModel) setMaterialWireframe(activeModel, isWireframe);
});
axesToggle.addEventListener('change', () => { axes.visible = axesToggle.checked; });
document.getElementById('save-image').addEventListener('click', () => {
  renderer.domElement.toBlob((blob) => {
    if (!blob) {
      setStatus('Could not export the viewport image. Try another browser.', true);
      return;
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'cardianatomy-3d-view.png';
    link.click();
    URL.revokeObjectURL(url);
    setStatus('Viewport image exported as PNG.');
  }, 'image/png');
});

const dropzone = document.getElementById('dropzone');
dropzone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropzone.classList.add('dragging');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragging'));
dropzone.addEventListener('drop', async (event) => {
  event.preventDefault();
  dropzone.classList.remove('dragging');
  const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
  await handleFile(file);
});

function resize() {
  const width = Math.max(viewport.clientWidth, 1);
  const height = Math.max(viewport.clientHeight, 1);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}
const resizeObserver = new ResizeObserver(resize);
resizeObserver.observe(viewport);
window.addEventListener('beforeunload', () => {
  resizeObserver.disconnect();
  controls.dispose();
  renderer.dispose();
});
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
resize();
restoreDemo();
animate();
