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
      const res = await fetch("/api/users");
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
      card.className = "card";
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

    try {
      const params = new URLSearchParams({
        generations: genInput.value || DEFAULTS.generations,
        pop_size: popInput.value || DEFAULTS.pop_size,
        mutation_rate: mutInput.value || DEFAULTS.mutation_rate,
      });
      const res = await fetch(`/api/recommend/${userId}?${params}`);
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

  recommendBtn.addEventListener("click", () => {
    const id = parseInt(userSelect.value, 10);
    if (id) fetchRecommendations(id);
  });

  userSelect.addEventListener("change", () => {
    recommendBtn.disabled = !userSelect.value;
  });

  resetBtn.addEventListener("click", () => {
    genInput.value = DEFAULTS.generations;
    popInput.value = DEFAULTS.pop_size;
    mutInput.value = DEFAULTS.mutation_rate;
  });

  loadUsers();
})();
