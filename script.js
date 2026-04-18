// Navbar scroll styling
const navbar = document.querySelector('.navbar');
window.addEventListener('scroll', () => {
    if (window.scrollY > 20) navbar.classList.add('scrolled');
    else navbar.classList.remove('scrolled');
});

// Dynamic year
document.getElementById('year').textContent = new Date().getFullYear();

// Smooth anchor scroll with offset for fixed nav
document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        const targetId = link.getAttribute('href');
        if (targetId.length <= 1) return;
        const target = document.querySelector(targetId);
        if (!target) return;
        e.preventDefault();
        const top = target.getBoundingClientRect().top + window.scrollY - 72;
        window.scrollTo({ top, behavior: 'smooth' });
        closeMobileMenu();
    });
});

// Mobile menu
const menuToggle = document.querySelector('.menu-toggle');
let mobileMenu = null;

function buildMobileMenu() {
    if (mobileMenu) return mobileMenu;
    mobileMenu = document.createElement('div');
    mobileMenu.className = 'mobile-menu';
    mobileMenu.innerHTML = `
        <a href="#services">Services</a>
        <a href="#clients">Clients</a>
        <a href="#process">Process</a>
        <a href="#contact">Contact</a>
    `;
    document.body.appendChild(mobileMenu);
    mobileMenu.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', (e) => {
            const targetId = a.getAttribute('href');
            const target = document.querySelector(targetId);
            if (!target) return;
            e.preventDefault();
            const top = target.getBoundingClientRect().top + window.scrollY - 72;
            window.scrollTo({ top, behavior: 'smooth' });
            closeMobileMenu();
        });
    });
    return mobileMenu;
}

function closeMobileMenu() {
    if (mobileMenu) mobileMenu.classList.remove('open');
}

menuToggle?.addEventListener('click', () => {
    const menu = buildMobileMenu();
    menu.classList.toggle('open');
});

// Animate stat counters on view
const stats = document.querySelectorAll('.stat-value');
const animateCount = (el) => {
    const target = +el.dataset.target;
    const duration = 1400;
    const start = performance.now();
    const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target) + (target >= 100 ? '' : '');
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target + (target >= 100 ? '' : '');
    };
    requestAnimationFrame(step);
};

// Reveal-on-scroll for sections and cards
const revealTargets = document.querySelectorAll(
    '.hero-stats, .service-card, .process-step, .logo-item, .cta-card, .section-head'
);
revealTargets.forEach(el => el.classList.add('reveal'));

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        if (entry.target.classList.contains('hero-stats')) {
            stats.forEach(animateCount);
        }
        observer.unobserve(entry.target);
    });
}, { threshold: 0.15 });

revealTargets.forEach(el => observer.observe(el));

// Stagger card reveals
document.querySelectorAll('.service-grid .service-card').forEach((card, i) => {
    card.style.transitionDelay = `${i * 80}ms`;
});
document.querySelectorAll('.process-grid .process-step').forEach((step, i) => {
    step.style.transitionDelay = `${i * 100}ms`;
});
document.querySelectorAll('.logo-grid .logo-item').forEach((logo, i) => {
    logo.style.transitionDelay = `${i * 50}ms`;
});

// Contact form — local handler (no backend)
const form = document.getElementById('contactForm');
const status = document.getElementById('formStatus');

form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.name || !data.email || !data.company || !data.message) {
        status.style.color = '#f87171';
        status.textContent = 'Please fill out every field.';
        return;
    }
    status.style.color = '#10b981';
    status.textContent = `Thanks, ${data.name.split(' ')[0]}! We'll reply within 24 hours.`;
    form.reset();
    setTimeout(() => { status.textContent = ''; }, 6000);
});
