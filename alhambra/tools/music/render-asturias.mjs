// Asturias: opening studies and a longer guitar reduction (--full).
// Independently entered from the original piano score.
// Transposed G minor -> E minor; piano octave doubling reduced for guitar.
// The last two bars are a new short cadence, not part of Albéniz's original.
// See README.md for sources and sample attribution. Node.js + ffmpeg only.
import fs from 'node:fs';
import { fullScore } from './asturias-score.mjs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const dir = path.dirname(fileURLToPath(import.meta.url));
const cache = path.join(dir, '.cache');
const out = path.resolve(dir, '../../public/audio');
fs.mkdirSync(cache, {recursive:true});
fs.mkdirSync(out, {recursive:true});
const sampleFile = path.join(cache, 'nylon.js');
if (!fs.existsSync(sampleFile)) throw Error('Download nylon.js as documented in README.md first.');
const bytes = fs.readFileSync(sampleFile);
if (crypto.createHash('sha256').update(bytes).digest('hex') !== '5375fa9e0408d960e12b6e4ec120c42bce824d80b18e982b27ddaece146a4f64') throw Error('Unexpected sample source checksum');
const source = bytes.toString();
// Parse data only: never execute downloaded JavaScript.
const bank = JSON.parse(source.slice(source.indexOf('{', source.indexOf('acoustic_guitar_nylon =')), source.lastIndexOf('}') + 1).replace(/,\s*}$/, '}'));
const rate = 44100;
const pitches = {C:0,D:2,E:4,F:5,G:7,A:9,B:11};
function midi(name) {
  const m = /^([A-G])([#b]?)(\d)$/.exec(name);
  if (!m) throw Error(`Bad note ${name}`);
  return (Number(m[3])+1)*12+pitches[m[1]]+(m[2]==='#'?1:m[2]==='b'?-1:0);
}
function noteName(n) { return ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'][n%12]+(Math.floor(n/12)-1); }
const samples = new Map();
function sample(n) {
  if (samples.has(n)) return samples.get(n);
  const key = noteName(n), data = bank[key];
  if (!data) throw Error(`Missing sample ${key}`);
  const inputFile = path.join(cache, `${key}.mp3`), rawFile = path.join(cache, `${key}.raw`);
  fs.writeFileSync(inputFile, Buffer.from(data.split(',')[1], 'base64'));
  execFileSync('ffmpeg', ['-nostdin','-v','error','-y','-i',inputFile,'-f','f32le','-ac','1','-ar',String(rate),rawFile], {stdio:'ignore',timeout:15000});
  const raw = fs.readFileSync(rawFile);
  const floats = new Float32Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));
  samples.set(n,floats);
  return floats;
}
const base = 'G3 D4 Eb4 C4 D4 Bb3';
// Six eighth-note melody attacks per 3/4 bar, interleaved with six D4 pedals.
// Names below remain in the original G-minor piano key for source auditing.
const bars = [
  base,base,base,'C4 A3 Bb3 C4 A3 Bb3',base,base,base,'C4 A3 Bb3 G3 F3 Eb3',
  'D3 D4 Eb4 C4 D4 Bb3','D3 D4 Eb4 C4 D4 Bb3','D3 A3 C4 D4 Eb4 F4',
  'D4 Eb4 C4 D4 Bb3 A3','D3 D4 Eb4 C4 D4 Bb3','D3 D4 Eb4 C4 D4 Bb3',
  'D3 C4 D4 Eb4 F4 D4','Eb4 C4 D4 Bb3 C4 A3',
  base,base,base,'C4 A3 Bb3 C4 A3 Bb3',base,base,base,'C4 A3 Bb3 G3 F3 Eb3',
].map(b=>b.split(' ').map(n=>midi(n)-3));
if (bars.length!==24 || bars.some(b=>b.length!==6)) throw Error('Incomplete transcription');

function render(bpm,tag) {
  let seed=232;
  const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
  const beat=60/bpm; let events=[];
  const add=(t,n,d,g,voice)=>events.push({t,n,d,g,voice});
  let at=.25;
  for(let b=0;b<bars.length;b++) {
    const swell= b<8 ? .72+.08*Math.sin(b*Math.PI/7) : b<16 ? .72+.07*(b-8)/8 : .83+.30*(b-16)/7;
    const barBeat=beat*(1+.009*Math.sin(b*.8));
    for(let i=0;i<6;i++) {
      const t=at+i*.5*barBeat;
      add(t+(random()-.5)*.003,bars[b][i],.47*barBeat,swell*(i===0?1.07:1)*(1+(random()-.5)*.06),'melody');
      add(t+.25*barBeat+(random()-.5)*.004,midi('B3'),.29*barBeat,.47*swell*(i%2?.94:1),'pedal');
      if(b>=16) add(t+.25*barBeat+.004,midi('B4'),.26*barBeat,.32*swell,'octave');
    }
    at+=3*barBeat;
  }
  // New excerpt ending: rolled B7, followed by E minor. Keeps the sample from
  // ending abruptly in the middle of the original's continuing development.
  ['B2','F#3','A3','D#4','F#4'].forEach((n,i)=>add(at+i*.026,midi(n),1.7*beat,.85,'cadence'));
  at+=3*beat;
  ['E2','B2','E3','G3','B3','E4'].forEach((n,i)=>add(at+i*.023,midi(n),2.1, .9,'cadence'));
  let duration=at+3.3;
  if(tag==='full'){
    const score=fullScore(bars,midi);events=score.events;duration=score.duration;
    fs.writeFileSync(path.join(dir,'asturias-sections.json'),JSON.stringify(score.sections,null,2)+'\n');
  }
  const size=Math.ceil(duration*rate);
  const dry=new Float32Array(size);
  for(const e of events) {
    const s=sample(e.n), start=Math.round(e.t*rate), hold=Math.round(e.d*rate), release=Math.round((e.voice==='cadence'?.28:.065)*rate);
    const len=Math.min(s.length,hold+release,size-start);
    // Soft notes lose some upper-frequency energy, approximating lighter plucks.
    let low=0; const a=e.voice==='pedal'?.57:.80;
    for(let i=0;i<len;i++) {
      low+=a*(s[i]-low);
      const env=i<hold?1:Math.pow(Math.max(0,1-(i-hold)/release),2);
      dry[start+i]+=low*env*e.g*.53;
    }
  }
  const L=new Float32Array(dry), R=new Float32Array(dry);
  // Quiet short room reflections; mostly dry to preserve rapid articulation.
  for(const [ms,g] of [[29,.075],[47,.06],[71,.044],[103,.032],[149,.022],[211,.015]]) {
    const dl=Math.round(ms*.001*rate),dr=Math.round((ms+11)*.001*rate);
    for(let i=0;i<size-dr;i++){L[i+dl]+=dry[i]*g;R[i+dr]+=dry[i]*g;}
  }
  let peak=0,energy=0;
  for(let i=0;i<size;i++)peak=Math.max(peak,Math.abs(L[i]),Math.abs(R[i]));
  const gain=.86/peak, pcm=Buffer.alloc(size*4);
  for(let i=0;i<size;i++) {
    const fade=Math.min(1,(size-i)/(rate*.45));
    const l=L[i]*gain*fade,r=R[i]*gain*fade;
    if(!Number.isFinite(l+r))throw Error('Invalid audio sample');
    energy+=(l*l+r*r)/2;
    pcm.writeInt16LE(Math.round(l*32767),i*4);pcm.writeInt16LE(Math.round(r*32767),i*4+2);
  }
  const header=Buffer.alloc(44);
  header.write('RIFF');header.writeUInt32LE(36+pcm.length,4);header.write('WAVEfmt ',8);
  header.writeUInt32LE(16,16);header.writeUInt16LE(1,20);header.writeUInt16LE(2,22);
  header.writeUInt32LE(rate,24);header.writeUInt32LE(rate*4,28);header.writeUInt16LE(4,32);header.writeUInt16LE(16,34);
  header.write('data',36);header.writeUInt32LE(pcm.length,40);
  const wav=path.join(cache,`asturias-${tag}.wav`), mp3=path.join(out,`asturias-${tag}.mp3`);
  fs.writeFileSync(wav,Buffer.concat([header,pcm]));
  execFileSync('ffmpeg',['-v','error','-y','-i',wav,'-codec:a','libmp3lame','-b:a','192k','-metadata',`title=Asturias — ${tag} guitar arrangement`,'-metadata','artist=Isaac Albéniz / sequenced nylon-guitar study',mp3], {stdio:'ignore',timeout:30000});
  fs.writeFileSync(path.join(dir,`asturias-${tag}-events.json`),JSON.stringify({bpm,originalBars:tag==='full'?null:24,ending:tag==='full'?'Guitar reduction with coda':'New two-bar cadence',events},null,2)+'\n');
  return {tag,bpm,seconds:Number(duration.toFixed(3)),notes:events.length,peakDBFS:20*Math.log10(.86),rmsDBFS:20*Math.log10(Math.sqrt(energy/size)),file:mp3};
}
const results=process.argv.includes('--full')?[render(152,'full')]:[render(132,'study'),render(152,'brisk')];
fs.writeFileSync(path.join(dir,process.argv.includes('--full')?'asturias-full-render.json':'asturias-render.json'),JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results,null,2));
