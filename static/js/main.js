(function () {
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
    const panelReviewQuote = document.getElementById("panel-review-quote");
    const aspectList = document.getElementById("aspect-list");
    const resultsEmpty = document.getElementById("results-empty");

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

    function renderResults(data) {
        showPanelState("results");
        aspectList.innerHTML = "";

        const count = data.detalii.length;
        resultsSummary.textContent =
            count > 0
                ? `${count} aspect(e) detectat(e) în review.`
                : "Niciun aspect nu a putut fi asociat textului.";

        const quote =
            data.review.length > 200
                ? data.review.slice(0, 200).trim() + "…"
                : data.review;
        panelReviewQuote.textContent = quote;
        panelReviewQuote.hidden = !data.review;

        resultsEmpty.hidden = count > 0;

        data.detalii.forEach((item, index) => {
            const li = document.createElement("li");
            li.className = "aspect-item";
            li.style.animationDelay = `${index * 0.05}s`;

            const scoreHtml =
                item.sursa !== "lexicon"
                    ? `<span class="score">${Math.round(item.scor * 100)}%</span>`
                    : "";

            li.innerHTML = `
                <span class="aspect-name">${escapeHtml(item.aspect)}</span>
                <span class="aspect-meta">
                    <span class="badge ${badgeClass(item.sursa)}">${badgeLabel(item.sursa)}</span>
                    ${scoreHtml}
                </span>
            `;
            aspectList.appendChild(li);
        });
    }

    function resetToPlaceholder() {
        textarea.value = "";
        textarea.focus();
        updatePlaceholderPreview();
        showPanelState("placeholder");
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    textarea.addEventListener("input", updatePlaceholderPreview);

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
            alert("Nu s-a putut contacta serverul. Verificați că Flask rulează.");
        } finally {
            setLoading(false);
        }
    });

    showPanelState("placeholder");
})();
