(() => {
  const userSelect = document.getElementById("user-select");
  const recommendBtn = document.getElementById("recommend-btn");
  const statusEl = document.getElementById("status");
  const userInfoEl = document.getElementById("user-info");
  const resultsEl = document.getElementById("results");
  const genInput = document.getElementById("gen-input");
  const popInput = document.getElementById("pop-input");
  const mutInput = document.getElementById("mut-input");
  const resetBtn = document.getElementById("reset-btn");

  let users = [];
  const DEFAULTS = { generations: 120, pop_size: 80, mutation_rate: 0.05 };

  function setStatus(msg, type = "info") {
    if (!msg) {
      statusEl.classList.add("hidden");
      return;
    }
    statusEl.classList.remove("hidden", "error");
    if (type === "error") statusEl.classList.add("error");
    statusEl.innerHTML = type === "loading"
      ? `<span class="spinner"></span>${msg}`
      : msg;
  }

  async function loadUsers() {
    setStatus("جاري تحميل قائمة المستخدمين...", "loading");
    try {
      const res = await fetch("/sandbox/api/users");
      if (!res.ok) throw new Error("فشل تحميل المستخدمين");
      users = await res.json();
      users.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.user_id;
        opt.textContent = `مستخدم #${u.user_id}`;
        userSelect.appendChild(opt);
      });
      setStatus(null);
      recommendBtn.disabled = false;
    } catch (err) {
      setStatus(err.message, "error");
    }
  }

  function renderUserInfo(user, fitness) {
    userInfoEl.classList.remove("hidden");
    userInfoEl.innerHTML = `
      <span>المستخدم: <strong>${user.user_id}</strong></span>
      <span>العمر: <strong>${user.age}</strong></span>
      <span>الدولة: <strong>${user.country}</strong></span>
      <span class="fitness">اللياقة: ${fitness}</span>
    `;
  }

  function renderResults(recs) {
    resultsEl.innerHTML = "";
    recs.forEach((p, i) => {
      const card = document.createElement("div");
      card.className = "algo-card";
      card.innerHTML = `
        <div class="rank">${i + 1}</div>
        <div class="name">عنصر #${p.product_id}</div>
        <div class="category">${p.category}</div>
        <div class="price">${p.price.toFixed(2)}</div>
        <div class="score">
          <span>الدرجة</span>
          <span class="score-value">${p.score.toFixed(3)}</span>
        </div>
      `;
      resultsEl.appendChild(card);
    });
  }

  async function fetchRecommendations(userId) {
    setStatus("جاري تشغيل الخوارزمية الجينية...", "loading");
    userInfoEl.classList.add("hidden");
    resultsEl.innerHTML = "";
    recommendBtn.disabled = true;

    const validate = (input, label) => {
      const v = parseFloat(input.value);
      const min = parseFloat(input.min);
      const max = parseFloat(input.max);
      if (input.value === "" || isNaN(v)) {
        triggerInvalid(input);
        input.focus();
        throw new Error(`الحقل "${label}" فارغ — أدخل رقماً صحيحاً.`);
      }
      if (v < min || v > max) {
        triggerInvalid(input);
        input.focus();
        throw new Error(`القيمة "${v}" في حقل "${label}" خارج المجال المسموح (${min} – ${max}). يرجى تصحيحها.`);
      }
      input.classList.remove("invalid");
      return v;
    };

    let params;
    try {
      params = new URLSearchParams({
        generations: validate(genInput, "عدد الأجيال"),
        pop_size: validate(popInput, "حجم المجتمع"),
        mutation_rate: validate(mutInput, "معدل الطفرة"),
      });
    } catch (err) {
      setStatus(err.message, "error");
      recommendBtn.disabled = false;
      return;
    }

    try {
      const res = await fetch(`/sandbox/api/recommend/${userId}?${params}`);
      if (!res.ok) throw new Error("فشل توليد التوصيات");
      const data = await res.json();
      const user = users.find(u => u.user_id === data.user_id);
      renderUserInfo(user, data.fitness);
      renderResults(data.recommendations);
      const lastGen = data.history[data.history.length - 1];
      setStatus(`اكتملت الخوارزمية — ${data.history.length} جيل · أفضل لياقة: ${lastGen.best.toFixed(3)}`);
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      recommendBtn.disabled = false;
    }
  }

  const triggerInvalid = (el) => {
    el.classList.remove("invalid");
    void el.offsetWidth;
    el.classList.add("invalid");
  };

  recommendBtn.addEventListener("click", () => {
    const id = parseInt(userSelect.value, 10);
    if (!id) {
      triggerInvalid(userSelect);
      userSelect.focus();
      setStatus("يرجى اختيار مستخدم أولاً.", "error");
      return;
    }
    userSelect.classList.remove("invalid");
    fetchRecommendations(id);
  });

  userSelect.addEventListener("change", () => {
    recommendBtn.disabled = !userSelect.value;
    userSelect.classList.remove("invalid");
    if (userSelect.value) setStatus(null);
  });

  const resetAdvanced = () => {
    genInput.value = DEFAULTS.generations;
    popInput.value = DEFAULTS.pop_size;
    mutInput.value = DEFAULTS.mutation_rate;
    [genInput, popInput, mutInput].forEach(i => i.classList.remove("invalid"));
  };

  resetBtn.addEventListener("click", () => {
    resetAdvanced();
    setStatus(null);
  });

  const advancedDetails = document.querySelector("details.advanced");
  advancedDetails.addEventListener("toggle", () => {
    if (!advancedDetails.open) resetAdvanced();
  });

  [genInput, popInput, mutInput].forEach(input => {
    input.addEventListener("input", () => input.classList.remove("invalid"));
    input.addEventListener("keydown", (e) => {
      if (["e", "E", "+"].includes(e.key)) e.preventDefault();
    });
    input.addEventListener("paste", (e) => {
      const text = (e.clipboardData || window.clipboardData).getData("text");
      if (/[eE+]/.test(text)) e.preventDefault();
    });
  });

  loadUsers();
})();
