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
    const appLayout = document.querySelector(".app-layout");

    const profileMenu = document.querySelector(".profile-menu");
    const profileButton = document.getElementById("profile-menu-toggle");

    if (menuButton && sidebar && overlay && appLayout) {

        function openMobileSidebar() {
            sidebar.classList.add("mobile-open");
            overlay.classList.add("mobile-open");
            menuButton.setAttribute("aria-expanded", "true");
            menuButton.setAttribute("aria-label", "Close navigation menu");
            document.body.style.overflow = "hidden";
        }

        function closeMobileSidebar() {
            sidebar.classList.remove("mobile-open");
            overlay.classList.remove("mobile-open");
            menuButton.setAttribute("aria-expanded", "false");
            menuButton.setAttribute("aria-label", "Open navigation menu");
            document.body.style.overflow = "";
        }

        menuButton.addEventListener("click", function () {
            if (window.innerWidth < 768) {
                if (sidebar.classList.contains("mobile-open")) {
                    closeMobileSidebar();
                } else {
                    openMobileSidebar();
                }
            } else {
                appLayout.classList.toggle("sidebar-collapsed");

                const collapsed =
                    appLayout.classList.contains("sidebar-collapsed");

                menuButton.setAttribute("aria-expanded", String(!collapsed));
                menuButton.setAttribute(
                    "aria-label",
                    collapsed ? "Expand navigation menu" : "Collapse navigation menu"
                );
            }
        });

        overlay.addEventListener("click", closeMobileSidebar);

        sidebar.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.innerWidth < 768) {
                    closeMobileSidebar();
                }
            });
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth >= 768) {
                closeMobileSidebar();
            }
        });
    }

    if (profileMenu && profileButton) {

        function closeProfileMenu() {
            profileMenu.classList.remove("open");
            profileButton.setAttribute("aria-expanded", "false");
        }

        profileButton.addEventListener("click", function (event) {
            event.stopPropagation();

            const isOpen = profileMenu.classList.toggle("open");

            profileButton.setAttribute("aria-expanded", String(isOpen));
        });

        document.addEventListener("click", function (event) {
            if (!profileMenu.contains(event.target)) {
                closeProfileMenu();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeProfileMenu();
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebar && sidebar.classList.contains("mobile-open")) {
            sidebar.classList.remove("mobile-open");

            if (overlay) {
                overlay.classList.remove("mobile-open");
            }

            if (menuButton) {
                menuButton.setAttribute("aria-expanded", "false");
                menuButton.setAttribute("aria-label", "Open navigation menu");
            }

            document.body.style.overflow = "";
        }
    });
})();