/* Interaksi website dengan JavaScript murni; tanpa database atau penyimpanan inquiry. */
(() => {
  "use strict";

  const root = document.documentElement;
  const config = window.SITE_CONFIG || {};
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  const mobileNavigation = window.matchMedia("(max-width: 899px)");
  const header = document.getElementById("site-header");
  const nav = document.getElementById("site-nav");
  const menuToggle = document.getElementById("menu-toggle");
  const form = document.getElementById("inquiry-form");
  const status = document.getElementById("form-status");
  const fallback = document.getElementById("whatsapp-fallback");
  const fallbackLink = document.getElementById("whatsapp-fallback-link");
  root.classList.add("js");

  /* Identitas dan kontak diambil dari satu konfigurasi, selalu lewat textContent. */
  const placeholders = { name: "[Company Name]", email: "[Email address]", phone: "[Business phone]", address: "[Office address]", hours: "[Business hours]" };
  document.querySelectorAll("[data-company]").forEach((element) => {
    const key = element.dataset.company;
    element.textContent = config[key] || placeholders[key] || "";
  });
  if (config.name && config.name !== placeholders.name) {
    document.title = `${config.name} — Briquette Export & International Trade`;
    document.querySelector('meta[property="og:title"]').content = `${config.name} — Briquettes for global markets`;
  }
  document.getElementById("copyright-year").textContent = new Date().getFullYear();
  document.querySelectorAll('[data-contact="email"]').forEach((element) => {
    if (config.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(config.email)) element.href = `mailto:${config.email}`;
  });
  document.querySelectorAll('[data-contact="phone"]').forEach((element) => {
    if (config.phone) element.href = `tel:${config.phone.replace(/[^+\d]/g, "")}`;
  });
  document.querySelectorAll("[data-social]").forEach((element) => {
    const key = element.dataset.social;
    const url = config.social?.[key];
    if (!url) return;
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "https:") return;
      element.href = parsed.href;
      element.target = "_blank";
      element.rel = "noopener noreferrer";
      element.removeAttribute("aria-disabled");
      element.setAttribute("aria-label", key === "youtube" ? "YouTube" : key === "linkedin" ? "LinkedIn" : "Instagram");
    } catch { /* URL yang belum valid tetap menjadi placeholder noninteraktif. */ }
  });

  /* Navigasi mobile: tutup dengan Escape, tautan, klik di luar, atau perubahan ukuran. */
  function setMenu(open, returnFocus = false) {
    const expanded = mobileNavigation.matches && open;
    nav.classList.toggle("is-open", expanded);
    menuToggle.setAttribute("aria-expanded", String(expanded));
    menuToggle.setAttribute("aria-label", expanded ? "Close navigation" : "Open navigation");
    nav.inert = mobileNavigation.matches && !expanded;
    if (mobileNavigation.matches) nav.setAttribute("aria-hidden", String(!expanded));
    else nav.removeAttribute("aria-hidden");
    if (returnFocus) menuToggle.focus();
  }
  menuToggle.addEventListener("click", () => setMenu(menuToggle.getAttribute("aria-expanded") !== "true"));
  nav.addEventListener("click", (event) => { if (event.target.closest("a")) setMenu(false); });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") setMenu(false, true);
  });
  document.addEventListener("click", (event) => {
    if (!header.contains(event.target) && menuToggle.getAttribute("aria-expanded") === "true") setMenu(false);
  });
  mobileNavigation.addEventListener("change", () => setMenu(false));
  setMenu(false);

  /* Scroll diproses sekali per frame: header, menu aktif, dan indikator kemajuan. */
  const navLinks = [...document.querySelectorAll(".nav-link")];
  const navSections = ["home", "about", "services", "products", "contact"].map((id) => document.getElementById(id));
  const progress = document.getElementById("reading-progress");
  let scrollScheduled = false;
  function updateScrollUI() {
    scrollScheduled = false;
    header.classList.toggle("is-scrolled", window.scrollY > 12);
    const distance = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.transform = `scaleX(${distance > 0 ? Math.min(1, Math.max(0, window.scrollY / distance)) : 0})`;
    let current = "home";
    const offset = header.offsetHeight + 100;
    navSections.forEach((section) => { if (section.getBoundingClientRect().top <= offset) current = section.id; });
    navLinks.forEach((link) => {
      const active = link.hash === `#${current}`;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  function scheduleScrollUI() {
    if (!scrollScheduled) { scrollScheduled = true; window.requestAnimationFrame(updateScrollUI); }
  }
  window.addEventListener("scroll", scheduleScrollUI, { passive: true });
  window.addEventListener("resize", scheduleScrollUI, { passive: true });
  updateScrollUI();

  /* Reveal sekali saat masuk viewport, dengan jeda pendek seperti referensi Cartenz. */
  const revealElements = [...document.querySelectorAll("[data-reveal]")];
  let revealObserver;
  function setupReveals() {
    revealObserver?.disconnect();
    if (motionPreference.matches || !("IntersectionObserver" in window)) {
      root.classList.remove("motion-ready");
      revealElements.forEach((element) => element.classList.add("is-visible"));
      return;
    }
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -20px 0px" });
    revealElements.forEach((element) => {
      element.style.setProperty("--reveal-delay", `${Math.min(300, Number(element.dataset.delay) || 0)}ms`);
      if (!element.classList.contains("is-visible")) revealObserver.observe(element);
    });
    root.classList.add("motion-ready");
  }
  setupReveals();

  /* Crossfade 1,1 detik dan Ken Burns; autoplay berhenti saat tak terlihat atau reduced motion. */
  const slideshow = document.getElementById("hero-slideshow");
  const slides = [...slideshow.querySelectorAll(".hero-slide")];
  const dots = [...document.querySelectorAll("[data-slide]")];
  const pauseButton = document.getElementById("slideshow-pause");
  const slideCount = document.getElementById("slide-count");
  let activeSlide = 0;
  let slideshowTimer;
  let userPaused = false;
  let pointerPaused = false;
  let focusPaused = false;
  let heroVisible = true;
  function syncSlideshow() {
    window.clearTimeout(slideshowTimer);
    const stopped = userPaused || pointerPaused || focusPaused || motionPreference.matches || document.hidden || !heroVisible;
    slideshow.classList.toggle("is-animated", !motionPreference.matches);
    slideshow.classList.toggle("is-paused", stopped);
    pauseButton.setAttribute("aria-pressed", String(userPaused || motionPreference.matches));
    pauseButton.setAttribute("aria-label", motionPreference.matches ? "Slideshow paused for reduced motion" : userPaused ? "Play slideshow" : "Pause slideshow");
    pauseButton.querySelector("use").setAttribute("href", userPaused || motionPreference.matches ? "#i-play" : "#i-pause");
    pauseButton.disabled = motionPreference.matches;
    if (!stopped) slideshowTimer = window.setTimeout(() => showSlide((activeSlide + 1) % slides.length), 6000);
  }
  function showSlide(index) {
    if (index < 0 || index >= slides.length) return;
    activeSlide = index;
    slides.forEach((slide, position) => {
      const active = index === position;
      slide.classList.toggle("is-active", active);
      slide.setAttribute("aria-hidden", String(!active));
      dots[position].classList.toggle("is-active", active);
      dots[position].setAttribute("aria-pressed", String(active));
    });
    slideCount.textContent = `${String(index + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
    syncSlideshow();
  }
  dots.forEach((dot) => dot.addEventListener("click", () => showSlide(Number(dot.dataset.slide))));
  pauseButton.addEventListener("click", () => { userPaused = !userPaused; syncSlideshow(); });
  const slideshowArea = document.querySelector(".hero-visual");
  slideshowArea.addEventListener("pointerenter", (event) => { if (event.pointerType === "mouse") { pointerPaused = true; syncSlideshow(); } });
  slideshowArea.addEventListener("pointerleave", () => { pointerPaused = false; syncSlideshow(); });
  slideshowArea.addEventListener("focusin", () => { focusPaused = true; syncSlideshow(); });
  slideshowArea.addEventListener("focusout", (event) => { if (!slideshowArea.contains(event.relatedTarget)) { focusPaused = false; syncSlideshow(); } });
  document.addEventListener("visibilitychange", syncSlideshow);
  if ("IntersectionObserver" in window) {
    const heroObserver = new IntersectionObserver((entries) => { heroVisible = entries[0].isIntersecting; syncSlideshow(); });
    heroObserver.observe(slideshow);
  }
  motionPreference.addEventListener("change", () => { setupReveals(); syncSlideshow(); });
  showSlide(0);

  /* Validasi field wajib mencakup input yang hanya berisi spasi dan format email. */
  const requiredFields = [
    { name: "fullName", message: "Please enter your full name." },
    { name: "company", message: "Please enter your company name." },
    { name: "email", message: "Please enter a valid email address." },
    { name: "service", message: "Please select Export or Import." },
    { name: "commodity", message: "Please describe the product you need." }
  ];
  function fieldMessage(field) {
    const value = field.value.trim();
    if (field.name === "email") return value && field.validity.valid ? "" : "Please enter a valid email address.";
    if (field.name === "service") return ["Export", "Import"].includes(value) ? "" : "Please select Export or Import.";
    return value ? "" : requiredFields.find((item) => item.name === field.name)?.message || "";
  }
  function displayFieldError(field, message) {
    const error = document.getElementById(`${field.id}-error`);
    if (error) error.textContent = message;
    if (message) field.setAttribute("aria-invalid", "true");
    else field.removeAttribute("aria-invalid");
  }
  function setStatus(message, error = false) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
  }
  requiredFields.forEach(({ name }) => {
    const field = form.elements[name];
    field.addEventListener("blur", () => { if (field.value || field.hasAttribute("aria-invalid")) displayFieldError(field, fieldMessage(field)); });
    field.addEventListener("input", () => { if (field.hasAttribute("aria-invalid")) displayFieldError(field, fieldMessage(field)); });
    field.addEventListener("change", () => { if (field.hasAttribute("aria-invalid")) displayFieldError(field, fieldMessage(field)); });
  });
  form.addEventListener("input", () => {
    // Tautan lama dihapus agar tidak mengirim versi inquiry sebelum diedit.
    fallback.hidden = true;
    fallbackLink.removeAttribute("href");
    if (!status.classList.contains("is-error")) setStatus("");
  });

  /* Gunakan nomor WhatsApp konfigurasi yang sama untuk form dan tombol melayang. */
  function getWhatsAppNumber() {
    const value = String(config.whatsappNumber || "").trim();
    if (!/^\+?[\d\s()-]+$/.test(value)) return "";
    const digits = value.replace(/\D/g, "");
    return /^[1-9]\d{7,14}$/.test(digits) ? digits : "";
  }
  function messageFromForm() {
    const values = Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, String(value).trim()]));
    const optional = (value) => value || "Not specified";
    return [
      "Hello, I would like to request a quotation for your services.", "",
      `Full Name: ${values.fullName}`, `Company: ${values.company}`, `Email: ${values.email}`,
      `Phone / WhatsApp: ${optional(values.phone)}`, `Service Type: ${values.service}`,
      `Commodity: ${values.commodity}`, `Estimated Quantity: ${optional(values.quantity)}`,
      `Origin Country: ${optional(values.origin)}`, `Destination Country: ${optional(values.destination)}`, "",
      "Additional Notes:", optional(values.notes), "",
      "Please provide further information regarding the quotation and process.", "", "Thank you."
    ].join("\n");
  }
  function openWhatsApp(number, message) {
    const url = `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
    fallbackLink.href = url;
    fallback.hidden = false;
    try { window.open(url, "_blank", "noopener,noreferrer"); }
    catch { /* Tautan cadangan tetap tersedia jika popup diblokir browser. */ }
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    fallback.hidden = true;
    fallbackLink.removeAttribute("href");
    let firstInvalid;
    requiredFields.forEach(({ name }) => {
      const field = form.elements[name];
      field.value = field.value.trim();
      const message = fieldMessage(field);
      displayFieldError(field, message);
      if (message && !firstInvalid) firstInvalid = field;
    });
    if (firstInvalid) { setStatus("Please complete the highlighted fields to prepare your inquiry.", true); firstInvalid.focus(); return; }
    const number = getWhatsAppNumber();
    if (!number) { setStatus("Our WhatsApp contact has not been added yet. Please check back shortly or use the contact details below.", true); return; }
    openWhatsApp(number, messageFromForm());
    setStatus("Your inquiry is ready. Review the message in WhatsApp, then press Send.");
  });
  document.getElementById("inquiry-submit").disabled = false;

  // Saat mengetik di ponsel, tombol melayang tidak menutupi input atau keyboard.
  const floatingButton = document.getElementById("floating-whatsapp");
  function updateFloatingButton() {
    const editing = mobileNavigation.matches && form.contains(document.activeElement);
    floatingButton.classList.toggle("is-form-active", editing);
    floatingButton.inert = editing;
  }
  form.addEventListener("focusin", updateFloatingButton);
  form.addEventListener("focusout", () => window.setTimeout(updateFloatingButton, 0));
  mobileNavigation.addEventListener("change", updateFloatingButton);

  /* Pilihan layanan/produk mengisi form tanpa menghapus catatan yang sudah ditulis. */
  let inquiryFocusTimer;
  document.querySelectorAll("[data-inquiry-product], [data-inquiry-service], [data-inquiry-note]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      setMenu(false);
      let focusField = form.elements.commodity;
      if (button.dataset.inquiryService) { form.elements.service.value = button.dataset.inquiryService; focusField = form.elements.service; }
      if (button.dataset.inquiryProduct) {
        const product = button.dataset.inquiryProduct;
        form.elements.service.value = "Export";
        if (!focusField.value.trim()) focusField.value = product;
        else if (!focusField.value.includes(product)) focusField.value += `\n${product}`;
        displayFieldError(focusField, "");
      }
      if (button.dataset.inquiryNote) {
        focusField = form.elements.notes;
        const note = button.dataset.inquiryNote;
        if (!focusField.value.includes(note)) focusField.value += `${focusField.value ? "\n" : ""}${note}`;
      }
      fallback.hidden = true;
      fallbackLink.removeAttribute("href");
      setStatus("");
      document.getElementById("quote").scrollIntoView({ behavior: motionPreference.matches ? "instant" : "smooth", block: "start" });
      window.clearTimeout(inquiryFocusTimer);
      inquiryFocusTimer = window.setTimeout(() => focusField.focus(), motionPreference.matches ? 0 : 550);
    });
  });
  document.getElementById("floating-whatsapp").addEventListener("click", () => {
    const number = getWhatsAppNumber();
    if (number) {
      const url = `https://wa.me/${number}?text=${encodeURIComponent("Hello, I would like to discuss your briquette export services.")}`;
      window.open(url, "_blank", "noopener,noreferrer");
    } else {
      setStatus("Our WhatsApp contact has not been added yet. You can review the inquiry form or contact details below.", true);
      document.getElementById("quote").scrollIntoView({ behavior: motionPreference.matches ? "instant" : "smooth", block: "start" });
    }
  });
})();
