/* ==========================================================
   JK Growth Labs — interactions
   ========================================================== */

(() => {
    // ------- Navbar scroll state -------
    const navbar = document.getElementById('navbar');
    const floatCTA = document.querySelector('.float-cta');
    const heroHeight = () => document.querySelector('.hero')?.offsetHeight ?? 600;

    const onScroll = () => {
        if (window.scrollY > 20) navbar.classList.add('scrolled');
        else navbar.classList.remove('scrolled');

        if (window.scrollY > heroHeight() * 0.6) floatCTA?.classList.add('visible');
        else floatCTA?.classList.remove('visible');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // ------- Dynamic year -------
    document.getElementById('year').textContent = new Date().getFullYear();

    // ------- Smooth anchor scroll with nav offset -------
    const smoothScrollTo = (hash) => {
        const target = document.querySelector(hash);
        if (!target) return;
        const top = target.getBoundingClientRect().top + window.scrollY - 76;
        window.scrollTo({ top, behavior: 'smooth' });
    };

    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const hash = link.getAttribute('href');
            if (!hash || hash.length <= 1) return;
            if (!document.querySelector(hash)) return;
            e.preventDefault();
            smoothScrollTo(hash);
            closeMobileMenu();
        });
    });

    // ------- Mobile menu -------
    const menuToggle = document.querySelector('.menu-toggle');
    let mobileMenu = null;

    const buildMobileMenu = () => {
        if (mobileMenu) return mobileMenu;
        mobileMenu = document.createElement('div');
        mobileMenu.className = 'mobile-menu';
        mobileMenu.innerHTML = `
            <a href="#services">Services</a>
            <a href="#work">Work</a>
            <a href="#approach">Approach</a>
            <a href="#results">Results</a>
            <a href="#faq">FAQ</a>
            <a href="#contact" class="btn btn-primary">Book a call →</a>
        `;
        document.body.appendChild(mobileMenu);
        mobileMenu.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', (e) => {
                const hash = a.getAttribute('href');
                if (!document.querySelector(hash)) return;
                e.preventDefault();
                smoothScrollTo(hash);
                closeMobileMenu();
            });
        });
        return mobileMenu;
    };

    const closeMobileMenu = () => {
        if (mobileMenu) mobileMenu.classList.remove('open');
    };

    menuToggle?.addEventListener('click', () => {
        buildMobileMenu().classList.toggle('open');
    });

    // ------- Animated metric counters -------
    const counters = document.querySelectorAll('.metric-value [data-target]');
    const animateCount = (el) => {
        const target = +el.dataset.target;
        const duration = 1600;
        const start = performance.now();
        const step = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.floor(eased * target);
            if (progress < 1) requestAnimationFrame(step);
            else el.textContent = target;
        };
        requestAnimationFrame(step);
    };

    // ------- Reveal-on-scroll -------
    const revealTargets = document.querySelectorAll(
        '.hero-trust, .metrics-grid, .service-card, .process-step, .logo-item, .case-card, .testimonial, .faq-item, .cta-card, .section-head, .why-copy, .why-card'
    );
    revealTargets.forEach(el => el.classList.add('reveal'));

    const io = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('visible');
            if (entry.target.classList.contains('metrics-grid')) {
                counters.forEach(animateCount);
            }
            io.unobserve(entry.target);
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealTargets.forEach(el => io.observe(el));

    // ------- Staggered transition delays -------
    const stagger = (selector, step = 70) => {
        document.querySelectorAll(selector).forEach((el, i) => {
            el.style.transitionDelay = `${i * step}ms`;
        });
    };
    stagger('.service-grid .service-card', 70);
    stagger('.process-grid .process-step', 90);
    stagger('.logo-grid .logo-item', 45);
    stagger('.case-grid .case-card', 100);
    stagger('.testimonial-grid .testimonial', 80);
    stagger('.faq-list .faq-item', 50);

    // ------- FAQ: close others when one opens -------
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        item.addEventListener('toggle', () => {
            if (!item.open) return;
            faqItems.forEach(other => { if (other !== item) other.open = false; });
        });
    });

    // ------- Contact form (client-side only, demo handler) -------
    const form = document.getElementById('contactForm');
    const status = document.getElementById('formStatus');
    const submitBtn = form?.querySelector('button[type="submit"]');

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());

        const missing = ['name', 'email', 'company', 'interest', 'message']
            .filter(k => !data[k]?.toString().trim());

        if (missing.length) {
            status.style.color = '#f87171';
            status.textContent = `Please complete the ${missing[0]} field.`;
            return;
        }

        const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email);
        if (!emailOk) {
            status.style.color = '#f87171';
            status.textContent = 'Please enter a valid work email.';
            return;
        }

        const originalLabel = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Sending…';
        status.style.color = 'var(--text-dim)';
        status.textContent = '';

        // Simulated transit — swap for real endpoint when ready.
        await new Promise(r => setTimeout(r, 900));

        status.style.color = '#34d399';
        status.textContent = `Thanks, ${data.name.split(' ')[0]} — we'll reply within one business day.`;
        form.reset();
        submitBtn.innerHTML = originalLabel;
        submitBtn.disabled = false;

        setTimeout(() => { status.textContent = ''; }, 8000);
    });

    // ------- Subtle card tilt on pointer (hero-free, perf-light) -------
    const tiltables = document.querySelectorAll('.service-card, .case-card');
    tiltables.forEach(card => {
        card.addEventListener('pointermove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            card.style.transform = `translateY(-6px) rotateX(${(-y * 3).toFixed(2)}deg) rotateY(${(x * 3).toFixed(2)}deg)`;
        });
        card.addEventListener('pointerleave', () => {
            card.style.transform = '';
        });
    });
})();
