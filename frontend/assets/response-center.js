(function(){
"use strict";
var shelters=[
{name:"Puri Coastal Shelter",district:"Puri",state:"Odisha",lat:19.8135,lng:85.8312,capacity:500,available:182,water:true,food:true,medical:true,accessible:true},
{name:"Gopalpur Cyclone Shelter",district:"Ganjam",state:"Odisha",lat:19.2676,lng:84.9050,capacity:420,available:96,water:true,food:true,medical:false,accessible:true},
{name:"Kakinada Relief Shelter",district:"Kakinada",state:"Andhra Pradesh",lat:16.9891,lng:82.2475,capacity:600,available:240,water:true,food:true,medical:true,accessible:false},
{name:"Srikakulam Safe Center",district:"Srikakulam",state:"Andhra Pradesh",lat:18.2969,lng:83.8973,capacity:350,available:140,water:true,food:false,medical:true,accessible:true},
{name:"Paradip Community Shelter",district:"Jagatsinghpur",state:"Odisha",lat:20.3160,lng:86.6080,capacity:450,available:210,water:true,food:true,medical:true,accessible:true},
{name:"Digha Emergency Shelter",district:"Purba Medinipur",state:"West Bengal",lat:21.6280,lng:87.5080,capacity:380,available:72,water:true,food:true,medical:false,accessible:true}
];
var sos=[
{id:"SOS-2026-000123",lat:19.80,lng:85.82,priority:"CRITICAL",people:6,medical:true,place:"Puri, Odisha"},
{id:"SOS-2026-000119",lat:19.28,lng:84.89,priority:"HIGH",people:12,medical:false,place:"Gopalpur, Odisha"},
{id:"SOS-2026-000131",lat:16.98,lng:82.25,priority:"MEDIUM",people:4,medical:false,place:"Kakinada, Andhra Pradesh"}
];
var map, markers={sos:[],shelters:[],risk:[],track:[]};
function markerIcon(emoji){return L.divIcon({className:"rc-marker",html:'<div style="font-size:26px">'+emoji+'</div>',iconSize:[30,30],iconAnchor:[15,15]});}
function initMap(){
 if(!window.L||!document.getElementById("responseMap"))return;
 map=L.map("responseMap").setView([18.7,83.8],6);
 L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"&copy; OpenStreetMap contributors"}).addTo(map);
 sos.forEach(function(s){var m=L.marker([s.lat,s.lng],{icon:markerIcon(s.priority==="CRITICAL"?"🔴":"🟠")}).addTo(map).bindPopup("<b>"+s.id+"</b><br>Priority: "+s.priority+"<br>People affected: "+s.people+"<br>"+s.place+"<br><b>Medical: "+(s.medical?"YES":"NO")+"</b>");markers.sos.push(m);});
 shelters.forEach(function(s){var m=L.marker([s.lat,s.lng],{icon:markerIcon("🏠")}).addTo(map).bindPopup("<b>"+s.name+"</b><br>"+s.district+", "+s.state+"<br>Available: "+s.available+" / "+s.capacity+"<br>✓ Water · "+(s.food?"✓ Food":"✕ Food")+" · "+(s.medical?"✓ Medical":"✕ Medical"));markers.shelters.push(m);});
 var cyclone=[{lat:15.8,lng:87.3},{lat:17.1,lng:86.0},{lat:18.4,lng:84.9},{lat:19.4,lng:84.0}];
 markers.track.push(L.polyline(cyclone,{dashArray:"8 8",weight:4}).addTo(map).bindPopup("<b>Predicted cyclone track</b><br>Demo ensemble · uncertainty not shown to scale"));
 L.marker(cyclone[0],{icon:markerIcon("🌀")}).addTo(map).bindPopup("<b>Active cyclone</b><br>Demo system · follow official IMD bulletins");
 var risk=L.polygon([[19.9,85.4],[19.6,86.3],[18.8,86.1],[18.7,85.5]],{color:"#d83a3a",fillOpacity:.16,weight:2}).addTo(map).bindPopup("<b>High impact risk zone</b><br>Demo layer");
 markers.risk.push(risk);
}
function setLayer(name){
 if(!map)return;
 ["sos","shelters","risk","track"].forEach(function(k){markers[k].forEach(function(m){if(name==="all"||name===k){if(!map.hasLayer(m))m.addTo(map)}else if(map.hasLayer(m))map.removeLayer(m);});});
 document.querySelectorAll(".map-controls button").forEach(function(b){b.classList.toggle("active",b.dataset.layer===name);});
}
function renderShelters(list){
 var box=document.getElementById("shelterList"); if(!box)return;
 box.innerHTML=list.map(function(s){return '<article class="shelter-card"><h3>'+s.name+'</h3><b>'+s.district+', '+s.state+'</b><p>Capacity: '+s.capacity+' · Available: <strong>'+s.available+'</strong></p><div class="shelter-meta"><span class="tag">'+(s.water?"✓ Water":"✕ Water")+'</span><span class="tag">'+(s.food?"✓ Food":"✕ Food")+'</span><span class="tag">'+(s.medical?"✓ Medical":"✕ Medical")+'</span><span class="tag">'+(s.accessible?"✓ Accessible":"Standard")+'</span></div><button class="btn outline" onclick="window.open(\'https://www.google.com/maps/dir/?api=1&destination='+s.lat+','+s.lng+'\',\'_blank\')">GET DIRECTIONS</button></article>';}).join("");
}
function distance(a,b,c,d){var R=6371,x=(c-a)*Math.PI/180,y=(d-b)*Math.PI/180;var q=Math.sin(x/2)**2+Math.cos(a*Math.PI/180)*Math.cos(c*Math.PI/180)*Math.sin(y/2)**2;return R*2*Math.atan2(Math.sqrt(q),Math.sqrt(1-q));}
function assess(){
 var coast=+document.getElementById("coastDistance").value||0,wind=+document.getElementById("riskWind").value||0,rain=+document.getElementById("riskRain").value||0,surge=+document.getElementById("riskSurge").value||0,v=document.getElementById("vulnerability").value;
 var score=Math.min(100,(wind/2)+(rain/8)+(surge*10)+Math.max(0,30-coast)+(v==="high"?15:v==="medium"?8:0));
 var level=score>=75?"EXTREME":score>=55?"HIGH":score>=30?"MODERATE":"LOW";
 var r=document.getElementById("riskResult");r.innerHTML='<span class="risk-ring">'+Math.round(score)+'</span><div><b>YOUR PROTOTYPE RISK</b><h3>'+level+'</h3><p>Wind '+wind+' km/h · Rain '+rain+' mm · Surge '+surge+' m · Coast '+coast+' km.</p><p><strong>Action:</strong> Follow official IMD/NDMA and local authority instructions. Move to a designated shelter if ordered.</p><small>Prototype score — not an official warning.</small></div>';
 document.getElementById("metricRisk").textContent=level;
}
function init(){
 initMap(); renderShelters(shelters);
 document.querySelectorAll(".map-controls button").forEach(function(b){b.onclick=function(){setLayer(b.dataset.layer)}});
 document.getElementById("riskForm").addEventListener("submit",function(e){e.preventDefault();assess()});
 document.getElementById("findShelters").onclick=function(){var q=document.getElementById("shelterSearch").value.toLowerCase().trim();renderShelters(shelters.filter(function(s){return !q||s.name.toLowerCase().includes(q)||s.district.toLowerCase().includes(q)||s.state.toLowerCase().includes(q)}))};
 document.getElementById("useLocation").onclick=function(){if(!navigator.geolocation)return alert("Location is not supported by this browser.");navigator.geolocation.getCurrentPosition(function(pos){var lat=pos.coords.latitude,lng=pos.coords.longitude;renderShelters(shelters.map(function(s){return Object.assign({},s,{distance:distance(lat,lng,s.lat,s.lng)})}).sort(function(a,b){return a.distance-b.distance}));if(map)map.setView([lat,lng],10);},function(){alert("Location permission was not granted. Search by district instead.")})};
 document.getElementById("enableNotifications").onclick=function(){var out=document.getElementById("notifyStatus");if(!("Notification" in window)){out.textContent="Browser notifications are not supported.";return}Notification.requestPermission().then(function(p){out.textContent=p==="granted"?"Browser alerts enabled on this device.":"Permission not granted.";if(p==="granted")new Notification("CycloTrack India",{body:"Alert notifications are enabled. Follow official warnings."})})};
 var lang=document.getElementById("botLanguage"),saved=localStorage.getItem("cyclotrack_bot_language");if(saved)lang.value=saved;lang.onchange=function(){localStorage.setItem("cyclotrack_bot_language",lang.value)};
}
document.addEventListener("DOMContentLoaded",init);
})();
