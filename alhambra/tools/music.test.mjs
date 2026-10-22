import test from 'node:test';
import assert from 'node:assert/strict';
import {createMusic} from './web/music.js';

test('a cancelled pending play cannot restart music; retry after rejection works',async()=>{
  const ids=['musicTrack','musicToggle','musicPanel','musicPlay','musicVolume','musicVolumeValue','musicClose'];
  const elements=Object.fromEntries(ids.map(id=>[id,{listeners:{},attrs:{},value:id==='musicVolume'?'55':'',hidden:true,classList:{toggle(){}},addEventListener(t,fn){this.listeners[t]=fn;},setAttribute(k,v){this.attrs[k]=v;},getAttribute(k){return this.attrs[k]??null;},contains(){return false;},focus(){}}]));
  const previous=globalThis.document;
  const listeners={};globalThis.document={getElementById:id=>elements[id],addEventListener(t,fn){listeners[t]=fn;}};
  try{
    const a=elements.musicTrack;let resolve,reject;
    a.pause=()=>{a.paused=true;};
    a.play=()=>{a.paused=false;return new Promise((r,j)=>{resolve=r;reject=j;});};
    const warnings=[];createMusic({getLanguage:()=> 'ja',toast:(...x)=>warnings.push(x)});
    assert.equal(a.src,'audio/asturias-full.mp3','music starts automatically');
    assert.equal(a.volume,.55);
    assert.equal(elements.musicPlay.attrs['aria-pressed'],'true');
    await elements.musicPlay.listeners.click();
    resolve();await Promise.resolve();await Promise.resolve();
    assert.equal(a.paused,true);assert.equal(elements.musicPlay.attrs['aria-pressed'],'false');
    const second=elements.musicPlay.listeners.click();reject(new Error('network'));await second;
    assert.equal(elements.musicPlay.attrs['aria-pressed'],'false');assert.equal(warnings.length,1);
    const third=elements.musicPlay.listeners.click();resolve();await third;
    assert.equal(elements.musicPlay.textContent,'Ⅱ 一時停止');
    // A fresh instance silently retries browser-blocked autoplay on interaction.
    createMusic({getLanguage:()=> 'ja',toast:(...x)=>warnings.push(x)});
    reject(Object.assign(new Error('gesture required'),{name:'NotAllowedError'}));
    await Promise.resolve();await Promise.resolve();
    assert.equal(warnings.length,1);
    listeners.pointerdown({target:{}});resolve();
    await Promise.resolve();await Promise.resolve();
    assert.equal(elements.musicPlay.textContent,'Ⅱ 一時停止');
    await elements.musicPlay.listeners.click();
    listeners.pointerdown({target:{}});
    assert.equal(a.paused,true,'explicit pause survives subsequent gestures');
  }finally{globalThis.document=previous;}
});
