/* ============================================================
   CycloTrack India — Cyclone Info Chatbot Widget
   ------------------------------------------------------------
   Self-contained chat widget backed by a real AI model (Claude,
   via the CycloneAI FastAPI backend's /api/chat endpoint). It can
   answer open-ended questions about tropical cyclones — not just
   phrasings that match a hardcoded list — and remembers the last
   few turns of the conversation for follow-ups.

   HOW TO ADD TO A PAGE:
     <link rel="stylesheet" href="assets/chatbot.css">
     <script src="assets/chatbot.js" defer></script>

   POINTING AT YOUR BACKEND:
     By default the widget calls http://localhost:8000/api/chat
     (see backend/README.md to run that server). To point at a
     different address (e.g. a deployed backend), set this BEFORE
     loading chatbot.js:

       <script>window.CYCLOBOT_API_URL = "https://your-api.example.com/api/chat";</script>
       <script src="assets/chatbot.js" defer></script>

   OFFLINE FALLBACK:
     If the backend is unreachable, not yet running, or returns an
     error (e.g. no ANTHROPIC_API_KEY configured), the widget falls
     back to the small local KNOWLEDGE_BASE below via keyword
     matching, so the demo still works without a server. Once the
     backend responds successfully at least once, the widget knows
     "AI mode" is live and keeps using it for the rest of the
     session.
   ============================================================ */

(function () {
    'use strict';

    /* ------------------------------------------------------------
       1. KNOWLEDGE BASE
       Each entry: id, keywords (matched against lowercased input),
       and an HTML-ish response string. Order matters only as a
       tiebreaker; matching is by keyword-overlap score.
    ------------------------------------------------------------ */
    var KNOWLEDGE_BASE = [
        {
            id: 'greeting',
            keywords: ['hi', 'hello', 'hey', 'good morning', 'good evening', 'namaste', 'yo'],
            response: "Hello! I'm the CycloTrack cyclone info assistant. Ask me anything about tropical cyclones — what they are, how they form, why they occur, their history in India, categories, or safety. Where would you like to start?"
        },
        {
            id: 'what_is_cyclone',
            keywords: ['what is a cyclone', 'what is cyclone', 'define cyclone', 'meaning of cyclone', 'cyclone definition', 'explain cyclone'],
            response: "A <strong>tropical cyclone</strong> is a large, rotating storm system that forms over warm ocean waters near the tropics. It's powered by heat released when moist air rises and condenses, and it rotates around a low-pressure center. Depending on where in the world it forms, the very same phenomenon is called a <em>cyclone</em> (Indian Ocean, South Pacific), a <em>hurricane</em> (Atlantic, Northeast Pacific), or a <em>typhoon</em> (Northwest Pacific)."
        },
        {
            id: 'formation',
            keywords: ['how does a cyclone form', 'how do cyclones form', 'how cyclone forms', 'cyclone formation', 'how is a cyclone formed', 'genesis'],
            response: "Cyclones form through a chain of events: <ul>" +
                "<li>Warm ocean water (usually above 26.5°C) evaporates, feeding moist, warm air upward.</li>" +
                "<li>As this air rises and cools, water vapor condenses into clouds, releasing latent heat that fuels the storm further.</li>" +
                "<li>Air rushes in near the surface to replace the rising air, and the Earth's rotation (Coriolis force) makes this inflow spin.</li>" +
                "<li>If conditions stay favorable, the spinning thunderstorm cluster organizes into a well-defined low-pressure system with a calm 'eye' at the center.</li>" +
                "</ul>Ask me 'why do cyclones occur' if you want the specific conditions needed."
        },
        {
            id: 'why_occurs',
            keywords: ['why do cyclones occur', 'why does a cyclone occur', 'why cyclone occurs', 'conditions for cyclone', 'causes of cyclone', 'what causes a cyclone'],
            response: "Cyclones need several conditions to occur together: <ul>" +
                "<li><strong>Warm sea surface temperature</strong> — generally above 26.5°C, down to at least 50m depth, to supply energy.</li>" +
                "<li><strong>High humidity</strong> in the mid-troposphere to sustain thunderstorm clusters.</li>" +
                "<li><strong>Coriolis force</strong> — enough distance from the equator (usually beyond ~5°) for the Earth's rotation to make air spin; this is why cyclones almost never form right on the equator.</li>" +
                "<li><strong>Low vertical wind shear</strong> — winds shouldn't change too much in speed/direction with height, or the storm gets torn apart.</li>" +
                "<li><strong>A pre-existing weather disturbance</strong>, such as a cluster of thunderstorms or a low-pressure area, to act as a seed.</li>" +
                "</ul>When all of these line up, a low-pressure system can intensify into a full tropical cyclone."
        },
        {
            id: 'structure',
            keywords: ['structure of cyclone', 'parts of a cyclone', 'eye of the storm', 'eyewall', 'rainbands', 'anatomy of cyclone'],
            response: "A mature cyclone has three key parts: <ul>" +
                "<li><strong>The eye</strong> — a calm, often clear region at the very center, typically 30–65 km wide, with low pressure and light winds.</li>" +
                "<li><strong>The eyewall</strong> — a ring of intense thunderstorms surrounding the eye, where the strongest winds and heaviest rain occur.</li>" +
                "<li><strong>Rainbands</strong> — spiral bands of clouds and showers extending outward from the eyewall, which can reach hundreds of kilometers.</li>" +
                "</ul>This spiral structure is exactly what shows up so clearly in satellite imagery."
        },
        {
            id: 'why_rotate',
            keywords: ['why do cyclones rotate', 'why do cyclones spin', 'coriolis', 'clockwise', 'anticlockwise', 'counterclockwise', 'direction of rotation'],
            response: "Cyclones spin because of the <strong>Coriolis force</strong>, caused by Earth's rotation. In the <strong>Northern Hemisphere</strong> (including the Bay of Bengal and Arabian Sea), cyclones rotate <strong>counter-clockwise</strong>. In the <strong>Southern Hemisphere</strong>, they rotate <strong>clockwise</strong>. The Coriolis force is essentially zero at the equator, which is also why cyclones almost never form within about 5° latitude of it."
        },
        {
            id: 'stages_imd',
            keywords: ['stages of cyclone', 'imd classification', 'depression', 'deep depression', 'severe cyclonic storm', 'cyclone classification india', 'imd scale', 'cyclonic storm stages'],
            response: "India Meteorological Department (IMD) classifies systems in the North Indian Ocean by sustained wind speed: <ul>" +
                "<li><strong>Low Pressure Area</strong> — below 31 km/h</li>" +
                "<li><strong>Depression</strong> — 31–50 km/h</li>" +
                "<li><strong>Deep Depression</strong> — 51–62 km/h</li>" +
                "<li><strong>Cyclonic Storm</strong> — 63–88 km/h</li>" +
                "<li><strong>Severe Cyclonic Storm</strong> — 89–117 km/h</li>" +
                "<li><strong>Very Severe Cyclonic Storm</strong> — 118–166 km/h</li>" +
                "<li><strong>Extremely Severe Cyclonic Storm</strong> — 167–221 km/h</li>" +
                "<li><strong>Super Cyclonic Storm</strong> — above 221 km/h</li>" +
                "</ul>This is different from the Saffir-Simpson scale used for Atlantic hurricanes — ask me about that if you'd like a comparison."
        },
        {
            id: 'saffir_simpson',
            keywords: ['saffir-simpson', 'saffir simpson', 'hurricane category', 'category 1', 'category 5', 'hurricane scale'],
            response: "The <strong>Saffir-Simpson Hurricane Wind Scale</strong> is used mainly for Atlantic/Pacific hurricanes, rating them Category 1 to 5 by sustained wind speed: <ul>" +
                "<li><strong>Cat 1:</strong> 119–153 km/h</li>" +
                "<li><strong>Cat 2:</strong> 154–177 km/h</li>" +
                "<li><strong>Cat 3 (Major):</strong> 178–208 km/h</li>" +
                "<li><strong>Cat 4 (Major):</strong> 209–251 km/h</li>" +
                "<li><strong>Cat 5 (Major):</strong> 252 km/h and above</li>" +
                "</ul>IMD's scale for the North Indian Ocean uses different bands and names (see 'IMD classification') — the two aren't directly interchangeable, though comparisons are often drawn loosely."
        },
        {
            id: 'naming',
            keywords: ['cyclone names', 'how are cyclones named', 'naming of cyclones', 'who names cyclones', 'name list'],
            response: "Tropical cyclones are named by regional bodies coordinated under the World Meteorological Organization (WMO). For the North Indian Ocean, 13 member countries — including India, Bangladesh, Pakistan, Sri Lanka, Thailand, and others — each contribute names to a rotating list maintained by IMD (the Regional Specialized Meteorological Centre, New Delhi). Names are picked in sequence as storms form, are kept short and easy to communicate, and a name is retired if the storm was especially deadly or destructive."
        },
        {
            id: 'terminology_regions',
            keywords: ['cyclone vs hurricane', 'difference between cyclone and hurricane', 'typhoon vs cyclone', 'hurricane vs typhoon', 'same as hurricane'],
            response: "Cyclone, hurricane, and typhoon are the <strong>same weather phenomenon</strong> — a rotating tropical storm system — just named differently by region: <ul>" +
                "<li><strong>Cyclone</strong> — North Indian Ocean, South Pacific, Southeast Indian Ocean</li>" +
                "<li><strong>Hurricane</strong> — Atlantic Ocean and Northeast Pacific</li>" +
                "<li><strong>Typhoon</strong> — Northwest Pacific (East/Southeast Asia)</li>" +
                "</ul>The physics behind all of them is identical."
        },
        {
            id: 'season_india',
            keywords: ['cyclone season india', 'when do cyclones occur', 'cyclone season', 'months', 'time of year', 'pre-monsoon', 'post-monsoon'],
            response: "In the North Indian Ocean, cyclones cluster in two windows: <ul>" +
                "<li><strong>Pre-monsoon (April–June)</strong> — fewer but sometimes very intense storms.</li>" +
                "<li><strong>Post-monsoon (October–December)</strong> — the more active season, especially in the Bay of Bengal.</li>" +
                "</ul>The Bay of Bengal sees roughly 4–5 times more cyclones than the Arabian Sea, largely because of warmer, more consistent sea surface temperatures and moisture inflow — though Arabian Sea activity has been rising in recent decades."
        },
        {
            id: 'history_india',
            keywords: ['history of cyclones in india', 'famous cyclones', 'past cyclones', 'notable cyclones', 'odisha super cyclone', 'cyclone fani', 'cyclone amphan', 'major cyclones india'],
            response: "Some of the most significant cyclones to hit India include: <ul>" +
                "<li><strong>Odisha Super Cyclone (1999)</strong> — Category 5-equivalent, one of the most powerful storms ever recorded in the North Indian Ocean.</li>" +
                "<li><strong>Cyclone Phailin (2013)</strong> — a very severe cyclonic storm; large-scale evacuations kept the death toll far lower than in 1999.</li>" +
                "<li><strong>Cyclone Hudhud (2014)</strong> — struck Visakhapatnam, Andhra Pradesh, with major infrastructure damage.</li>" +
                "<li><strong>Cyclone Fani (2019)</strong> — an extremely severe cyclonic storm that hit Odisha, again with a highly effective evacuation response.</li>" +
                "<li><strong>Cyclone Amphan (2020)</strong> — one of the costliest cyclones on record for the North Indian Ocean, affecting West Bengal and Bangladesh.</li>" +
                "<li><strong>Cyclone Nisarga (2020)</strong> — a rarer Arabian Sea system that made landfall near Maharashtra.</li>" +
                "</ul>Check the 'History' page on this site for a fuller timeline."
        },
        {
            id: 'deadliest_global',
            keywords: ['deadliest cyclone', 'worst cyclone ever', 'most deadly storm', '1970 bhola', 'bhola cyclone'],
            response: "The <strong>1970 Bhola Cyclone</strong>, which struck East Pakistan (now Bangladesh) and India's West Bengal coast, is considered the deadliest tropical cyclone on record, with an estimated death toll in the hundreds of thousands. It's a major reason the region invested heavily afterward in early-warning systems and cyclone shelters — steps that have sharply reduced casualties in more recent storms of similar strength."
        },
        {
            id: 'tracking',
            keywords: ['how are cyclones tracked', 'how do we predict cyclones', 'cyclone prediction', 'satellite tracking', 'insat', 'doppler radar', 'forecasting'],
            response: "Cyclones are tracked and forecast using a mix of tools: <ul>" +
                "<li><strong>Geostationary satellites</strong> (like India's INSAT series) provide continuous imagery of cloud patterns and storm structure.</li>" +
                "<li><strong>Doppler Weather Radars</strong> along the coast track rainfall intensity and wind fields at close range.</li>" +
                "<li><strong>Ocean buoys and ships</strong> measure sea surface temperature, pressure, and wave height.</li>" +
                "<li><strong>Numerical weather prediction models</strong> simulate the atmosphere to forecast track and intensity days in advance.</li>" +
                "<li><strong>AI/ML models</strong> (like the kind this project is built around) increasingly help detect, classify, and predict cyclone patterns faster from multi-source satellite data.</li>" +
                "</ul>"
        },
        {
            id: 'warning_system',
            keywords: ['warning system', 'colour code', 'color code', 'imd alert', 'red alert', 'orange alert', 'yellow alert'],
            response: "IMD issues cyclone warnings using a color-coded system, similar to general weather alerts: <ul>" +
                "<li><strong>Green</strong> — No warning, normal conditions.</li>" +
                "<li><strong>Yellow</strong> — Be aware; a system is being watched.</li>" +
                "<li><strong>Orange</strong> — Be prepared; significant impact likely, authorities begin precautionary action.</li>" +
                "<li><strong>Red</strong> — Take action; severe impact expected, evacuations and emergency measures are activated.</li>" +
                "</ul>Bulletins are issued at regular intervals as a system approaches the coast, along with expected landfall time, location, and intensity."
        },
        {
            id: 'impacts',
            keywords: ['effects of cyclone', 'impact of cyclone', 'damage caused by cyclone', 'storm surge', 'what happens during a cyclone'],
            response: "Cyclones cause damage through several combined effects: <ul>" +
                "<li><strong>Storm surge</strong> — an abnormal rise in sea level pushed ashore by the storm's winds, often the single biggest cause of casualties and coastal flooding.</li>" +
                "<li><strong>High winds</strong> — can destroy weak structures, uproot trees, and down power lines.</li>" +
                "<li><strong>Heavy rainfall</strong> — leads to inland flooding and landslides, sometimes well after the storm has weakened.</li>" +
                "<li><strong>Agricultural and economic loss</strong> — crops, fisheries, and infrastructure near the coast are especially vulnerable.</li>" +
                "</ul>"
        },
        {
            id: 'safety',
            keywords: ['safety tips', 'what to do during a cyclone', 'how to stay safe', 'precautions', 'dos and donts', 'evacuation', 'prepare for cyclone'],
            response: "General cyclone safety guidance: <ul>" +
                "<li><strong>Before:</strong> Follow official IMD/NDMA bulletins, keep emergency supplies (food, water, torch, first-aid, documents) ready, know your nearest cyclone shelter.</li>" +
                "<li><strong>During:</strong> Stay indoors and away from windows, avoid coastal areas and low-lying regions prone to storm surge, don't go out during the 'eye' — winds return violently from the opposite direction.</li>" +
                "<li><strong>After:</strong> Avoid flooded or debris-strewn roads, watch for downed power lines, wait for an official all-clear before returning to evacuated areas.</li>" +
                "</ul>Always prioritize official evacuation orders from local authorities and IMD/NDMA over general guidance like this."
        },
        {
            id: 'dissipation',
            keywords: ['why do cyclones weaken', 'cyclone dissipation', 'why does a cyclone die out', 'why do cyclones weaken over land'],
            response: "Cyclones weaken (dissipate) mainly when their energy source is cut off: <ul>" +
                "<li><strong>Moving over land</strong> cuts off the warm ocean moisture supply and increases surface friction, rapidly weakening the storm.</li>" +
                "<li><strong>Moving over cooler water</strong> reduces the heat and moisture available to sustain it.</li>" +
                "<li><strong>Strong vertical wind shear</strong> can tilt and disrupt the storm's structure.</li>" +
                "<li><strong>Interaction with dry air</strong> can choke off the thunderstorm activity that powers the system.</li>" +
                "</ul>"
        },
        {
            id: 'climate_change',
            keywords: ['climate change', 'global warming', 'are cyclones getting worse', 'more intense cyclones'],
            response: "Scientific studies broadly indicate that while the total number of tropical cyclones globally may not be rising sharply, <strong>a warming ocean is associated with a higher proportion of storms reaching high intensity</strong>, faster rapid-intensification events, and heavier rainfall rates within storms. Sea-level rise also makes storm surge more damaging along coastlines. Research on regional trends (like the Arabian Sea and Bay of Bengal specifically) is still an active area of study."
        },
        {
            id: 'tornado_vs_cyclone',
            keywords: ['tornado vs cyclone', 'difference between tornado and cyclone', 'is a tornado a cyclone'],
            response: "Tropical cyclones and tornadoes are both rotating storms but very different in scale and origin: <ul>" +
                "<li><strong>Cyclones</strong> form over warm oceans, span hundreds of kilometers, and last days.</li>" +
                "<li><strong>Tornadoes</strong> form over land from severe thunderstorms, are usually under a kilometer wide, and last minutes to a couple of hours.</li>" +
                "</ul>A landfalling cyclone can, however, spawn tornadoes as a secondary effect."
        },
        {
            id: 'about_project',
            keywords: ['what is this website', 'what is this project', 'what does this site do', 'cyclotrack', 'about this app', 'what can you do'],
            response: "This site, <strong>CycloTrack India</strong>, is built for Smart India Hackathon 2026 (Problem SIH26070, Ministry of Earth Sciences) to detect, classify, and predict tropical cyclone patterns using AI/ML on multi-source satellite data. I'm the info assistant — ask me anything about what cyclones are, how and why they form, their history, categories, and safety, and I'll do my best to explain."
        },
        {
            id: 'thanks',
            keywords: ['thank you', 'thanks', 'thank u', 'appreciate it', 'thx'],
            response: "You're welcome! Feel free to ask about anything else — formation, categories, past cyclones, safety, or how forecasting works."
        }
    ];

    var FALLBACK_RESPONSE = "I'm not sure about that one yet — I'm focused on general cyclone knowledge (formation, causes, categories, history, tracking, and safety). Try rephrasing, or tap one of the suggestions below.";

    var OFFLINE_NOTE = "(Running in offline demo mode — the AI backend isn't reachable right now, so I'm answering from a small built-in knowledge base instead of thinking freely. See backend/README.md to enable full AI mode.)";

    var QUICK_CHIPS = [
        "What is a cyclone?",
        "How do cyclones form?",
        "Cyclone history in India",
        "Safety tips"
    ];

    /* ------------------------------------------------------------
       1b. AI BACKEND CONFIG
       CYCLOBOT_API_URL can be set on window before this script
       loads to point at a deployed backend; defaults to local dev.
    ------------------------------------------------------------ */
    var API_URL = (typeof window !== 'undefined' && window.CYCLOBOT_API_URL) || 'http://localhost:8000/api/chat';
    var aiConfirmedLive = false;   // true once the backend has answered successfully at least once
    var offlineNoteShown = false;  // only mention offline mode once per session
    var conversationHistory = [];  // [{role: 'user'|'assistant', content: string}], capped below
    var MAX_HISTORY_MESSAGES = 16;

    function pushHistory(role, content) {
        conversationHistory.push({ role: role, content: content });
        if (conversationHistory.length > MAX_HISTORY_MESSAGES) {
            conversationHistory = conversationHistory.slice(-MAX_HISTORY_MESSAGES);
        }
    }

    function stripHtml(html) {
        var tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }

    // Real AI call to the FastAPI backend (Claude under the hood).
    function askAiBackend(userText) {
        return fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText, history: conversationHistory })
        }).then(function (res) {
            if (!res.ok) throw new Error('Backend responded with ' + res.status);
            return res.json();
        }).then(function (data) {
            if (!data || typeof data.reply !== 'string' || !data.reply.trim()) {
                throw new Error('Empty reply from backend');
            }
            aiConfirmedLive = true;
            return data.reply;
        });
    }

    // Offline fallback using the local keyword-matched knowledge base.
    function offlineReply(userText) {
        var entry = matchIntent(userText);
        var reply = entry ? entry.response : FALLBACK_RESPONSE;
        if (!offlineNoteShown) {
            offlineNoteShown = true;
            reply += '<br><br><span class="cycai-offline-note">' + OFFLINE_NOTE + '</span>';
        }
        return reply;
    }

    /* ------------------------------------------------------------
       2. INTENT MATCHING
       Simple, dependency-free keyword-overlap scorer. Picks the
       knowledge-base entry whose keyword phrases best match the
       user's message.
    ------------------------------------------------------------ */
    function normalize(text) {
        return text.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function matchIntent(userText) {
        var input = normalize(userText);
        if (!input) return null;

        var inputWords = input.split(' ');
        var bestEntry = null;
        var bestScore = 0;

        for (var i = 0; i < KNOWLEDGE_BASE.length; i++) {
            var entry = KNOWLEDGE_BASE[i];
            var score = 0;

            for (var j = 0; j < entry.keywords.length; j++) {
                var phrase = entry.keywords[j];
                if (input.indexOf(phrase) !== -1) {
                    // Whole-phrase match is a strong signal, weighted by phrase length
                    score += phrase.split(' ').length * 3;
                    continue;
                }
                // Partial word-overlap match
                var phraseWords = phrase.split(' ');
                var overlap = 0;
                for (var k = 0; k < phraseWords.length; k++) {
                    if (phraseWords[k].length > 2 && inputWords.indexOf(phraseWords[k]) !== -1) {
                        overlap++;
                    }
                }
                if (overlap > 0) score += overlap;
            }

            if (score > bestScore) {
                bestScore = score;
                bestEntry = entry;
            }
        }

        return bestScore >= 2 ? bestEntry : null;
    }

    /* ------------------------------------------------------------
       3. RESPONSE HOOK
       Tries the real AI backend first (open-ended, remembers
       context). Falls back to the local keyword-matched knowledge
       base if the backend errors out or isn't running, so the
       widget degrades gracefully instead of breaking.
    ------------------------------------------------------------ */
    function getBotReply(userText) {
        return askAiBackend(userText).catch(function (err) {
            console.warn('[CycloBot] AI backend unavailable, using offline fallback:', err && err.message);
            // Small delay so the offline fallback still feels like it "thought" about it,
            // rather than snapping back suspiciously instantly.
            return new Promise(function (resolve) {
                setTimeout(function () { resolve(offlineReply(userText)); }, 350 + Math.random() * 350);
            });
        });
    }

    /* ------------------------------------------------------------
       4. WIDGET UI
    ------------------------------------------------------------ */
    var ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.5 0 10-4 10-9s-4.5-9-10-9-10 4-10 9c0 2 .7 3.9 2 5.4L3 22l5.2-1.6c1.2.4 2.5.6 3.8.6Z"></path></svg>';
    var ICON_STORM = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 0-7 7c0 3 2 5 2 5h10s2-2 2-5a7 7 0 0 0-7-7Z"></path><path d="M8 14v2a4 4 0 0 0 8 0v-2"></path><path d="M10 20v1"></path><path d="M14 20v1"></path></svg>';
    var ICON_CLOSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>';
    var ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"></path><path d="M22 2 11 13"></path></svg>';

    function buildWidget() {
        var root = document.createElement('div');
        root.id = 'cycai-widget';
        root.innerHTML =
            '<button class="cycai-launcher" id="cycaiLauncher" aria-label="Open cyclone info chatbot">' +
                ICON_CHAT + '<span class="cycai-badge"></span>' +
            '</button>' +
            '<div class="cycai-panel" id="cycaiPanel">' +
                '<div class="cycai-header">' +
                    '<div class="cycai-header-icon">' + ICON_STORM + '</div>' +
                    '<div class="cycai-header-text">' +
                        '<div class="cycai-header-title">Cyclo<span>Bot</span></div>' +
                        '<div class="cycai-header-sub"><span class="cycai-status-dot"></span>Cyclone Info Assistant</div>' +
                    '</div>' +
                    '<button class="cycai-close" id="cycaiClose" aria-label="Close chat">' + ICON_CLOSE + '</button>' +
                '</div>' +
                '<div class="cycai-body" id="cycaiBody"></div>' +
                '<div class="cycai-chips" id="cycaiChips"></div>' +
                '<div class="cycai-input-row">' +
                    '<input class="cycai-input" id="cycaiInput" type="text" placeholder="Ask about cyclones…" autocomplete="off">' +
                    '<button class="cycai-send" id="cycaiSend" aria-label="Send message">' + ICON_SEND + '</button>' +
                '</div>' +
                '<div class="cycai-disclaimer">Educational info only — follow official IMD/NDMA alerts for real-time warnings.</div>' +
            '</div>';
        document.body.appendChild(root);
        return root;
    }

    function escapeAndKeepBasicTags(html) {
        // Our KB strings are authored by us (not user input), so we allow
        // the small set of tags we actually use.
        return html;
    }

    function scrollToBottom(body) {
        body.scrollTop = body.scrollHeight;
    }

    function addMessage(body, sender, html) {
        var msg = document.createElement('div');
        msg.className = 'cycai-msg ' + sender;
        var avatarLetter = sender === 'bot' ? '⛈' : 'U';
        msg.innerHTML =
            '<div class="cycai-msg-avatar">' + avatarLetter + '</div>' +
            '<div class="cycai-bubble">' + html + '</div>';
        body.appendChild(msg);
        scrollToBottom(body);
    }

    function addTyping(body) {
        var msg = document.createElement('div');
        msg.className = 'cycai-msg bot cycai-typing';
        msg.id = 'cycaiTypingIndicator';
        msg.innerHTML =
            '<div class="cycai-msg-avatar">⛈</div>' +
            '<div class="cycai-bubble"><span></span><span></span><span></span></div>';
        body.appendChild(msg);
        scrollToBottom(body);
    }

    function removeTyping(body) {
        var el = document.getElementById('cycaiTypingIndicator');
        if (el) el.remove();
    }

    function renderChips(container, input, sendHandler) {
        container.innerHTML = '';
        QUICK_CHIPS.forEach(function (label) {
            var chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'cycai-chip';
            chip.textContent = label;
            chip.addEventListener('click', function () {
                sendHandler(label);
            });
            container.appendChild(chip);
        });
    }

    function init() {
        if (document.getElementById('cycai-widget')) return; // avoid double init
        var root = buildWidget();

        var launcher = root.querySelector('#cycaiLauncher');
        var panel = root.querySelector('#cycaiPanel');
        var closeBtn = root.querySelector('#cycaiClose');
        var body = root.querySelector('#cycaiBody');
        var chipsWrap = root.querySelector('#cycaiChips');
        var input = root.querySelector('#cycaiInput');
        var sendBtn = root.querySelector('#cycaiSend');

        var greeted = false;

        function openPanel() {
            root.classList.add('cycai-open');
            if (!greeted) {
                greeted = true;
                addMessage(body, 'bot', "Hi! I'm CycloBot 🌪️, an AI assistant — ask me anything about tropical cyclones: what they are, how/why they form, categories, history in India, safety tips, or follow-up questions on anything I say.");
            }
            setTimeout(function () { input.focus(); }, 50);
        }

        function closePanel() {
            root.classList.remove('cycai-open');
        }

        launcher.addEventListener('click', openPanel);
        closeBtn.addEventListener('click', closePanel);

        renderChips(chipsWrap, input, handleSend);

        function handleSend(overrideText) {
            var text = (typeof overrideText === 'string' ? overrideText : input.value).trim();
            if (!text) return;

            addMessage(body, 'user', escapeAndKeepBasicTags(text));
            input.value = '';
            addTyping(body);

            getBotReply(text).then(function (reply) {
                removeTyping(body);
                addMessage(body, 'bot', escapeAndKeepBasicTags(reply));
                // Keep AI conversational memory in sync (plain text, no markup).
                pushHistory('user', text);
                pushHistory('assistant', stripHtml(reply));
            });
        }

        sendBtn.addEventListener('click', function () { handleSend(); });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSend();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
