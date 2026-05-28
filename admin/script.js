const navToggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");

if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

const form = document.querySelector("#consult-form");
const status = document.querySelector(".form-status");

if (form && status) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const name = data.get("name") || "";
    const email = data.get("email") || "";
    const company = data.get("company") || "";
    const message = data.get("message") || "";
    const subject = encodeURIComponent(`Free consult request from ${company || name}`);
    const body = encodeURIComponent(
      `Name: ${name}\nEmail: ${email}\nCompany: ${company}\n\nBottleneck to discuss:\n${message}`
    );

    status.textContent = "Opening a draft email so your team can connect directly.";
    window.location.href = `mailto:hello@smithrevenuestrategy.com?subject=${subject}&body=${body}`;
  });
}

const canvas = document.querySelector("#flow-canvas");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (canvas) {
  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let tick = 0;

  const nodes = [
    { x: 0.18, y: 0.2, label: "CRM" },
    { x: 0.38, y: 0.16, label: "OPS" },
    { x: 0.68, y: 0.28, label: "AI" },
    { x: 0.26, y: 0.55, label: "DATA" },
    { x: 0.52, y: 0.62, label: "LOGIC" },
    { x: 0.78, y: 0.76, label: "REV" }
  ];

  const links = [
    [0, 1],
    [1, 2],
    [0, 3],
    [3, 4],
    [2, 4],
    [4, 5]
  ];

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    canvas.width = width * scale;
    canvas.height = height * scale;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
  }

  function drawGrid() {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#020711";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(72,255,132,0.08)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 38) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 38) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  function nodePoint(node) {
    return { x: node.x * width, y: node.y * height };
  }

  function drawLinks() {
    links.forEach(([from, to], index) => {
      const a = nodePoint(nodes[from]);
      const b = nodePoint(nodes[to]);
      const pulse = (Math.sin(tick * 0.035 + index) + 1) / 2;

      ctx.strokeStyle = "rgba(72,255,132,0.28)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      const midX = (a.x + b.x) / 2;
      ctx.bezierCurveTo(midX, a.y, midX, b.y, b.x, b.y);
      ctx.stroke();

      const px = a.x + (b.x - a.x) * pulse;
      const py = a.y + (b.y - a.y) * pulse;
      ctx.fillStyle = index % 2 ? "#fff19b" : "#48ff84";
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawNodes() {
    nodes.forEach((node, index) => {
      const point = nodePoint(node);
      const radius = index === 2 || index === 5 ? 38 : 30;

      ctx.fillStyle = "#052513";
      ctx.beginPath();
      ctx.roundRect(point.x - radius, point.y - radius, radius * 2, radius * 2, 8);
      ctx.fill();

      ctx.strokeStyle = index === 2 ? "#48ff84" : index === 5 ? "#fff19b" : "#9ed2df";
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.fillStyle = "#f7f5f0";
      ctx.font = "800 12px ui-monospace, SFMono-Regular, Consolas, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.label, point.x, point.y);
    });
  }

  function drawCapacityMeter() {
    const x = width * 0.12;
    const y = height * 0.9;
    const w = width * 0.72;
    const h = 14;
    const fill = reduceMotion ? 0.72 : 0.66 + Math.sin(tick * 0.025) * 0.08;

    ctx.fillStyle = "rgba(72,255,132,0.12)";
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 7);
    ctx.fill();

    const gradient = ctx.createLinearGradient(x, y, x + w, y);
    gradient.addColorStop(0, "#9ed2df");
    gradient.addColorStop(0.55, "#48ff84");
    gradient.addColorStop(1, "#fff19b");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.roundRect(x, y, w * fill, h, 7);
    ctx.fill();

    ctx.fillStyle = "rgba(158,210,223,0.9)";
    ctx.font = "700 11px ui-monospace, SFMono-Regular, Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText("REVENUE CAPACITY RESTORED", x, y - 12);
  }

  function render() {
    drawGrid();
    drawLinks();
    drawNodes();
    drawCapacityMeter();
    tick += 1;
    if (!reduceMotion) requestAnimationFrame(render);
  }

  window.addEventListener("resize", () => {
    resizeCanvas();
    if (reduceMotion) render();
  });

  resizeCanvas();
  render();
}
