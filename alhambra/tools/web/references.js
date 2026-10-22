// The photographs and their credits are local static assets, loaded on demand.
export function createReferences({getPlace,getLanguage,onOpen}){
  const $=id=>document.getElementById(id),dialog=$('references');
  let manifestPromise=null,photos=[],index=0,currentPlace=null,generation=0;
  const localized=(ja,en)=>getLanguage()==='ja'?ja:en;
  function status(state,ja,en){$('referenceStage').dataset.state=state;$('referenceStatus').textContent=localized(ja,en);}
  function labels(){
    $('referenceClose').setAttribute('aria-label',localized('写真を閉じる','Close photographs'));
    $('referencePrevious').setAttribute('aria-label',localized('前の写真','Previous photograph'));
    $('referenceNext').setAttribute('aria-label',localized('次の写真','Next photograph'));
    if(currentPlace){$('referenceTitle').textContent=currentPlace[getLanguage()];$('referenceSpanish').textContent=currentPlace.es;}
  }
  async function manifest(){
    if(!manifestPromise)manifestPromise=fetch('data/references.json').then(response=>{
      if(!response.ok)throw new Error('Reference catalogue unavailable');
      return response.json();
    }).catch(error=>{manifestPromise=null;throw error;});
    return manifestPromise;
  }
  function show(next){
    index=(next+photos.length)%photos.length;const photo=photos[index],token=++generation;
    const image=new Image();image.id='referenceImage';image.alt=photo.caption[getLanguage()];image.decoding='async';
    image.width=photo.width;image.height=photo.height;
    image.onload=()=>{if(token===generation)status('ready','','');};
    image.onerror=()=>{if(token===generation)status('error','写真を読み込めませんでした。下の出典リンクからご覧いただけます。','The photograph could not load. You can view it using the source link below.');};
    status('loading','写真を読み込んでいます…','Loading photograph…');
    $('referenceFrame').replaceChildren(image);image.src=photo.file;
    $('referenceCaption').textContent=photo.caption[getLanguage()];
    $('referenceChanges').textContent=photo.file.endsWith('.webp')?localized('縮小・WebP変換','Resized & converted to WebP'):localized('写真素材（JPEG）','Photographic material source (JPEG)');
    $('referenceAuthor').textContent=`${localized('撮影','Photo')}: ${photo.author}`;
    $('referenceLicense').textContent=photo.license;$('referenceLicense').href=photo.licenseUrl;
    $('referenceSource').href=photo.source;$('referenceSource').title=photo.originalTitle;
    $('referenceCounter').textContent=`${index+1} / ${photos.length}`;
    $('referenceNavigation').hidden=photos.length<2;$('referenceAttribution').hidden=false;
  }
  async function open(){
    if(dialog.open)return;
    onOpen();currentPlace=getPlace();photos=[];index=0;labels();
    $('referenceFrame').replaceChildren();$('referenceCaption').textContent='';
    $('referenceAttribution').hidden=true;$('referenceNavigation').hidden=true;
    status('loading','写真を読み込んでいます…','Loading photographs…');
    const token=++generation;dialog.showModal();
    try{
      const data=await manifest();if(token!==generation||!dialog.open)return;
      photos=data.places[currentPlace.id];if(!photos?.length)throw new Error('No photographs for this place');
      show(0);
    }catch{
      if(token===generation&&dialog.open)status('error','参考写真を読み込めませんでした。閉じて、もう一度お試しください。','The photographs could not load. Close and try again.');
    }
  }
  $('referenceClose').onclick=()=>dialog.close();
  $('referencePrevious').onclick=()=>show(index-1);$('referenceNext').onclick=()=>show(index+1);
  dialog.addEventListener('keydown',event=>{
    if(photos.length>1&&['ArrowLeft','ArrowRight'].includes(event.key)){
      event.preventDefault();show(index+(event.key==='ArrowLeft'?-1:1));
    }
  });
  // Both ends of a click must be on the backdrop, so image drags do not close it.
  let backdropDown=false;
  const outside=event=>{const r=dialog.getBoundingClientRect();return event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom;};
  dialog.addEventListener('pointerdown',event=>{backdropDown=event.target===dialog&&outside(event);});
  dialog.addEventListener('click',event=>{if(backdropDown&&event.target===dialog&&outside(event))dialog.close();backdropDown=false;});
  dialog.addEventListener('close',()=>{generation++;$('referenceOpen').focus({preventScroll:true});});
  return {open,localize:labels};
}
