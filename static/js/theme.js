(function () {
    const STORAGE_KEY = "paulschoolhub-theme";

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem(STORAGE_KEY, theme);

        const button = document.getElementById("theme-toggle");

        if (button) {
            if (theme === "dark") {
                button.textContent = "☀ Light";
                button.setAttribute("aria-label", "Switch to light mode");
                button.setAttribute("title", "Switch to light mode");
            } else {
                button.textContent = "🌙 Dark";
                button.setAttribute("aria-label", "Switch to dark mode");
                button.setAttribute("title", "Switch to dark mode");
            }
        }
    }

    const savedTheme = localStorage.getItem(STORAGE_KEY);
    const initialTheme = savedTheme === "dark" ? "dark" : "light";

    document.documentElement.setAttribute("data-theme", initialTheme);

    document.addEventListener("DOMContentLoaded", function () {
        const button = document.getElementById("theme-toggle");

        if (!button) {
            return;
        }

        applyTheme(initialTheme);

        button.addEventListener("click", function () {
            const currentTheme =
                document.documentElement.getAttribute("data-theme");

            applyTheme(currentTheme === "dark" ? "light" : "dark");
        });
    });
})();


(function () {
    const menuButton = document.getElementById("mobile-menu-toggle");
    const sidebar = document.getElementById("school-sidebar");
    const overlay = document.getElementById("sidebar-overlay");

    if (!menuButton || !sidebar || !overlay) {
        return;
    }

    function openSidebar() {
        sidebar.classList.add("mobile-open");
        overlay.classList.add("mobile-open");
        menuButton.setAttribute("aria-expanded", "true");
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        sidebar.classList.remove("mobile-open");
        overlay.classList.remove("mobile-open");
        menuButton.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
    }

    menuButton.addEventListener("click", function () {
        if (sidebar.classList.contains("mobile-open")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay.addEventListener("click", closeSidebar);

    sidebar.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", closeSidebar);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeSidebar();
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth >= 768) {
            closeSidebar();
        }
    });
})();