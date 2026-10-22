// Metres. Y is up; X follows the palace's east–west axis, Z its north–south axis.
// Room dimensions and relationships are an interpretive model, not a survey.
export const PLACES = [
  { id:'lions', no:'01', group:'nasrid', ja:'ライオンの中庭', en:'Court of the Lions', es:'Patio de los Leones', p:[27,1.65,7], t:[40,3.3,-2], floor:0, desc:{ja:'水路が四方へ伸びる大理石の中庭。細い柱が支える透かし彫りのアーチと、12頭のライオンが囲む噴水を巡ります。',en:'A marble court divided by four water channels. Slender columns carry carved arcades around a fountain supported by twelve lions.'}},
  { id:'myrtles', no:'02', group:'nasrid', ja:'アラヤネスの中庭', en:'Court of the Myrtles', es:'Patio de los Arrayanes', p:[-8.2,1.65,15], t:[0,7,-24], floor:0, desc:{ja:'長い水鏡の向こうにコマレスの塔。生垣、白い大理石の床、両端の柱廊がつくる静かな対称を歩きます。',en:'The Comares Tower rises beyond a long reflecting pool, framed by myrtle hedges, marble paving and porticoes.'}},
  { id:'ambassadors', no:'03', group:'nasrid', ja:'大使の間', en:'Hall of the Ambassadors', es:'Salón de los Embajadores', p:[0,1.65,-27.2], t:[0,7.2,-34], floor:0, desc:{ja:'コマレスの塔に収まる玉座の間。三方の窓のくぼみ、色彩豊かな腰壁、漆喰装飾と星形の木組み天井を見上げます。',en:'The throne room within the Comares Tower. Nine recessed window bays, tiled dados, carved plaster and a star-patterned timber ceiling.'}},
  { id:'sisters', no:'04', group:'nasrid', ja:'二姉妹の間', en:'Hall of the Two Sisters', es:'Sala de Dos Hermanas', p:[38,1.65,-16.3], t:[38,10.3,-21.5], floor:0, desc:{ja:'八角形へ移り変わる壁の上に、星を中心として広がるムカルナス天井。小さな立体の反復が光と影を刻みます。',en:'A square chamber becomes an octagon beneath a muqarnas vault. Repeated three-dimensional cells articulate the light around a central star.'}},
  { id:'abencerrajes', no:'05', group:'nasrid', ja:'アベンセラッヘスの間', en:'Hall of the Abencerrajes', es:'Sala de los Abencerrajes', p:[38,1.65,16.4], t:[38,8.8,21], floor:0, desc:{ja:'ライオンの中庭の南にある部屋。中央の水盤を囲むタイルと漆喰、その上に星形のムカルナスを組んでいます。',en:'South of the Court of the Lions, a central basin, tiled dado and plaster walls lead the eye to a star-shaped muqarnas vault.'}},
  { id:'mexuar', no:'06', group:'nasrid', ja:'メスアール', en:'Mexuar', es:'Sala del Mexuar', p:[-37,1.65,8], t:[-34,3.2,-4], floor:0, desc:{ja:'宮殿の政務空間。独立した柱、木の天井、幾何学タイルの腰壁から、黄金の間の中庭を経てコマレス宮へ。',en:'The administrative hall: freestanding columns, a timber ceiling and geometric dados, connected to the Golden Room court and Comares Palace.'}},
  { id:'kings', no:'07', group:'nasrid', ja:'諸王の間', en:'Hall of the Kings', es:'Sala de los Reyes', p:[59,1.65,8], t:[59,3.4,-7], floor:0, desc:{ja:'ライオンの中庭の東側に続く細長い空間。連続するアーチと装飾壁を再構成しています。中央の人物画を写真から天井面に再現しています。',en:'An elongated hall on the eastern side of the Court of the Lions, with a sequence of arches and ornamented walls. The central painting of figures is reproduced from a photograph on a curved ceiling panel.'}},
  { id:'lindaraja', no:'08', group:'nasrid', ja:'リンダラハの展望室', en:'Lindaraja Belvedere', es:'Mirador de Lindaraja', p:[38,1.65,-32], t:[38,2.4,-40], floor:0, desc:{ja:'二姉妹の間からアヒメセスの間を抜ける小さな展望室。双子窓と装飾アーチの向こうに、糸杉の庭が広がります。',en:'Beyond the Two Sisters and the Ajimeces hall, paired windows frame the cypress garden from a small, richly decorated belvedere.'}},
  { id:'alcazaba', no:'09', group:'fortress', ja:'アルカサバの兵営跡', en:'Alcazaba · Military quarter', es:'Barrio Castrense', p:[-91,1.65,67], t:[-161,5,73], floor:0, desc:{ja:'赤褐色の城壁に囲まれた軍事地区。通りを挟む住居跡、貯水槽、城門を歩き、塔と城壁の上へ進めます。',en:'The red-walled military quarter, with excavated houses, a central street, cisterns and fortified gateways. Climb the stairs to the battlements.'}},
  { id:'vela', no:'10', group:'fortress', ja:'ベラの塔', en:'Tower of the Candle', es:'Torre de la Vela', p:[-186,27.65,79], t:[-120,7,30], floor:26, desc:{ja:'アルカサバ西端の塔から、宮殿群とグラナダを見渡します。階段は徒歩操作のために簡略化した接続です。',en:'A panorama of the palace and Granada from the western tower. The stair connection is simplified for continuous walking.'}},
  { id:'partal', no:'11', group:'gardens', ja:'パルタル宮と庭園', en:'Partal Palace & gardens', es:'El Partal', p:[96,1.65,13], t:[96,5,-25], floor:0, desc:{ja:'水面に映る五連の柱廊と貴婦人の塔。段状の庭園を通り、東へ続く城壁沿いの散歩道へ。',en:'A five-arched portico and the Tower of the Ladies reflected in water. Terraced gardens lead east towards the walk along the towers.'}},
  { id:'generalife', no:'12', group:'gardens', ja:'ヘネラリフェ', en:'Generalife', es:'Patio de la Acequia', p:[420,33.65,-181], t:[420,36,-221], floor:32, desc:{ja:'宮殿から離れた夏の離宮。長い水路、交差する噴水、刈り込まれた生垣と花壇、両端の白いパビリオンを巡ります。',en:'The summer retreat beyond the Alhambra walls. A long water channel, crossing fountain jets, clipped hedges and flowerbeds between white pavilions.'}},
  { id:'carlos', no:'13', group:'grounds', ja:'カルロス5世宮殿', en:'Palace of Charles V', es:'Palacio de Carlos V', p:[3,1.65,77], t:[3,6,55], floor:0, desc:{ja:'方形の建物の中に円形の中庭。二層の古典的な列柱と、ナスル朝宮殿との建築の違いを見比べます。',en:'A circular courtyard within a square Renaissance palace. Two tiers of classical columns offer a striking comparison with the Nasrid palaces.'}},
  { id:'justice', no:'14', group:'grounds', ja:'裁きの門', en:'Gate of Justice', es:'Puerta de la Justicia', p:[-24,1.65,148], t:[-20,7,130], floor:0, desc:{ja:'大きな馬蹄形アーチが迎える城門。赤い城壁と塔、宮殿の外を囲む緑を眺めます。',en:'A monumental horseshoe gateway in the red walls, surrounded by the woodland below the palace.'}},
  { id:'overview', no:'15', group:'grounds', ja:'アルハンブラ全景', en:'The whole Alhambra', es:'La colina de la Sabika', p:[-300,275,400], t:[145,0,-20], mode:'orbit', desc:{ja:'サビカの丘を囲む城壁、アルカサバ、宮殿と庭園、その向こうのヘネラリフェ。ドラッグで回転し、全体のつながりを確かめます。',en:'The walls of the Sabika hill, the Alcazaba, palaces, gardens and the Generalife beyond. Drag to orbit and discover how the complex fits together.'}},
];
// Views placed after registering P-000158's scale bar against the OSM footprints.
const views={
  lions:[[27,1.65,25],[40,3.2,16]],myrtles:[[1.5,1.65,17.8],[1.5,5,-22]],
  ambassadors:[[1.5,1.65,-30],[1.5,7,-39]],sisters:[[38,1.65,4.4],[38,7.3,.4]],
  abencerrajes:[[38,1.65,31.5],[38,8.5,36]],mexuar:[[-29,1.65,3],[-29,3.7,-12]],
  kings:[[59,1.65,28],[59,3.5,8]],lindaraja:[[38,1.65,-9],[38,2,-24]],
  alcazaba:[[-151,1.65,27],[-225,6,25]],vela:[[-229,27.65,23],[-100,5,30]],
  partal:[[92.8,1.65,16],[101,5,-18]],generalife:[[375.5,33.65,-32],[370,35,-75]],
  carlos:[[-40,1.65,76],[-40,6,52]],justice:[[-55,1.65,148],[-55,7,123]],
  overview:[[-350,280,400],[80,0,20]]
};
for(const p of PLACES){[p.p,p.t]=views[p.id];}
export const TOUR = ['lions','myrtles','ambassadors','sisters','abencerrajes','mexuar','kings','lindaraja','alcazaba','vela','partal','generalife','carlos','justice','overview'];
export const BY_ID = Object.fromEntries(PLACES.map(p=>[p.id,p]));
