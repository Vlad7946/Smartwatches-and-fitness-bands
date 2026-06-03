(function () {
    const keywordsEl = document.getElementById("aspect-keywords-data");
    let ASPECT_KEYWORDS = {};
    if (keywordsEl && keywordsEl.textContent.trim()) {
        try {
            ASPECT_KEYWORDS = JSON.parse(keywordsEl.textContent);
        } catch (e) {
            console.warn("Lexicon aspecte invalid în pagină:", e);
        }
    }

    const form = document.getElementById("review-form");
    const textarea = document.getElementById("review");
    const submitBtn = document.getElementById("submit-btn");
    const btnLabel = submitBtn.querySelector(".btn-label");
    const btnSpinner = submitBtn.querySelector(".btn-spinner");

    const panelPlaceholder = document.getElementById("panel-placeholder");
    const panelLoading = document.getElementById("panel-loading");
    const panelResults = document.getElementById("panel-results");
    const panelPreviewBox = document.getElementById("panel-preview-box");
    const panelPreviewText = document.getElementById("panel-preview-text");
    const panelTitle = document.getElementById("panel-title");
    const panelDesc = document.getElementById("panel-desc");
    const resetPanelBtn = document.getElementById("reset-panel-btn");

    const resultsSummary = document.getElementById("results-summary");
    const reviewToneEl = document.getElementById("review-tone");
    const panelReviewQuote = document.getElementById("panel-review-quote");
    const sentimentGroups = document.getElementById("sentiment-groups");
    const resultsEmpty = document.getElementById("results-empty");
    const charCountEl = document.getElementById("char-count");
    const sentimentCountEls = {
        pozitive: document.getElementById("count-pozitive"),
        negative: document.getElementById("count-negative"),
        neutre: document.getElementById("count-neutre"),
    };

    const ASPECT_BUCKETS = ["pozitive", "negative", "neutre"];
    const TONAL_BUCKETS = ["pozitive", "negative"];

    const TONE_LABELS = {
        pozitiv: "Pozitiv",
        negativ: "Negativ",
        neutru: "Neutru",
        mixt: "Mixt",
    };

    const listByBucket = Object.fromEntries(
        ASPECT_BUCKETS.map((b) => [b, document.getElementById(`aspect-list-${b}`)])
    );

    const TONE_TO_BUCKET = {
        pozitiv: "pozitive",
        negativ: "negative",
        neutru: "neutre",
    };

    const BUCKET_TO_TONE = {
        pozitive: "pozitiv",
        negative: "negativ",
        neutre: "neutru",
    };

    const POS_WORDS = [
        "bun",
        "buna",
        "bună",
        "excelent",
        "foarte bun",
        "util",
        "rapid",
        "recomand",
        "precis",
        "confortabil",
        "mare",
        "exacta",
        "exactă",
        "exact",
        "clara",
        "clară",
    ];
    const NEG_WORDS = [
        "prost",
        "proasta",
        "proastă",
        "slab",
        "slaba",
        "slabă",
        "rau",
        "rău",
        "incomod",
        "dezamag",
        "problem",
        "nu recomand",
        "intarz",
        "întârz",
        "ridicat",
        "scump",
        "scazut",
        "scăzut",
        "scazuta",
        "scăzută",
        "cam scazut",
        "perfomanta",
        "performanta",
        "delay",
        "delay mare",
        "intarziere",
        "întârziere",
        "mai mica",
        "mai mică",
        "mai mic decat",
        "decat promis",
        "decât promis",
        "cea promisa",
        "sub asteptari",
        "poate varia",
        "imprecis",
        "inexact",
        "nu e constant",
        "precizie slaba",
    ];
    const MIX_WORDS = [
        "insa",
        "însă",
        "dar ",
        "totusi",
        "totuși",
        "totodata",
        "totodată",
        "in schimb",
        "în schimb",
    ];
    const NEU_WORDS = ["normal", "decent", "acceptabil", "mediu", "ok"];
    const NEGATION_PHRASES = [
        "nu par",
        "nu sunt",
        "nu e ",
        "nu este",
        "nu prea",
        "nu foarte",
        "fara ",
        "fără ",
        "nu ",
    ];

    function sentimentScores(clause) {
        let pos = POS_WORDS.filter((w) => textHasTerm(clause, w)).length;
        let neg = NEG_WORDS.filter((w) => textHasTerm(clause, w)).length;
        if (NEGATION_PHRASES.some((p) => textHasTerm(clause, p)) && pos > 0) {
            neg = Math.max(neg, pos);
            pos = 0;
        }
        return { pos, neg };
    }

    function foldDiacritics(text) {
        return String(text)
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function normalizeReviewText(text) {
        return foldDiacritics(
            (text || "")
                .toLowerCase()
                .replace(/[„""«»']/g, "")
                .replace(/^[^:]+:\s*/, "")
                .trim()
        );
    }

    function textHasTerm(text, term) {
        const t = foldDiacritics(text);
        const w = foldDiacritics(term).trim();
        if (!w) return false;
        if (w.length <= 4) {
            const escaped = w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            return new RegExp(
                `(?<![a-z\u0103\u00e2\u00ee\u0219\u021b037])${escaped}(?![a-z\u0103\u00e2\u00ee\u0219\u021b037])`,
                "i"
            ).test(t);
        }
        return t.includes(w);
    }

    function splitReviewSegments(text) {
        const normalized = normalizeReviewText(text);
        if (!normalized) return [];

        let parts = [normalized];
        MIX_WORDS.forEach((marker) => {
            const next = [];
            parts.forEach((part) => {
                part.split(marker).forEach((p) => {
                    if (p.trim()) next.push(p.trim());
                });
            });
            parts = next;
        });

        const clauses = [];
        parts.forEach((part) => {
            part.split(/[.!?]+\s*/).forEach((sentence) => {
                const s = sentence.trim().replace(/^[,;\s]+/, "");
                if (!s) return;
                const parts = [];
                if (s.includes(",")) {
                    s.split(",").forEach((piece) => {
                        const p = piece.trim().replace(/^[,;\s]+/, "");
                        if (p) parts.push(p);
                    });
                } else {
                    parts.push(s);
                }
                parts.forEach((part) => {
                    if (part.includes(" și ")) {
                        part.split(" și ").forEach((seg) => {
                            const t = seg.trim();
                            if (t) clauses.push(t);
                        });
                    } else {
                        clauses.push(part);
                    }
                });
            });
        });
        return clauses.length ? clauses : [normalized];
    }

    function clauseTone(clause, forAspectBucket) {
        const { pos, neg } = sentimentScores(clause);
        const neu = NEU_WORDS.filter((w) => textHasTerm(clause, w)).length;
        if (pos > 0 && neg > 0) {
            if (forAspectBucket) {
                return pos >= neg ? "pozitiv" : "negativ";
            }
            return "mixt";
        }
        if (pos > neg) return "pozitiv";
        if (neg > pos) return "negativ";
        if (neu > 0) return "neutru";
        return "neutru";
    }

    function aspectInClause(clause, aspect) {
        const keywords = ASPECT_KEYWORDS[aspect];
        if (keywords && keywords.length) {
            return keywords.some((kw) => textHasTerm(clause, kw));
        }
        const clauseNorm = foldDiacritics(clause);
        return foldDiacritics(aspect)
            .split(/\s+/)
            .some((part) => part.length > 4 && clauseNorm.includes(part));
    }

    function aspectContextFragment(reviewText, aspect) {
        const normalized = normalizeReviewText(reviewText);
        const keywords = ASPECT_KEYWORDS[aspect] || [];
        let bestPos = -1;
        let bestLen = 0;

        for (const kw of keywords) {
            const folded = foldDiacritics(kw);
            const pos = normalized.indexOf(folded);
            if (pos !== -1 && (bestPos === -1 || pos < bestPos)) {
                bestPos = pos;
                bestLen = folded.length;
            }
        }

        if (bestPos === -1) {
            return normalized;
        }

        const prefix = normalized.slice(0, bestPos);
        let start = Math.max(0, bestPos - 90);
        const darIdx = prefix.lastIndexOf("dar ");
        if (darIdx !== -1) {
            start = Math.max(start, darIdx + 4);
        }
        const lastComma = prefix.lastIndexOf(",");
        if (lastComma !== -1) {
            start = Math.max(start, lastComma + 1);
        }

        let end = Math.min(normalized.length, bestPos + bestLen + 90);
        const chunk = normalized.slice(start, end);
        const rel = bestPos - start;
        const commaRight = chunk.indexOf(",", rel);
        if (commaRight !== -1) {
            end = start + commaRight;
        }
        return normalized.slice(start, end).trim();
    }

    function bucketFromClauses(clauses) {
        let bestBucket = null;
        let bestScore = -1;

        for (const clause of clauses) {
            const tone = clauseTone(clause, true);
            const bucket = TONE_TO_BUCKET[tone];
            if (!bucket) continue;

            const { pos, neg } = sentimentScores(clause);
            const score = Math.max(pos, neg);
            if (score > bestScore) {
                bestScore = score;
                bestBucket = bucket;
            }
        }

        return bestBucket;
    }

    function inferAspectBucket(aspect, reviewText) {
        const fragment = aspectContextFragment(reviewText, aspect);
        const { pos: fragPos, neg: fragNeg } = sentimentScores(fragment);
        if (fragPos !== fragNeg) {
            const bucket = TONE_TO_BUCKET[clauseTone(fragment, true)];
            if (bucket) return bucket;
        }

        const segments = splitReviewSegments(reviewText);
        if (!segments.length) return null;

        const matching = segments.filter((clause) => aspectInClause(clause, aspect));
        if (matching.length) {
            return bucketFromClauses(matching);
        }

        const bucket = TONE_TO_BUCKET[clauseTone(fragment, true)];
        return bucket || null;
    }

    function inferToneFromReviewText(text) {
        const segments = splitReviewSegments(text);
        if (!segments.length) return "neutru";

        const tones = new Set(
            segments.map(clauseTone).filter((t) => t !== "neutru")
        );
        if (tones.has("pozitiv") && tones.has("negativ")) return "mixt";
        if (tones.size > 1) return "mixt";

        const t = segments.join(" ");
        const hasMix = MIX_WORDS.some((w) => textHasTerm(t, w));
        const pos = POS_WORDS.filter((w) => textHasTerm(t, w)).length;
        const neg = NEG_WORDS.filter((w) => textHasTerm(t, w)).length;
        const neu = NEU_WORDS.filter((w) => textHasTerm(t, w)).length;

        if (hasMix && (pos > 0 || neg > 0)) return "mixt";
        if (pos > 0 && neg > 0) return "mixt";
        if (pos > neg) return "pozitiv";
        if (neg > pos) return "negativ";
        if (neu > 0) return "neutru";
        return "neutru";
    }

    function resolveReviewTone(data) {
        if (data.ton_review && TONE_LABELS[data.ton_review]) {
            return data.ton_review;
        }

        const groups = data.aspecte_pe_sentiment;
        if (groups && typeof groups === "object") {
            const filled = TONAL_BUCKETS.filter((b) => (groups[b] || []).length > 0);
            const bucketTones = filled
                .map((b) => BUCKET_TO_TONE[b])
                .filter((t) => t && TONE_LABELS[t]);
            if (
                bucketTones.includes("pozitiv") &&
                bucketTones.includes("negativ")
            ) {
                return "mixt";
            }
            if (bucketTones.length === 1) {
                return bucketTones[0];
            }
        }

        const tones = [
            ...new Set(
                (data.detalii || [])
                    .map((d) => d.sentiment)
                    .filter((s) => s && TONE_LABELS[s])
            ),
        ];
        if (tones.length === 1) return tones[0];
        if (tones.length > 1) return "mixt";

        const inferred = inferToneFromReviewText(data.review);
        if (inferred) return inferred;

        const segments = splitReviewSegments(data.review || "");
        if (segments.length >= 2) return "mixt";

        return "neutru";
    }

    function toneLabelFor(data) {
        const tone = resolveReviewTone(data);
        return TONE_LABELS[tone] || "";
    }

    function showPanelState(state) {
        panelPlaceholder.hidden = state !== "placeholder";
        panelLoading.hidden = state !== "loading";
        panelResults.hidden = state !== "results";
    }

    function setLoading(loading) {
        submitBtn.disabled = loading;
        btnSpinner.hidden = !loading;
        btnLabel.textContent = loading ? "Se analizează..." : "Identifică aspectele";
        if (loading) {
            showPanelState("loading");
        }
    }

    function resizeReviewTextarea() {
        if (!textarea) return;
        const field = textarea.closest(".field");
        const minH = parseFloat(getComputedStyle(textarea).minHeight) || 160;
        let fillH = minH;

        if (field) {
            const label = field.querySelector(".field-top");
            const labelGap = 8;
            fillH = Math.max(
                field.clientHeight - (label ? label.offsetHeight + labelGap : 0),
                minH
            );
        }

        textarea.style.height = "auto";
        const contentH = textarea.scrollHeight;
        const next = Math.max(contentH, fillH);
        textarea.style.height = `${next}px`;
        textarea.style.overflowY = contentH > fillH ? "auto" : "hidden";
    }

    function updateCharCount() {
        if (!charCountEl) return;
        const len = textarea.value.length;
        if (!len) {
            charCountEl.textContent = "";
            return;
        }
        charCountEl.textContent = `${len.toLocaleString("ro-RO")} caractere`;
    }

    function updatePlaceholderPreview() {
        const review = textarea.value.trim();
        if (!review) {
            panelPreviewBox.hidden = true;
            panelTitle.textContent = "Cum funcționează analiza";
            panelDesc.textContent =
                "Completați review-ul în stânga, apoi apăsați butonul de analiză. Aici veți vedea aspectele detectate automat.";
            return;
        }

        panelPreviewBox.hidden = false;
        panelTitle.textContent = "Pregătit pentru analiză";
        panelDesc.textContent =
            "Review-ul este introdus. Apăsați „Identifică aspectele” pentru a vedea rezultatele aici.";
        const preview =
            review.length > 160 ? review.slice(0, 160).trim() + "…" : review;
        panelPreviewText.textContent = preview;
    }

    function badgeClass(sursa) {
        if (sursa === "lexicon") return "badge-lexicon";
        if (sursa === "ml") return "badge-ml";
        return "badge-hybrid";
    }

    function badgeLabel(sursa) {
        if (sursa === "lexicon") return "Lexicon";
        if (sursa === "ml") return "ML";
        return "Lexicon + ML";
    }

    function bucketForAspect(data, aspect) {
        const item = data.detalii.find((d) => d.aspect === aspect);
        if (item?.sentiment && TONE_TO_BUCKET[item.sentiment]) {
            return TONE_TO_BUCKET[item.sentiment];
        }

        const groups = data.aspecte_pe_sentiment;
        if (groups && typeof groups === "object") {
            for (const bucket of ASPECT_BUCKETS) {
                const list = groups[bucket] || [];
                if (list.includes(aspect)) {
                    return bucket;
                }
            }
        }

        const inferred = inferAspectBucket(aspect, data.review || "");
        if (inferred) return inferred;

        const tone = resolveReviewTone(data);
        if (TONE_TO_BUCKET[tone]) {
            return TONE_TO_BUCKET[tone];
        }

        return null;
    }

    function renderAspectItem(item, index) {
        const li = document.createElement("li");
        li.className = "aspect-item";
        if (item.sentiment) {
            li.classList.add(`aspect-item--${item.sentiment}`);
        }
        li.style.animationDelay = `${index * 0.05}s`;

        const scoreHtml =
            item.sursa !== "lexicon"
                ? `<span class="score">${Math.round(item.scor * 100)}%</span>`
                : "";

        li.innerHTML = `
            <span class="aspect-name">${formatAspectLabel(item.aspect)}</span>
            <span class="aspect-meta">
                <span class="badge ${badgeClass(item.sursa)}">${badgeLabel(item.sursa)}</span>
                ${scoreHtml}
            </span>
        `;
        return li;
    }

    function renderResults(data) {
        showPanelState("results");

        ASPECT_BUCKETS.forEach((bucket) => {
            const listEl = listByBucket[bucket];
            if (listEl) {
                listEl.innerHTML = "";
            }
        });

        const totalCount = data.detalii.length;
        const byBucket = Object.fromEntries(ASPECT_BUCKETS.map((b) => [b, []]));
        data.detalii.forEach((item) => {
            const bucket = bucketForAspect(data, item.aspect);
            if (bucket && ASPECT_BUCKETS.includes(bucket)) {
                byBucket[bucket].push(item);
            }
        });

        const countPoz = byBucket.pozitive.length;
        const countNeg = byBucket.negative.length;
        const countNeu = byBucket.neutre.length;
        const visibleCount = countPoz + countNeg + countNeu;
        const toneLabel = toneLabelFor(data);

        if (visibleCount > 0) {
            const parts = [];
            if (countPoz) parts.push(`${countPoz} pozitive`);
            if (countNeg) parts.push(`${countNeg} negative`);
            if (countNeu) parts.push(`${countNeu} neutre`);
            resultsSummary.textContent = `${visibleCount} aspect(e): ${parts.join(", ")}.`;
        } else {
            resultsSummary.textContent =
                "Niciun aspect nu a putut fi asociat textului.";
        }

        if (reviewToneEl) {
            const reviewTone = resolveReviewTone(data);
            reviewToneEl.className = "review-tone tone-pill";
            let toneText = "";
            if (totalCount > 0 && toneLabel) {
                if (reviewTone) {
                    reviewToneEl.classList.add(`tone-pill--${reviewTone}`);
                }
                toneText = `Ton review: ${toneLabel}`;
                if (reviewTone === "mixt") {
                    toneText += " · aspecte grupate pe ton mai jos";
                }
            }
            reviewToneEl.textContent = toneText;
            reviewToneEl.hidden = totalCount === 0 || !toneLabel;
        }

        Object.entries(sentimentCountEls).forEach(([bucket, el]) => {
            if (!el) return;
            const n = (byBucket[bucket] || []).length;
            el.textContent = n > 0 ? String(n) : "";
        });

        const quote =
            data.review.length > 200
                ? data.review.slice(0, 200).trim() + "…"
                : data.review;
        panelReviewQuote.textContent = quote;
        panelReviewQuote.hidden = !data.review;

        resultsEmpty.hidden = totalCount > 0;
        if (sentimentGroups) {
            sentimentGroups.hidden = totalCount === 0;
        }

        const groups = document.querySelectorAll(".sentiment-group");
        if (groups.length > 0) {
            groups.forEach((section) => {
                const bucket = section.dataset.bucket;
                const items = byBucket[bucket] || [];
                const listEl = listByBucket[bucket];
                const emptyEl = section.querySelector(".sentiment-empty");

                if (listEl) {
                    items.forEach((item, index) => {
                        listEl.appendChild(renderAspectItem(item, index));
                    });
                }

                section.hidden = totalCount > 0 && items.length === 0;
                if (emptyEl) {
                    emptyEl.hidden = items.length > 0;
                }
            });
        } else if (visibleCount > 0) {
            console.warn(
                "Pagina nu conține grupuri de sentiment. Reîncărcați http://127.0.0.1:5050/ după repornirea serverului."
            );
        }
    }

    function resetToPlaceholder() {
        textarea.value = "";
        textarea.style.height = "";
        resizeReviewTextarea();
        updateCharCount();
        textarea.focus();
        updatePlaceholderPreview();
        showPanelState("placeholder");
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /** Evită „și” singur pe un rând în titluri tip „X și Y”. */
    function formatAspectLabel(name) {
        return escapeHtml(
            String(name).replace(/\s+și\s+/gi, "\u00a0și\u00a0")
        );
    }

    textarea.addEventListener("input", () => {
        resizeReviewTextarea();
        updateCharCount();
        updatePlaceholderPreview();
    });

    resizeReviewTextarea();
    updateCharCount();
    window.addEventListener("resize", resizeReviewTextarea);

    const reviewField = textarea.closest(".field");
    if (reviewField && typeof ResizeObserver !== "undefined") {
        new ResizeObserver(() => resizeReviewTextarea()).observe(reviewField);
    }

    resetPanelBtn.addEventListener("click", resetToPlaceholder);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const review = textarea.value.trim();
        if (!review) {
            textarea.focus();
            return;
        }

        setLoading(true);
        try {
            const res = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ review }),
            });
            const data = await res.json();
            if (!res.ok) {
                showPanelState("placeholder");
                alert(data.error || "Eroare la analiză.");
                return;
            }
            renderResults(data);
        } catch (err) {
            showPanelState("placeholder");
            console.error("Analiză eșuată:", err);
            const hint =
                err instanceof TypeError
                    ? "Reîncărcați pagina (Ctrl+F5) și reporniți serverul: opriți python app.py, apoi porniți din nou."
                    : "Verificați că accesați http://127.0.0.1:5050/ (același URL ca serverul).";
            alert(
                "Nu s-a putut finaliza analiza.\n\n" +
                    hint +
                    "\n\nDetalii în consola browserului (F12)."
            );
        } finally {
            setLoading(false);
        }
    });

    showPanelState("placeholder");

    const serverStatus = document.getElementById("server-status");
    fetch("/health")
        .then((r) => r.json())
        .then((data) => {
            if (!serverStatus) return;
            const version = String(data.api_version || "");
            const versionNum = parseFloat(version);
            if (data.sentiment_api && version && versionNum >= 2.1) {
                serverStatus.textContent = `Server analiză v${version} (sentiment activ)`;
                serverStatus.className = "server-status server-status-ok";
            } else {
                serverStatus.textContent =
                    "Server vechi detectat — opriți toate procesele python app.py și reporniți.";
                serverStatus.className = "server-status server-status-warn";
            }
            serverStatus.hidden = false;
        })
        .catch(() => {
            if (!serverStatus) return;
            serverStatus.textContent =
                "Nu s-a putut verifica serverul. Porniți: python app.py";
            serverStatus.className = "server-status server-status-warn";
            serverStatus.hidden = false;
        });
})();
