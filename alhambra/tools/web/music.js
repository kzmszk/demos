// Stream the rendered track; do not decode minutes of PCM in the 3D renderer.
export function createMusic({getLanguage,toast}) {
  const $=id=>document.getElementById(id), track=$('musicTrack');
  const toggle=$('musicToggle'), panel=$('musicPanel'), play=$('musicPlay'), volume=$('musicVolume');
  let wanted=false,pending=false,revision=0,awaitingGesture=false;
  try{const saved=localStorage.getItem('alhambra.music.volume');if(saved!==null&&Number.isFinite(Number(saved)))volume.value=String(Math.max(0,Math.min(100,Number(saved))));}catch{}
  track.volume=Number(volume.value)/100;
  const label=(ja,en)=>getLanguage()==='ja'?ja:en;
  function localize(){
    toggle.title=toggle.getAttribute('aria-label')||label('音楽','Music');
    play.textContent=pending?label('読み込み中…（停止）','Loading… (stop)'):wanted?label('Ⅱ 一時停止','Ⅱ Pause'):label('▶ 再生','▶ Play');
    play.setAttribute('aria-pressed',String(wanted));
    toggle.classList.toggle('playing',wanted);
    $('musicVolumeValue').value=`${volume.value}%`;
    volume.setAttribute('aria-valuetext',`${volume.value}%`);
  }
  function close(){panel.hidden=true;toggle.setAttribute('aria-expanded','false');}
  toggle.addEventListener('click',()=>{panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));});
  $('musicClose').addEventListener('click',()=>{close();toggle.focus();});
  document.addEventListener('pointerdown',e=>{if(!panel.hidden&&!panel.contains(e.target)&&!toggle.contains(e.target))close();});
  panel.addEventListener('keydown',e=>{e.stopPropagation();if(e.key==='Escape'){close();toggle.focus();}});
  async function start(automatic=false){
    const token=++revision;
    awaitingGesture=false;wanted=true;pending=true;localize();
    try{
      if(!track.getAttribute('src'))track.src='audio/asturias-full.mp3';
      await track.play();
      if(token!==revision){if(!wanted)track.pause();return;}
      pending=false;localize();
    }catch(error){
      if(token!==revision)return;
      pending=false;
      if(automatic&&error.name==='NotAllowedError'){
        awaitingGesture=true;localize();return;
      }
      wanted=false;localize();
      toast('音楽を再生できませんでした。再生ボタンでもう一度お試しください。','Music could not start. Press Play to try again.');
    }
  }
  play.addEventListener('click',()=>{
    if(wanted){++revision;awaitingGesture=false;wanted=false;pending=false;track.pause();localize();return;}
    return start();
  });
  const unlock=e=>{
    if(awaitingGesture&&wanted&&!play.contains(e.target))start(true);
  };
  document.addEventListener('pointerdown',unlock);
  document.addEventListener('keydown',unlock);
  track.addEventListener('error',()=>{
    ++revision;awaitingGesture=false;wanted=false;pending=false;localize();
    toast('音楽ファイルを読み込めませんでした。','The music file could not be loaded.');
  });
  volume.addEventListener('input',()=>{
    track.volume=Number(volume.value)/100;
    try{localStorage.setItem('alhambra.music.volume',volume.value);}catch{}
    localize();
  });
  localize();
  start(true);
  return {localize};
}
