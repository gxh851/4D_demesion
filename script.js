// script.js - 根据用户输入动态生成不同场景
let scene, camera, renderer, controls;
let currentGroup = null;
let currentTheme = 'garden';
let isDynamicView = false;
let dynamicAngle = 0;
let animationObjects = [];
let currentTime = 0;

// 不同场景的配置
const sceneConfigs = {
    garden: {
        name: '🌸 感官花园',
        task: '识别花朵颜色，观察蝴蝶飞舞，放松呼吸',
        groundColor: 0x3a8a5a,
        backgroundColor: 0x1a4a3a,
        buildings: [],
        trees: [
            { x: -2.5, z: -2, color: 0x5a9a4a },
            { x: 2.5, z: -2, color: 0x5a9a4a },
            { x: -2, z: 2, color: 0x4a8a3a },
            { x: 2, z: 2, color: 0x4a8a3a }
        ],
        flowers: [
            { x: -1, z: 0.5, color: 0xff6b9d },
            { x: 0, z: 1, color: 0xffaa44 },
            { x: 1, z: 0.5, color: 0xdd88ff },
            { x: -0.5, z: -1, color: 0xff8888 },
            { x: 0.5, z: -1.2, color: 0x88ffaa }
        ],
        specialObjects: [
            { type: 'butterfly', x: 0, z: 0 }
        ]
    },
    bus: {
        name: '🚌 公交车社交场景',
        task: '排队上车，学会刷卡并找座位',
        groundColor: 0x5a6a6a,
        backgroundColor: 0x2a4a5a,
        buildings: [],
        trees: [],
        flowers: [],
        specialObjects: [
            { type: 'bus', x: 0, z: 0, color: 0xdd4444 },
            { type: 'stopSign', x: -3, z: 0.5, color: 0xffaa33 },
            { type: 'person', x: -2, z: 1, color: 0x88aaff, role: 'waiting' },
            { type: 'person', x: -1.5, z: 1.2, color: 0xffaa88, role: 'waiting' },
            { type: 'person', x: -1, z: 1.4, color: 0xaaffaa, role: 'waiting' }
        ]
    },
    park: {
        name: '🌳 公园互动场景',
        task: '与小朋友一起玩滑梯，学会轮流等待',
        groundColor: 0x4a8a5a,
        backgroundColor: 0x2a5a3a,
        buildings: [],
        trees: [
            { x: -3, z: -2, color: 0x5a9a4a },
            { x: 3, z: -2, color: 0x5a9a4a },
            { x: -2.5, z: 2, color: 0x4a8a3a },
            { x: 2.5, z: 2, color: 0x4a8a3a }
        ],
        flowers: [
            { x: -1.5, z: 1, color: 0xff8888 },
            { x: 1.5, z: 1, color: 0xffaa66 },
            { x: 0, z: 1.8, color: 0xff66aa }
        ],
        specialObjects: [
            { type: 'slide', x: 0, z: -1.5, color: 0xcc8844 },
            { type: 'swing', x: 2, z: 1, color: 0xaa8866 },
            { type: 'person', x: -1, z: -0.5, color: 0xffaaaa, role: 'playing' },
            { type: 'person', x: 1, z: -0.8, color: 0xaaffaa, role: 'waiting' }
        ]
    },
    supermarket: {
        name: '🛒 超市购物场景',
        task: '按清单拿取苹果、牛奶，学习购物礼仪',
        groundColor: 0x6a6a6a,
        backgroundColor: 0x3a4a4a,
        buildings: [],
        trees: [],
        flowers: [],
        specialObjects: [
            { type: 'shelf', x: -2, z: -1, color: 0xaa8866, width: 1.2, height: 0.8 },
            { type: 'shelf', x: 2, z: -1, color: 0xaa8866, width: 1.2, height: 0.8 },
            { type: 'shelf', x: 0, z: -1.8, color: 0xaa8866, width: 1.5, height: 0.8 },
            { type: 'cart', x: -1, z: 1.5, color: 0x6688aa },
            { type: 'fruit', x: -2, z: -0.8, color: 0xff4444 },
            { type: 'fruit', x: 2, z: -0.8, color: 0x44ff44 },
            { type: 'person', x: 0.5, z: 1.2, color: 0x88aaff, role: 'shopping' }
        ]
    },
    classroom: {
        name: '📚 教室集体场景',
        task: '听从老师指令，安坐与举手回答问题',
        groundColor: 0x6a7a8a,
        backgroundColor: 0x3a4a5a,
        buildings: [],
        trees: [],
        flowers: [],
        specialObjects: [
            { type: 'desk', x: -1.5, z: -0.5, color: 0xccaa77 },
            { type: 'desk', x: 0, z: -0.5, color: 0xccaa77 },
            { type: 'desk', x: 1.5, z: -0.5, color: 0xccaa77 },
            { type: 'teacher', x: 0, z: -2, color: 0xffaa77 },
            { type: 'blackboard', x: 0, z: -2.8, color: 0x334455 },
            { type: 'person', x: -1.5, z: 0.2, color: 0x88aaff, role: 'student' },
            { type: 'person', x: 0, z: 0.2, color: 0xaaffaa, role: 'student' },
            { type: 'person', x: 1.5, z: 0.2, color: 0xffaa88, role: 'student' }
        ]
    }
};

// 初始化Three.js
function initThree() {
    const container = document.getElementById('canvasContainer');
    if (!container) return;
    const width = container.clientWidth;
    const height = 320;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a4a3a);
    scene.fog = new THREE.FogExp2(0x1a4a3a, 0.02);

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(5, 4, 6);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0.5, 0);

    // 灯光
    const ambient = new THREE.AmbientLight(0x404060);
    scene.add(ambient);
    const mainLight = new THREE.DirectionalLight(0xffffff, 1);
    mainLight.position.set(5, 10, 7);
    mainLight.castShadow = true;
    scene.add(mainLight);
    const fillLight = new THREE.PointLight(0x4466cc, 0.3);
    fillLight.position.set(-2, 3, 4);
    scene.add(fillLight);
    const backLight = new THREE.PointLight(0xffaa66, 0.2);
    backLight.position.set(0, 2, -3);
    scene.add(backLight);

    animate();
}

function animate() {
    requestAnimationFrame(animate);

    // 更新动画
    if (animationObjects.length > 0) {
        animationObjects.forEach(obj => {
            if (obj.update) obj.update();
        });
    }

    if (controls) controls.update();
    if (isDynamicView && camera) {
        dynamicAngle += 0.005;
        const radius = 6;
        camera.position.x = Math.sin(dynamicAngle) * radius;
        camera.position.z = Math.cos(dynamicAngle) * radius;
        camera.position.y = 3;
        controls.target.set(0, 0.5, 0);
        controls.update();
    }
    if (renderer && scene && camera) renderer.render(scene, camera);
}

// 根据主题构建场景
function buildScene(themeKey) {
    if (!scene) initThree();
    if (currentGroup) scene.remove(currentGroup);
    animationObjects = [];

    const config = sceneConfigs[themeKey] || sceneConfigs.garden;
    currentTheme = themeKey;
    scene.background = new THREE.Color(config.backgroundColor);
    if (scene.fog) scene.fog.color = new THREE.Color(config.backgroundColor);

    const group = new THREE.Group();

    // 地面
    const ground = new THREE.Mesh(
        new THREE.CircleGeometry(7, 32),
        new THREE.MeshStandardMaterial({ color: config.groundColor, roughness: 0.7, metalness: 0.1 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.2;
    ground.receiveShadow = true;
    group.add(ground);

    // 草地装饰
    const grassMat = new THREE.MeshStandardMaterial({ color: 0x5a9a4a });
    for (let i = 0; i < 60; i++) {
        const blade = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 0.1, 3), grassMat);
        const angle = Math.random() * Math.PI * 2;
        const rad = 2 + Math.random() * 4.5;
        blade.position.x = Math.cos(angle) * rad;
        blade.position.z = Math.sin(angle) * rad;
        blade.position.y = -0.15;
        group.add(blade);
    }

    // 添加树木
    if (config.trees) {
        config.trees.forEach(tree => {
            const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.35, 0.6, 6), new THREE.MeshStandardMaterial({ color: 0xaa8866 }));
            trunk.position.y = 0.2;
            const foliage = new THREE.Mesh(new THREE.ConeGeometry(0.45, 0.7, 8), new THREE.MeshStandardMaterial({ color: tree.color }));
            foliage.position.y = 0.55;
            const treeGroup = new THREE.Group();
            treeGroup.add(trunk);
            treeGroup.add(foliage);
            treeGroup.position.set(tree.x, -0.1, tree.z);
            group.add(treeGroup);
        });
    }

    // 添加花朵
    if (config.flowers) {
        config.flowers.forEach(flower => {
            const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.25, 4), new THREE.MeshStandardMaterial({ color: 0x5a8a3a }));
            stem.position.y = 0.1;
            const head = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8), new THREE.MeshStandardMaterial({ color: flower.color }));
            head.position.y = 0.25;
            const flowerGroup = new THREE.Group();
            flowerGroup.add(stem);
            flowerGroup.add(head);
            flowerGroup.position.set(flower.x, -0.15, flower.z);
            group.add(flowerGroup);
        });
    }

    // 添加特殊物体
    if (config.specialObjects) {
        config.specialObjects.forEach(obj => {
            let mesh;
            switch(obj.type) {
                case 'bus':
                    const body = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.7, 0.9), new THREE.MeshStandardMaterial({ color: obj.color }));
                    body.position.y = 0.2;
                    const roof = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.2, 0.85), new THREE.MeshStandardMaterial({ color: 0xdddddd }));
                    roof.position.y = 0.6;
                    const wheels = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.1, 8), new THREE.MeshStandardMaterial({ color: 0x333333 }));
                    wheels.rotation.z = Math.PI / 2;
                    wheels.position.set(0.5, 0, 0.5);
                    const busGroup = new THREE.Group();
                    busGroup.add(body);
                    busGroup.add(roof);
                    busGroup.add(wheels.clone().position.set(0.5, -0.05, 0.5));
                    busGroup.add(wheels.clone().position.set(-0.5, -0.05, 0.5));
                    busGroup.add(wheels.clone().position.set(0.5, -0.05, -0.5));
                    busGroup.add(wheels.clone().position.set(-0.5, -0.05, -0.5));
                    busGroup.position.set(obj.x, -0.1, obj.z);
                    mesh = busGroup;
                    break;
                case 'person':
                    const bodyP = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.45, 6), new THREE.MeshStandardMaterial({ color: obj.color }));
                    bodyP.position.y = 0.22;
                    const headP = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16), new THREE.MeshStandardMaterial({ color: 0xffddbb }));
                    headP.position.y = 0.5;
                    const personGroup = new THREE.Group();
                    personGroup.add(bodyP);
                    personGroup.add(headP);
                    personGroup.position.set(obj.x, -0.15, obj.z);
                    mesh = personGroup;
                    break;
                case 'slide':
                    const base = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.1, 1.0), new THREE.MeshStandardMaterial({ color: obj.color }));
                    base.position.y = 0.05;
                    const ramp = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.9), new THREE.MeshStandardMaterial({ color: 0xdd8844 }));
                    ramp.position.set(0, 0.35, -0.25);
                    ramp.rotation.x = 0.5;
                    const slideGroup = new THREE.Group();
                    slideGroup.add(base);
                    slideGroup.add(ramp);
                    slideGroup.position.set(obj.x, -0.15, obj.z);
                    mesh = slideGroup;
                    break;
                case 'swing':
                    const frame = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.0, 0.8), new THREE.MeshStandardMaterial({ color: 0xaa8866 }));
                    frame.position.y = 0.4;
                    const seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.3), new THREE.MeshStandardMaterial({ color: 0xccaa77 }));
                    seat.position.y = 0.15;
                    const swingGroup = new THREE.Group();
                    swingGroup.add(frame);
                    swingGroup.add(seat);
                    swingGroup.position.set(obj.x, -0.1, obj.z);
                    mesh = swingGroup;
                    break;
                case 'shelf':
                    const shelfBody = new THREE.Mesh(new THREE.BoxGeometry(obj.width || 1.0, obj.height || 0.7, 0.4), new THREE.MeshStandardMaterial({ color: obj.color }));
                    shelfBody.position.y = 0.2;
                    const shelfGroup = new THREE.Group();
                    shelfGroup.add(shelfBody);
                    shelfGroup.position.set(obj.x, -0.1, obj.z);
                    mesh = shelfGroup;
                    break;
                case 'cart':
                    const cartBody = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.3, 0.6), new THREE.MeshStandardMaterial({ color: obj.color }));
                    cartBody.position.y = 0.1;
                    const cartGroup = new THREE.Group();
                    cartGroup.add(cartBody);
                    cartGroup.position.set(obj.x, -0.15, obj.z);
                    mesh = cartGroup;
                    break;
                case 'fruit':
                    const fruit = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8), new THREE.MeshStandardMaterial({ color: obj.color }));
                    fruit.position.y = 0.05;
                    const fruitGroup = new THREE.Group();
                    fruitGroup.add(fruit);
                    fruitGroup.position.set(obj.x, -0.1, obj.z);
                    mesh = fruitGroup;
                    break;
                case 'desk':
                    const deskTop = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.08, 0.5), new THREE.MeshStandardMaterial({ color: obj.color }));
                    deskTop.position.y = 0.15;
                    const deskLeg = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.2, 0.08), new THREE.MeshStandardMaterial({ color: 0x886644 }));
                    deskLeg.position.y = 0;
                    const deskGroup = new THREE.Group();
                    deskGroup.add(deskTop);
                    deskGroup.add(deskLeg.clone().position.set(0.25, 0, 0.2));
                    deskGroup.add(deskLeg.clone().position.set(-0.25, 0, 0.2));
                    deskGroup.add(deskLeg.clone().position.set(0.25, 0, -0.2));
                    deskGroup.add(deskLeg.clone().position.set(-0.25, 0, -0.2));
                    deskGroup.position.set(obj.x, -0.15, obj.z);
                    mesh = deskGroup;
                    break;
                case 'teacher':
                    const teacherBody = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.5, 6), new THREE.MeshStandardMaterial({ color: obj.color }));
                    teacherBody.position.y = 0.25;
                    const teacherHead = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16), new THREE.MeshStandardMaterial({ color: 0xffddbb }));
                    teacherHead.position.y = 0.55;
                    const teacherGroup = new THREE.Group();
                    teacherGroup.add(teacherBody);
                    teacherGroup.add(teacherHead);
                    teacherGroup.position.set(obj.x, -0.15, obj.z);
                    mesh = teacherGroup;
                    break;
                case 'blackboard':
                    const board = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.8, 0.08), new THREE.MeshStandardMaterial({ color: obj.color, emissive: 0x112233 }));
                    board.position.y = 0.3;
                    const boardGroup = new THREE.Group();
                    boardGroup.add(board);
                    boardGroup.position.set(obj.x, 0, obj.z);
                    mesh = boardGroup;
                    break;
                default:
                    mesh = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.4, 0.4), new THREE.MeshStandardMaterial({ color: obj.color }));
                    mesh.position.set(obj.x, 0, obj.z);
            }
            if (mesh) {
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                group.add(mesh);
            }
        });
    }

    // 添加动态小球（通用动画）
    const movingBall = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 16),
        new THREE.MeshStandardMaterial({ color: 0xff6666, emissive: 0x441111 })
    );
    movingBall.castShadow = true;
    group.add(movingBall);
    let ballX = 0, ballDir = 0.02;
    animationObjects.push({
        update: () => {
            ballX += ballDir;
            if (ballX > 2.2) ballDir = -0.02;
            if (ballX < -2.2) ballDir = 0.02;
            movingBall.position.set(ballX, 0.2, 1.8);
        }
    });

    // 添加旋转装饰
    const starGroup = new THREE.Group();
    for (let i = 0; i < 5; i++) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.4, 0.08), new THREE.MeshStandardMaterial({ color: 0xffdd88 }));
        const angle = (i / 5) * Math.PI * 2;
        arm.position.set(Math.cos(angle) * 0.45, 0, Math.sin(angle) * 0.45);
        starGroup.add(arm);
    }
    starGroup.position.set(1.8, 0.7, -1.5);
    group.add(starGroup);
    let starRot = 0;
    animationObjects.push({
        update: () => {
            starRot += 0.025;
            starGroup.rotation.y = starRot;
        }
    });

    scene.add(group);
    currentGroup = group;

    // 更新UI
    document.getElementById('sceneNameDisplay').innerHTML = `<i class="fas fa-cube"></i> ${config.name} | 4D动态场景`;
    document.getElementById('currentTaskDesc').innerHTML = `🎯 ${config.task}`;
    document.getElementById('interactionFeedback').innerHTML = `✨ 已加载“${config.name}”，使用鼠标拖拽旋转视角，观察场景中的动态物体`;
}

// 根据用户输入解析场景
function parseSceneFromInput(prompt) {
    const lower = prompt.toLowerCase();
    if (lower.includes('公交') || lower.includes('巴士') || lower.includes('车')) return 'bus';
    if (lower.includes('公园') || lower.includes('秋千') || lower.includes('草地')) return 'park';
    if (lower.includes('超市') || lower.includes('商店') || lower.includes('购物')) return 'supermarket';
    if (lower.includes('教室') || lower.includes('学校') || lower.includes('课堂') || lower.includes('老师')) return 'classroom';
    return 'garden';
}

function setView(type) {
    if (!camera || !controls) return;
    isDynamicView = false;
    switch(type) {
        case 'front': camera.position.set(0, 2, 7); controls.target.set(0, 0.5, 0); break;
        case 'side': camera.position.set(6, 2, 0); controls.target.set(0, 0.5, 0); break;
        case 'top': camera.position.set(0, 8, 0); controls.target.set(0, 0.5, 0); break;
        case 'dynamic': isDynamicView = true; dynamicAngle = 0; return;
    }
    controls.update();
}

// 后端API调用
async function callBackendAPI(prompt) {
    try {
        const response = await fetch('http://localhost:8000/api/generate-4d', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });
        if (response.ok) {
            const data = await response.json();
            return data;
        }
    } catch(e) {
        console.log('后端调用失败:', e);
    }
    return null;
}

// DOM事件
document.addEventListener('DOMContentLoaded', () => {
    initThree();
    buildScene('garden');

    // 视角按钮
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            setView(btn.dataset.view);
        });
    });

    const generateBtn = document.getElementById('generateSceneBtn');
    const voiceTextArea = document.getElementById('voiceTextArea');
    const textInput = document.getElementById('textInput');
    const genModeRadios = document.querySelectorAll('input[name="genMode"]');

    generateBtn.addEventListener('click', async () => {
        const voice = voiceTextArea.value.trim();
        const text = textInput.value.trim();
        let prompt = text || voice;

        if (!prompt) {
            document.getElementById('interactionFeedback').innerHTML = '⚠️ 请输入或说出场景描述（如：公交车、公园、超市、教室）';
            return;
        }

        const useAI = document.querySelector('input[name="genMode"]:checked').value === 'ai';
        const loading = document.getElementById('sceneLoading');
        loading.style.display = 'flex';

        let sceneType = 'garden';

        if (useAI) {
            const result = await callBackendAPI(prompt);
            if (result && result.success) {
                sceneType = result.scene_type;
                document.getElementById('interactionFeedback').innerHTML = `🤖 AI生成: ${result.message}`;
            } else {
                sceneType = parseSceneFromInput(prompt);
                document.getElementById('interactionFeedback').innerHTML = `⚠️ AI服务未响应，使用本地解析: ${sceneType}`;
            }
        } else {
            sceneType = parseSceneFromInput(prompt);
            document.getElementById('interactionFeedback').innerHTML = `✨ 本地模式 - 根据“${prompt}”生成${sceneType}场景`;
        }

        buildScene(sceneType);
        loading.style.display = 'none';

        // 记录历史
        const time = new Date().toLocaleString();
        const historyDiv = document.getElementById('historyRecords');
        const record = document.createElement('div');
        record.className = 'record-item';
        record.innerHTML = `${time} — 生成: ${prompt.substring(0,40)} → ${sceneType}场景`;
        historyDiv.prepend(record);
    });

    // 完成任务按钮
    document.getElementById('taskCompleteBtn').addEventListener('click', () => {
        const sceneName = sceneConfigs[currentTheme]?.name || '当前场景';
        const time = new Date().toLocaleTimeString();
        document.getElementById('interactionFeedback').innerHTML = `✅ ${time} 完成训练: ${sceneName} ⭐⭐⭐`;
        const historyDiv = document.getElementById('historyRecords');
        const record = document.createElement('div');
        record.className = 'record-item';
        record.innerHTML = `${new Date().toLocaleString()} — 完成任务: ${sceneName}`;
        historyDiv.prepend(record);
    });

    // 画板功能
    const canvas = document.getElementById('sketchCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 400; canvas.height = 160;
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#2c3e66';
    ctx.lineWidth = 2;
    let drawing = false;
    const getCoords = (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        let cx, cy;
        if (e.touches) { cx = e.touches[0].clientX; cy = e.touches[0].clientY; }
        else { cx = e.clientX; cy = e.clientY; }
        return { x: (cx - rect.left) * scaleX, y: (cy - rect.top) * scaleY };
    };
    canvas.addEventListener('mousedown', () => drawing = true);
    canvas.addEventListener('mouseup', () => { drawing = false; ctx.beginPath(); });
    canvas.addEventListener('mousemove', (e) => { if(drawing) { const p = getCoords(e); ctx.lineTo(p.x, p.y); ctx.stroke(); ctx.beginPath(); ctx.moveTo(p.x, p.y); } });
    canvas.addEventListener('touchstart', (e) => { drawing = true; e.preventDefault(); });
    canvas.addEventListener('touchend', () => { drawing = false; ctx.beginPath(); });
    canvas.addEventListener('touchmove', (e) => { if(drawing) { const p = getCoords(e); ctx.lineTo(p.x, p.y); ctx.stroke(); ctx.beginPath(); ctx.moveTo(p.x, p.y); } });
    document.getElementById('clearCanvasBtn').addEventListener('click', () => {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    });
    document.getElementById('undoCanvasBtn').addEventListener('click', () => {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    });

    // 语音识别
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = 'zh-CN';
        recognition.onresult = (e) => {
            voiceTextArea.value = e.results[0][0].transcript;
            document.getElementById('recordingStatus').innerText = '✅ 完成';
            document.getElementById('recordBtn').classList.remove('recording');
        };
        recognition.onerror = () => {
            document.getElementById('recordingStatus').innerText = '识别失败';
            document.getElementById('recordBtn').classList.remove('recording');
        };
    }
    document.getElementById('recordBtn').addEventListener('click', () => {
        if (recognition) {
            recognition.start();
            document.getElementById('recordingStatus').innerText = '🎙️ 录音中...';
            document.getElementById('recordBtn').classList.add('recording');
        } else {
            alert('浏览器不支持语音识别');
        }
    });

    // 评估记录
    document.getElementById('addRecordBtn').addEventListener('click', () => {
        const abc = document.getElementById('abcScore').value;
        const cars = document.getElementById('carsScore').value;
        const pep = document.getElementById('pepScore').value;
        const historyDiv = document.getElementById('historyRecords');
        const record = document.createElement('div');
        record.className = 'record-item';
        record.innerHTML = `${new Date().toLocaleString()} — ABC:${abc} CARS:${cars} PEP-3:${pep}`;
        historyDiv.prepend(record);
        document.getElementById('interactionFeedback').innerHTML = `📊 评估已保存，继续康复训练！`;
    });
});
// 后端健康检查函数
async function checkBackendHealth() {
    const statusSpan = document.getElementById('backendStatus');
    try {
        const response = await fetch('http://localhost:8000/health', {
            method: 'GET',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            statusSpan.innerHTML = '✅ 已连接';
            statusSpan.style.color = '#10b981';
            console.log('后端连接成功:', data);
            return true;
        } else {
            throw new Error('响应异常');
        }
    } catch (error) {
        console.error('后端连接失败:', error);
        statusSpan.innerHTML = '❌ 未连接 (请确保后端运行在8000端口)';
        statusSpan.style.color = '#ef4444';
        return false;
    }
}

// 修改后的API调用函数，增加更好的错误处理
async function callBackendAPI(prompt) {
    try {
        console.log('正在调用后端API:', prompt);
        const response = await fetch('http://localhost:8000/api/generate-4d', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ prompt: prompt })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('后端返回:', data);
        return data;
    } catch(e) {
        console.error('后端调用失败详情:', e);
        return null;
    }
}

// 页面加载时检测后端状态
document.addEventListener('DOMContentLoaded', () => {
    // 检测后端连接
    checkBackendHealth();
    
    // 每30秒检测一次
    setInterval(checkBackendHealth, 30000);
});