// Independent guitar reduction of the early piano score, printed pp.2–7.
// All pitch names below use the ORIGINAL key; renderer transposes down 3 semitones.
// Piano octave doublings are reduced; ornamentation/voicings are adapted.
export function fullScore(opening, midi) {
  const events=[], sections=[]; let time=.3, seed=232;
  const rnd=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
  const pitch=n=>typeof n==='number'?n:midi(n)-3;
  function put(t,n,d,g,voice='melody'){events.push({t,n:pitch(n),d,g:g*(.97+rnd()*.06),voice});}
  function chord(t,ns,d,g){ns.split(' ').forEach((n,i)=>put(t+i*.012,n,d,g,'cadence'));}
  const base='G3 D4 Eb4 C4 D4 Bb3', turn='C4 A3 Bb3 C4 A3 Bb3';
  const desc='C4 A3 Bb3 G3 F3 Eb3';
  const fast=[...opening.map(n=>({notes:n,accent:null})),
    // pp.2–3: dominant accents, rising dynamics, chromatic tension.
    ...[base,base,'A3 D4 Eb4 F4 G4 A4','F4 G4 Eb4 F4 D4 C4',base,base,
      'A3 D4 Eb4 F4 G4 A4','F4 G4 Eb4 F4 D4 C4'].map((n,i)=>({notes:n,accent:i===3||i===7?null:'D3 A3 D4 F#4 A4'})),
    ...[base,base,base,turn].map((n,i)=>({notes:n,accent:i===3?null:'G2 D3 G3 Bb3 D4 G4'})),
    ...[base,base,base,'C4 A3 Bb3 C4 G3 A3'].map((n,i)=>({notes:n,accent:i===3?null:'F#2 C3 F#3 A3 D4 F#4'})),
    ...['D4 Eb4 C#4 D4 Bb3','Eb4 F4 D4 Eb4 Bb3','D4 Eb4 C#4 D4 Bb3','Eb4 F4 Eb4 Eb4 Bb3','D4 Eb4 C4 D4 Bb3'].map((n,i)=>({notes:'D3 '+n,accent:i%2?'F#2 C3 F#3 A3 D4 F#4':'D3 A3 D4 F#4 A4'})),
    ...['C4 A3 Bb3 C4 A3 Bb3','A3 Bb3 C4 A3 Bb3 Bb3','A3 Bb3 Bb3 A3 G3 F3',base,turn,'G3 A3 Bb3 C4 A3 Bb3','G3 A3 Bb3 G3 F3 Eb3'].map(n=>({notes:n})),
  ];
  function rapid(reprise=false) {
    sections.push({name:reprise?'再現部':'主部',at:time});
    const beat=60/152;
    fast.forEach((b,bi)=>{
      const notes=typeof b.notes==='string'?b.notes.split(' ').map(pitch):b.notes;
      const gain=bi<16?.72:bi<24?.85+(bi-16)*.04:bi<45?1.08:Math.max(.52,1.05-(bi-45)*.07);
      notes.forEach((n,i)=>{
        const t=time+i*.5*beat;
        put(t+(rnd()-.5)*.003,n,.47*beat,gain*(i===0?1.08:1));
        put(t+.25*beat,'D4',.29*beat,.47*gain,'pedal');
        if(bi>=16&&bi<49)put(t+.25*beat+.004,'D5',.26*beat,.30*gain,'octave');
      });
      if(b.accent)chord(time,b.accent,.43*beat,.70);
      time+=3*beat;
    });
    // pp.3/7: pedal arpeggios, followed by the rising dominant run.
    const figures=[['D2','A2 D3 Eb3 C#3 D3','F#3 A3'],['D2','A2 E3 F3 D3 E3','G3 Bb3'],['D2','A2 D3 Eb3 C#3 D3','F#3 A3'],['D2','A2 E3 F3 D3 E3','G3 Bb3'],['D2','A2 D3 Eb3 C#3 D3','F#3 A3'],['D2','D3 Eb3 C#3 D3 A2','F#3 A3']];
    for(const [bass,ns,upper] of figures){
      const line=[bass,...ns.split(' ')];
      line.forEach((n,i)=>{put(time+i*.5*beat,n,.46*beat,.65);chord(time+(i*.5+.25)*beat,upper,.23*beat,.34);});
      time+=3*beat;
    }
    const run='D2 G3 A3 C#4 D4 F#4 A4 C#5 D5 F#5 A5 D6'.split(' ');
    run.forEach((n,i)=>{let p=pitch(n);while(p>81)p-=12;put(time+i*.25*beat,p,.3*beat,.70);});time+=3*beat;
    chord(time,'D3 A3 D4 F#4 A4',2.3,.65);time+=3.2;
  }
  rapid();
  sections.push({name:'中間部',at:time});
  // Cantando: melody reduced by an octave to the upper guitar register.
  // Tokens are original note:quarter-note duration; rests are '-'.
  function song(melody,bass,tempo=72,gain=.76,hold=1) {
    const beat=60/tempo; let pos=0;
    for(const token of melody.split(' ')) {
      const [n,dur]=token.split(':');const d=Number(dur);
      if(n!=='-')put(time+pos*beat,pitch(n)-12,Math.max(.12,d*beat*.92),gain);
      pos+=d;
    }
    if(bass) bass.split(' ').forEach((n,i)=>put(time+i*beat,n,beat*1.15,.45,'bass'));
    time+=pos*beat*hold;
  }
  function restChord(ns,tempo=72,hold=1){const beat=60/tempo;chord(time,ns,3*beat*hold,.58);time+=3*beat*hold;}
  function theme(lower=false){
    song('D6:2 C6:.5 D6:.5','D3 C3 D3');
    song('F6:2 D6:.5 C6:.5','F3 D3 C3');
    song('D6:2 -:1','D3');
    restChord(lower?'A2 E3 G3 C#4 E4':'D3 A3 D4 F#4 A4',72,1.25);
  }
  theme();theme(true);
  song('D6:2 C#6:1','D3 C#3',68);
  song('C#6:1 Bb5:.5 A5:.5 G5:.5 Bb5:.5','C#3 Bb2 A2',68);
  song('A5:2 -:1','G2',68);restChord('D3 A3 D4 F#4 A4',68,1.25);
  song('F6:2 A6:.5 F6:.5','D3 E3 D3',72,.84);
  song('E6:.5 D6:.5 E6:.25 D6:.25 C6:.5 F6:1','C#3 Bb2 C3',66);
  song('Bb5:2 -:1','G2',62);restChord('A2 E3 G3 C#4 E4',62,1.2);
  // pp.4–5: answering low phrases, little turns, chromatic descent.
  song('-:1 D5:2','Bb3',68,.65);
  song('-:1 G5:.5 F5:.5 G5:.5 Eb6:.5','A3',72,.72);
  song('-:1 D5:2','Bb3',68,.64);
  song('-:1 C#6:1 C6:1','A3 F#3',68,.66);
  for(let k=0;k<3;k++)song('-:1 '+(k===0?'Bb5':'A5')+':1 D6:1','G3',68-k*2,.67);
  restChord('D3 A3 C#4 G4',64,1.2);
  const answer=()=>{song('-:2 F#5:1','D3 A3',76,.65);song('C6:.5 D6:.5 E6:.5 F6:.25 E6:.25 D6:.5 C6:.5','D3 A3',76,.76);};
  answer();answer();
  song('-:2 F#5:1','D3 A3',72,.64);
  song('C6:.5 D6:.5 E6:.5 F6:.25 E6:.25 D6:.5 C6:.5','C3 D3 E3',70);
  song('D6:.5 C#6:.5 Bb5:.5 D6:.5 C6:.5 A5:.5','D3 C#3 Bb2',66,.68);
  song('C6:.5 Bb5:.5 G#5:.5 Bb5:.5 A5:.5 F5:.5','C3 Bb2 G#2',62,.65);
  answer();answer();
  song('D5:.5 E5:.5 F5:.5 C5:.25 D5:.25 A4:.5 C5:.5','D3 C3 Bb2',76,.84);
  song('A4:.5 C5:.5 G4:.5 C5:.5 A4:.5 C5:.5','A2 G#2 A2',76,.70);
  song('F5:.5 G5:.5 A5:.5 E5:.25 F5:.25 C5:.5 E5:.5','F3 E3 D3',76,.85);
  song('D5:.5 F5:.5 C#5:.5 F5:.5 D5:.5 F5:.5','D3 C3 D3',76,.76);
  song('Bb5:.5 C6:.5 D6:.5 F6:.5 Eb6:.5 D6:.5','Bb3 C4 D4',72,.84);
  song('F6:.5 D6:.5 C6:.5 B5:.5 D6:.5 F6:.5','F4 D4 C4',66,.78,1.15);
  song('E4:.5 F4:.5 G4:.5 A4:.25 G4:.25 F4:.5 E4:.5','C3 C#3',70,.75);
  answer();answer();song('-:2 F#5:1','D3 A3',68,.6);
  song('A4:.5 B4:.5 C5:.5 E5:.5 B4:.5 C5:.5','G3',76,.68);
  song('E4:.5 F#4:.5 G4:.5 C5:.5 F#4:.5 G4:.5','E3',72,.65);
  song('D4:.5 G4:.5 A4:.5 F#4:.5 E4:.5 D4:.5','D3',66,.6);
  theme();theme(true);
  rapid(true);
  sections.push({name:'コーダ',at:time});
  for(const ns of ['G2 D3 G3 Bb3','D3 F#3 A3','G2 D3 G3 Bb3','C3 Eb3 G3','Eb3 G3 Bb3 Eb4','Eb3 G3 Bb3 D4'])restChord(ns,66,1);
  song('F#5:1 E5:.5 D5:.5 C5:.5 Bb4:.5','G2',60,.58);
  for(let i=0;i<2;i++){
    const beat=60/84;opening[0].forEach((n,j)=>{put(time+j*.5*beat,n,.5*beat,.55);put(time+(j*.5+.25)*beat,'D4',.35*beat,.28,'pedal');});time+=3*beat;
  }
  for(let i=0;i<2;i++)song('G5:.5 G5:.5 G5:.5 G5:.5 G5:.5 G5:.5','C#3 D3 C#3',70-i*8,.45);
  chord(time,'G2 D3 G3 Bb3 D4 G4',2.8,.42);time+=3.4;put(time,'G2',2.6,.43,'cadence');time+=3.8;
  return {events,sections,duration:time};
}
