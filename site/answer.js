"use strict";
// Coordinates use the original page's proportions. The source image is unchanged;
// these vector overlays explain only the three examples selected for publication.
const examples = {
  attachment: {
    title: "Attaching part 3468", level: "Easy · Part connections",
    question: "Bolt 380571-S is used to attach part 3468 to what part?",
    answer: '<p class="answer-number">3397 (lower control arm)</p>',
    regions: [
      {label:"1", tone:"blue", polygon:"962,688 973,687 978,690 978,697 974,701 974,721 971,724 965,723 964,701 960,698 960,692", marker:[1060,660], target:[978,694], title:"Bolt 380571-S", text:"Find the bolt labeled 380571-S above the bent end of part 3468."},
      {label:"2", tone:"orange", path:"M 512,763 L 572,758 697,748 697,762 574,771 514,774 511,771 Z M 747,744 L 904,735 967,730 981,729 984,724 990,726 986,741 983,744 940,747 902,749 747,758 Z", marker:[838,654], target:[865,737], title:"3468 (strut rod)", text:"Follow the strut rod to its bent end. The assembly line runs downward from the bolt through this attachment point."},
      {label:"3", tone:"green", rect:[965,723,10,223], marker:[1140,770], target:[975,777], title:"Assembly guide line", text:"This thin line continues from the end of the bolt, through the strut rod’s attachment point and down through the lower control arm. It shows how the parts line up when assembled; it is not a separate part."},
      {label:"4", tone:"purple", polygon:"788,828 794,814 806,807 820,809 830,821 842,833 865,846 902,862 938,880 985,891 1012,897 1022,901 1026,910 1024,920 1013,930 984,939 960,945 940,946 935,939 898,913 860,888 843,871 836,872 797,845 788,839", marker:[1200,914], target:[1026,910], title:"3397 (lower control arm)", text:"Continue down that assembly line to the lower control arm. Its callout identifies it as 3397, which is the answer."},
    ],
  },
  hardware: {
    title: "A change in attachment hardware", level: "Medium · Catalog notation",
    question: "According to the diagram, what change(s) were made to the attachment hardware for part 18A017?",
    answer: '<ul><li>Nut <strong>33923-S</strong> was replaced by <strong>34392-S</strong>.</li><li>Bolt <strong>355471-S</strong> was replaced by <strong>378940-S</strong>.</li></ul>',
    regions: [
      {
        "label": "1",
        "tone": "blue",
        "polygon": "401.7,367.7 409.7,362.3 423.3,358 428,352 435.3,348.7 445,348.7 451.7,353.3 453.7,358 462,364 473,369.7 476.3,377.7 474.3,382 469.3,384 463.7,381.3 453.3,371.3 450.3,374.7 448.7,388 445,390.3 429,390 425.3,386 425.7,372 412.3,375 404,374 400.3,371.7",
        "marker": [
          274,
          320
        ],
        "target": [
          401,
          366
        ],
        "title": "18A017 (upper shock absorber bracket)",
        "text": "Find the three-legged mounting bracket above the shock absorber. The dated nut and bolt callouts refer to hardware that fastens this bracket to the car."
      },
      {
        "label": "2",
        "tone": "orange",
        "path": "M 348,197 h 187 v 35 h -187 Z M 348,239 h 174 v 30 h -174 Z M 463.3,334.7 L 468,332.7 L 474,333 L 477.7,335.3 L 478,338.7 L 479.7,341.3 L 478.3,344.3 L 472.3,344 L 467,343 L 463,342.3 Z",
        "marker": [
          435,
          143
        ],
        "target": [
          435,
          197
        ],
        "title": "Nut: 33923-S → 34392-S",
        "text": "The note above the bracket lists 33923-S before March 1, 1966 and 34392-S from that date onward. Its leader points to the nut on the bracket’s attachment line. This is the first replacement."
      },
      {
        "label": "3",
        "tone": "purple",
        "path": "M 510,433 h 196 v 72 h -196 Z M 468.7,508.3 L 472,506 L 475,507.7 L 475,517 L 478.7,520 L 478.7,523.7 L 474.7,526.3 L 469.7,526.7 L 463.3,523.3 L 463,519.3 L 467,517 Z",
        "marker": [
          641,
          366
        ],
        "target": [
          630,
          433
        ],
        "title": "Bolt: 355471-S → 378940-S",
        "text": "The lower note gives the same changeover date for the bolt: 355471-S before March 1, 1966, then 378940-S. Include both the nut change and the bolt change in the answer."
      }
    ],
  },
  assembly: {
    title: "The parts along bolt 5495", level: "Hard · Assembly order",
    question: "Part 5495 passes through a series of other parts. List all the part numbers for these parts, in order from top to bottom as installed on the vehicle. Do not include 5495 itself.",
    partNames: {"378866-S":"nut","371169-S":"washer","55490":"bushing / insulator","5482":"stabilizer bar","5490":"tubular spacer","3397":"lower control arm"},
    parts: ["378866-S","371169-S","55490","5482","55490","371169-S","5490","371169-S","55490","3397","5A491","55490","371169-S"],
    regions: [
      {
        "label": "5495",
        "tone": "blue",
        "path": "M 929,1040.3 L 933.7,1039.7 L 936.3,1043 L 937,1137.3 L 940,1142.3 L 940,1147.7 L 934.7,1151.7 L 925.7,1150.7 L 921,1147.7 L 921.3,1142 L 926,1139 L 926,1044 Z",
        "marker": [
          1020,
          1220
        ],
        "target": [
          937,
          1130
        ],
        "title": "5495 (stabilizer link bolt)",
        "text": "Start with the long bolt below the lower control arm. It holds the stabilizer-link stack together. The question excludes 5495 itself and asks for the other parts in their installed order, from top to bottom."
      },
      {
        "label": "G",
        "tone": "green",
        "path": "M 513.5,1090 L 513.5,1177.4 L 515.2,1182.5 L 520.8,1182.5 L 568.5,1148 L 571.5,1145.8 L 571.9,1145.9 L 572.5,1148.2 L 570.5,1189.9 L 568.5,1229.9 L 565.5,1330 L 565.5,1391.2 L 567.1,1399.1 L 576.9,1396.3 L 850.3,1259.1 L 855.1,1255.5 L 857.5,1248.4 L 857.5,886 L 852.5,886 L 852.5,1247.6 L 850.9,1252.5 L 847.7,1254.9 L 575.1,1391.7 L 570.9,1392.9 L 570.5,1390.8 L 570.5,1330 L 573.5,1230.1 L 575.5,1190.1 L 577.5,1147.8 L 576.1,1142.1 L 570.5,1140.2 L 565.5,1144 L 519.2,1177.5 L 518.8,1177.5 L 518.5,1176.6 L 518.5,1090 Z",
        "guide": true,
        "marker": [
          755,
          1410
        ],
        "target": [
          740,
          1314
        ],
        "title": "Assembly guide line — not an answer item",
        "text": "Follow the thin line between the separated groups. It bends from the upper stack to the end of the stabilizer bar, then runs down below the lower stack and back up toward the lower control arm. Those bends make room on the page; they do not change the installed order. The shaded strip marks the guide, not another part."
      },
      {
        "label": "1–3",
        "tone": "orange",
        "path": "M 512.7,1074.3 L 519,1073 L 524.3,1076 L 526.3,1082 L 524.7,1088 L 518.7,1090.7 L 512,1089.7 L 508.7,1086 L 509,1080 Z M 504.7,1110.7 L 511.7,1107.7 L 521,1107.7 L 529,1110.3 L 531.7,1114.7 L 529.3,1119.7 L 521.7,1122.3 L 512,1122.3 L 505,1119 L 502.3,1115 Z M 506,1133.7 L 514.7,1130.7 L 522.3,1131.3 L 528.3,1134.7 L 528.3,1141.7 L 524.7,1148.3 L 517,1151 L 509,1148.3 L 505.7,1144.3 L 502.3,1139.7 L 502.7,1136.7 Z",
        "marker": [
          355,
          1070
        ],
        "target": [
          509,
          1080
        ],
        "title": "Upper nut, washer and bushing",
        "text": "Begin above the bar: 378866-S (nut), 371169-S (washer), then 55490 (rubber bushing, called an insulator in the catalog). The three separate outlines identify the three physical pieces."
      },
      {
        "label": "4",
        "tone": "purple",
        "path": "M 177,1072 L 183,1073 324,1180 Q 332,1186 342,1186 L 405,1186 420,1190 419,1202 405,1200 338,1200 Q 328,1200 319,1194 L 180,1087 176,1081 Z M 451,1209 Q 459,1214 470,1214 L 510,1214 Q 524,1214 534,1204 L 560,1178 564,1170 Q 573,1160 582,1167 L 584,1175 580,1182 570,1184 542,1213 Q 529,1224 513,1224 L 467,1225 451,1221 Z",
        "marker": [
          222,
          1250
        ],
        "target": [
          261,
          1132
        ],
        "title": "5482 (stabilizer bar)",
        "text": "Next is the hole at the end of the stabilizer bar, also called the anti-roll bar. The highlight follows the bar, leaving its separate mounting insulator unshaded. Use the main assembly, not the Mustang GT detail at the far left."
      },
      {
        "label": "5–9",
        "tone": "teal",
        "path": "M 563.3,1201.3 L 571.3,1199 L 579,1200.3 L 583,1204.7 L 585,1210.7 L 582.3,1216.7 L 576.7,1221.7 L 569,1222 L 561,1218.3 L 558.3,1212.3 L 559.3,1206.3 Z M 562.3,1229.7 L 571,1227 L 579.3,1229.7 L 584,1233.3 L 583.7,1238.7 L 577.7,1243.3 L 569,1244.7 L 562.3,1242 L 558.3,1238 L 558.7,1233.7 Z M 564.7,1250 L 570,1247.7 L 576,1249.7 L 577,1254.3 L 576.7,1279.7 L 573.3,1283.7 L 567.7,1283 L 563.3,1280.3 L 563.3,1253.7 Z M 560.3,1291.7 L 568.3,1289 L 577.3,1290.3 L 583.7,1294.3 L 584.3,1298.3 L 580.3,1302.3 L 572.3,1304.3 L 563,1302.7 L 557,1299.3 L 555.3,1296 Z M 560.7,1311.3 L 568,1308.7 L 575.3,1310 L 580.3,1313 L 582.3,1318 L 580.7,1324.7 L 576,1329.3 L 569.3,1329.3 L 562.7,1327 L 557.3,1322.3 L 555.7,1317.3 L 557.3,1314 Z",
        "marker": [
          700,
          1350
        ],
        "target": [
          582,
          1318
        ],
        "title": "Two bushings, two washers and a spacer",
        "text": "Below the bar, continue through 55490 (bushing), 371169-S (washer), 5490 (tubular spacer), another 371169-S washer, and another 55490 bushing. Repeated numbers here mean separate copies of the same part."
      },
      {
        "label": "10",
        "tone": "rose",
        "polygon": "788,828 794,814 806,807 820,809 830,821 842,833 865,846 902,862 938,880 985,891 1012,897 1022,901 1026,910 1024,920 1013,930 984,939 960,945 940,946 935,939 898,913 860,888 843,871 836,872 797,845 788,839",
        "marker": [
          1200,
          914
        ],
        "target": [
          1026,
          910
        ],
        "title": "3397 (lower control arm)",
        "text": "Follow the long return leg of the assembly guide up to the lower control arm. The link passes through 3397 after the five pieces below the stabilizer bar. Do not jump directly from the left-hand stack to the bolt."
      },
      {
        "label": "11–13",
        "tone": "ochre",
        "path": "M 923.3,963 L 930.3,960.3 L 936.3,962.7 L 941.3,968 L 944.7,972.7 L 944.7,977.7 L 939.7,981.7 L 931.7,983.7 L 922.3,981.7 L 917.3,977.7 L 917,972.7 L 919.7,968 Z M 922.3,992.7 L 930.3,989.7 L 937,991.3 L 942,994.7 L 944.7,1000.7 L 944.3,1007 L 938.7,1012.3 L 932.3,1013.7 L 924.3,1011.3 L 919,1007 L 918,999.7 Z M 921.7,1018.7 L 930,1016.3 L 937,1017.7 L 942.3,1021 L 944.7,1025.3 L 943,1030 L 936.3,1033.3 L 927.7,1033.7 L 919.3,1030.7 L 916,1026.3 L 917.3,1022 Z",
        "marker": [
          1190,
          1000
        ],
        "target": [
          945,
          1002
        ],
        "title": "Final three pieces below the arm",
        "text": "Finish with 5A491, then 55490 (bushing), then 371169-S (washer). They are shown between the lower control arm and bolt 5495. This is the fourth bushing and fourth washer in the answer."
      }
    ],
  },
};

const exampleKey = new URLSearchParams(location.search).get("example");
const example = Object.hasOwn(examples, exampleKey) ? examples[exampleKey] : null;
if (!example) {
  document.querySelector("#answer-error").hidden = false;
} else {
  document.title = `${example.title} — Part Catalog Bench`;
  document.querySelector("#answer-title").textContent = example.title;
  document.querySelector("#answer-level").textContent = example.level;
  document.querySelector("#answer-question").textContent = example.question;
  document.querySelector("#correct-answer").innerHTML = example.parts
    ? `<ol class="answer-part-list">${example.parts.map(p=>`<li>${p}${example.partNames?.[p] ? `<span class="answer-part-name">${example.partNames[p]}</span>` : ''}</li>`).join("")}</ol><p class="answer-note">Repeated part numbers are intentional: there are several copies of the same washers and bushings. The diagram labels 1–13 match this list; G is the assembly guide and is not an answer item.</p>`
    : example.answer;
  document.querySelector("#answer-highlights").innerHTML = example.regions.map(r =>
    `<line class="diagram-leader tone-${r.tone || 'default'}" x1="${r.marker[0]}" y1="${r.marker[1]}" x2="${r.target[0]}" y2="${r.target[1]}" vector-effect="non-scaling-stroke"/>`
  ).join("") + example.regions.map(r => {
    const attributes = `class="region-outline${r.guide ? ' assembly-guide' : ''} tone-${r.tone || 'default'}" vector-effect="non-scaling-stroke"`;
    if (r.path) return `<path d="${r.path}" ${attributes}/>`;
    if (r.rect) return `<rect x="${r.rect[0]}" y="${r.rect[1]}" width="${r.rect[2]}" height="${r.rect[3]}" ${attributes}/>`;
    return `<polygon points="${r.polygon}" ${attributes}/>`;
  }).join("");
  document.querySelector("#answer-markers").innerHTML = example.regions.map((r,i)=>`<a class="diagram-marker tone-${r.tone || 'default'}" href="#step-${i}" style="left:${r.marker[0]/1387*100}%;top:${r.marker[1]/1791*100}%" aria-label="${r.title}">${r.label}</a>`).join("");
  document.querySelector("#answer-steps").innerHTML = example.regions.map((r,i)=>`<section id="step-${i}" class="answer-step"><h3><span class="step-label tone-${r.tone || 'default'}">${r.label}</span>${r.title}</h3><p>${r.text}</p></section>`).join("");
  document.querySelector("#answer-content").hidden = false;
  document.querySelector("#diagram-zoom").addEventListener("change",event=>{
    document.querySelector("#annotated-diagram").style.width=`${Number(event.target.value)*100}%`;
  });
  document.querySelector("#toggle-highlights").addEventListener("click",event=>{
    const button=event.currentTarget;
    const shown=button.getAttribute("aria-pressed")!=="true";
    button.setAttribute("aria-pressed",String(shown));
    button.textContent=shown?"Hide highlights":"Show highlights";
    document.querySelector("#answer-highlights").style.display=shown?"":"none";
    document.querySelector("#answer-markers").hidden=!shown;
  });
}
