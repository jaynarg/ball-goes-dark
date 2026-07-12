/* Runs the real page script against stubbed THREE + DOM.
   `node --check` only proves the file parses. It happily accepts a temporal-dead-zone
   reference, a typo'd getElementById, or a call to a function that no longer exists —
   all of which kill the page on load. This executes it. */
const fs = require('fs');

const html = fs.readFileSync(process.argv[2] || 'index.html', 'utf8');
const src = html.split('<script>')[1].split('</script>')[0];

// ---------------------------------------------------------------- THREE stub
class V2 { constructor(x=0,y=0){this.x=x;this.y=y;} set(x,y){this.x=x;this.y=y;return this;} }
class V3 {
  constructor(x=0,y=0,z=0){this.x=x;this.y=y;this.z=z;}
  set(x,y,z){this.x=x;this.y=y;this.z=z;return this;}
  clone(){return new V3(this.x,this.y,this.z);}
  copy(v){this.x=v.x;this.y=v.y;this.z=v.z;return this;}
  add(v){this.x+=v.x;this.y+=v.y;this.z+=v.z;return this;}
  addVectors(a,b){this.x=a.x+b.x;this.y=a.y+b.y;this.z=a.z+b.z;return this;}
  subVectors(a,b){this.x=a.x-b.x;this.y=a.y-b.y;this.z=a.z-b.z;return this;}
  cross(v){const x=this.y*v.z-this.z*v.y,y=this.z*v.x-this.x*v.z,z=this.x*v.y-this.y*v.x;this.x=x;this.y=y;this.z=z;return this;}
  dot(v){return this.x*v.x+this.y*v.y+this.z*v.z;}
  lengthSq(){return this.dot(this);}
  length(){return Math.sqrt(this.lengthSq());}
  normalize(){const l=this.length()||1;this.x/=l;this.y/=l;this.z/=l;return this;}
  negate(){this.x=-this.x;this.y=-this.y;this.z=-this.z;return this;}
  lerp(v,t){this.x+=(v.x-this.x)*t;this.y+=(v.y-this.y)*t;this.z+=(v.z-this.z)*t;return this;}
  multiplyScalar(s){this.x*=s;this.y*=s;this.z*=s;return this;}
  applyQuaternion(){return this;}
}
class Quat {
  constructor(){this.x=0;this.y=0;this.z=0;this.w=1;}
  copy(){return this;} clone(){return new Quat();}
  setFromAxisAngle(){return this;} setFromUnitVectors(){return this;}
  premultiply(){return this;} slerp(){return this;}
}
class Obj3 {
  constructor(){this.children=[];this.position=new V3();this.rotation={set(){}};this.quaternion=new Quat();this.userData={};this.scale={setScalar(){}};}
  add(o){this.children.push(o);} copy(){return this;}
}
const stubMaterial = () => ({color:{set(){}}, emissive:{set(){}}, emissiveIntensity:0, opacity:1, map:null});
const THREE = {
  Vector2: V2, Vector3: V3, Quaternion: Quat, Group: Obj3, Scene: Obj3, Object3D: Obj3,
  Color: class { constructor(){} set(){} },
  BufferGeometry: class { setAttribute(){} },
  BufferAttribute: class { constructor(a,b){this.array=a;this.itemSize=b;} },
  SphereGeometry: class {},
  Mesh: class extends Obj3 { constructor(g,m){super();this.geometry=g;this.material=m;} },
  MeshStandardMaterial: class { constructor(){Object.assign(this, stubMaterial());} },
  MeshBasicMaterial: class { constructor(){Object.assign(this, stubMaterial());} },
  Sprite: class extends Obj3 { constructor(m){super();this.material=m;} },
  SpriteMaterial: class { constructor(){Object.assign(this, stubMaterial());} },
  CanvasTexture: class { constructor(){this.needsUpdate=false;} },
  AmbientLight: Obj3, HemisphereLight: Obj3, DirectionalLight: class extends Obj3 {},
  PerspectiveCamera: class extends Obj3 { constructor(fov){super();this.fov=fov;this.aspect=1;} updateProjectionMatrix(){} },
  WebGLRenderer: class {
    constructor(){ this.domElement = mkEl('canvas'); }
    setPixelRatio(){} setSize(){} render(){ stats.renders++; }
  },
  Raycaster: class { setFromCamera(){} intersectObjects(){return [];} },
};

// ------------------------------------------------------------------ DOM stub
const stats = { renders: 0, rafs: 0, ids: new Set(), missingIds: new Set() };
function mkEl(tag='div'){
  const el = {
    tagName: tag, style:{}, dataset:{}, hidden:false, value:'', textContent:'', innerHTML:'',
    children:[], classList:{add(){},remove(){},contains(){return false;}},
    addEventListener(){}, removeEventListener(){}, appendChild(c){el.children.push(c);},
    setAttribute(){}, getAttribute(){return null;}, focus(){},
    setPointerCapture(){}, releasePointerCapture(){},
    querySelectorAll(){return [];}, querySelector(){return null;},
    getBoundingClientRect(){ return {top:0,left:0,right:0,bottom:140,width:200,height:140}; },
    getContext(){ return {
      clearRect(){}, fillRect(){}, strokeRect(){}, fillText(){}, drawImage(){}, save(){}, restore(){},
      measureText(){return {width:10};}, set font(v){}, set fillStyle(v){}, set strokeStyle(v){},
      set textAlign(v){}, set textBaseline(v){}, set shadowColor(v){}, set shadowBlur(v){},
      set shadowOffsetY(v){}, set lineWidth(v){},
    };},
    width:0, height:0,
  };
  return el;
}
const known = {};
const document = {
  createElement: mkEl,
  getElementById(id){
    stats.ids.add(id);
    if(!(id in known)) known[id] = mkEl();
    return known[id];
  },
  querySelectorAll(){ return []; },
  querySelector(){ return null; },
  addEventListener(){},
  activeElement: null,
};
// the ids the markup actually defines
for(const id of (html.match(/id="([^"]+)"/g)||[]).map(s=>s.slice(4,-1))) known[id] = mkEl();

global.document = document;
global.window = { storage: undefined };
global.THREE = THREE;
global.innerWidth = +(process.env.W || 1440);
global.innerHeight = +(process.env.H || 900);
global.devicePixelRatio = 2;
global.addEventListener = () => {};
global.matchMedia = () => ({matches:false});
global.requestAnimationFrame = (fn) => { stats.rafs++; if(stats.rafs === 1) fn(performance.now()); };
global.performance = { now: () => 0 };
global.Image = class { set src(v){} };
global.Date = Date;

// ------------------------------------------------------------------- execute
try {
  new Function(src)();
} catch (e) {
  console.error('RUNTIME ERROR: ' + e.constructor.name + ': ' + e.message);
  const line = (e.stack||'').split('\n')[1] || '';
  console.error('  at' + line.replace(/^\s*at/, ''));
  process.exit(1);
}

// did the page reach the point where it actually draws?
const missing = [...stats.ids].filter(id => !(html.includes(`id="${id}"`)));
console.log(`executed cleanly at ${innerWidth}x${innerHeight}`);
console.log('  requestAnimationFrame calls :', stats.rafs, stats.rafs > 0 ? '(render loop started)' : '(NEVER STARTED)');
console.log('  renderer.render calls       :', stats.renders);
console.log('  getElementById ids used     :', stats.ids.size);
if(missing.length){
  console.error('  IDS NOT IN MARKUP          :', missing.join(', '));
  process.exit(1);
}
console.log('  every id resolves in markup : yes');
const through = known['through'] && known['through'].textContent;
console.log('  masthead date               :', JSON.stringify(through));
const strip = ['s_played','s_goals','s_scorers','s_og']
  .map(id => `${id}=${known[id] && known[id].textContent}`).join('  ');
console.log('  strip counters              :', strip);
for(const id of ['s_played','s_goals','s_scorers','s_og']){
  const v = known[id] && known[id].textContent;
  if(v === undefined || v === '' || v === '\u2014' || Number.isNaN(Number(v))){
    console.error('  STRIP COUNTER NOT SET:', id); process.exit(1);
  }
}
if(!through || !/through \w+ \d+/.test(through)){
  console.error('  BYLINE DATE NOT SET');
  process.exit(1);
}
if(stats.rafs === 0 || stats.renders === 0){
  console.error('  RENDER LOOP NEVER RAN');
  process.exit(1);
}
console.log('OK');
